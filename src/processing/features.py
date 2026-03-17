"""
src/processing/features.py
============================
Feature engineering : calcul de tous les indicateurs climatiques
requis par le cahier des charges (≥ 8 indicateurs).

Produit un dataset consolidé "master_features.parquet" prêt pour la modélisation.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import PROCESSED_DIR, INDICATORS


class ClimateFeatureEngineer:
    """
    Construit les indicateurs climatiques à partir des données nettoyées.

    Indicateurs produits :
    1. Anomalie de température (vs normale 1961-1990)
    2. Tendance décennale de température
    3. Indice de chaleur extrême
    4. Indice de sécheresse simplifié
    5. Taux de variation des GES
    6. Indice de pression carbone
    7. Score de risque climatique composite
    8. Fenêtre mobile (rolling mean 10 ans)
    """

    REFERENCE_PERIOD = (1961, 1990)  # Normale climatique de référence

    def __init__(self):
        self.output_dir = PROCESSED_DIR
        self.features_df: pd.DataFrame = None

    def build_all(self) -> pd.DataFrame:
        """Construit toutes les features et sauvegarde le dataset master."""
        logger.info("🔧 Feature engineering — construction des indicateurs...")

        # Chargement des datasets nettoyés
        temp_df = self._load("temperatures_clean.parquet")
        co2_df = self._load("co2_clean.parquet")
        ges_df = self._load("ges_clean.parquet")
        empreinte_df = self._load("empreinte_clean.parquet")

        # Construction du dataset maître (index = année)
        df = temp_df[["annee"]].copy() if temp_df is not None else pd.DataFrame({"annee": range(1900, 2025)})

        # ── Indicateurs température ──────────────────
        if temp_df is not None:
            df = df.merge(temp_df[["annee", "temp_moy_c", "jours_chauds_30", "jours_gel", "precip_mm"]],
                          on="annee", how="left")

            # 1. Anomalie vs normale 1961-1990
            ref_temp = temp_df.loc[
                temp_df["annee"].between(*self.REFERENCE_PERIOD), "temp_moy_c"
            ].mean()
            df["anomalie_temp_c"] = (df["temp_moy_c"] - ref_temp).round(3)

            # 2. Tendance mobile 10 ans (°C/décennie)
            df["trend_temp_10ans"] = (
                df["temp_moy_c"]
                .rolling(window=10, min_periods=5)
                .apply(self._linear_trend, raw=True)
            ).round(3)

            # 3. Indice chaleur extrême (normalisé 0-100)
            df["indice_chaleur"] = self._normalize(df["jours_chauds_30"]) * 100

            # 4. Indicateur sécheresse (déficit précipitations vs normale)
            if "precip_mm" in df.columns:
                ref_precip = temp_df.loc[
                    temp_df["annee"].between(*self.REFERENCE_PERIOD), "precip_mm"
                ].mean()
                df["deficit_precip_pct"] = ((df["precip_mm"] - ref_precip) / ref_precip * 100).round(2)
                df["annee_seche"] = (df["deficit_precip_pct"] < -10).astype(int)

        # ── Indicateurs CO₂ ────────────────────────
        if co2_df is not None:
            df = df.merge(co2_df[["annee", "co2_ppm"]], on="annee", how="left")

            # 5. Accélération CO₂ (variation annuelle)
            df["co2_variation_annuelle"] = df["co2_ppm"].diff().round(3)
            df["co2_acceleration"] = df["co2_variation_annuelle"].diff().round(4)

        # ── Indicateurs GES ─────────────────────────
        if ges_df is not None:
            ges_total = ges_df[ges_df["secteur"] == "TOTAL"][["annee", "emissions_mtco2eq"]].copy()
            ges_total.rename(columns={"emissions_mtco2eq": "ges_total_mtco2eq"}, inplace=True)
            df = df.merge(ges_total, on="annee", how="left")

            # 6. Taux de baisse GES (%)
            df["ges_variation_pct"] = df["ges_total_mtco2eq"].pct_change() * 100

            # Objectif 2030 : -55% vs 1990
            ges_1990 = ges_df.loc[(ges_df["annee"] == 1990) & (ges_df["secteur"] == "TOTAL"),
                                   "emissions_mtco2eq"].values
            if len(ges_1990) > 0:
                df["ges_vs_1990_pct"] = ((df["ges_total_mtco2eq"] - ges_1990[0]) / ges_1990[0] * 100).round(2)
                df["objectif_2030_ecart"] = df["ges_total_mtco2eq"] - (ges_1990[0] * 0.45)

        # ── Empreinte carbone ───────────────────────
        if empreinte_df is not None:
            df = df.merge(
                empreinte_df[["annee", "empreinte_totale_tco2eq", "part_importee_tco2eq"]],
                on="annee", how="left"
            )

        # ── Score de risque composite ───────────────
        df = self._compute_risk_score(df)

        # ── Variables de lags (pour les modèles ML) ─
        df = self._add_lag_features(df, target="temp_moy_c", lags=[1, 2, 3, 5, 10])
        if "co2_ppm" in df.columns:
            df = self._add_lag_features(df, target="co2_ppm", lags=[1, 2, 5])

        # Sauvegarde
        out = self.output_dir / "master_features.parquet"
        df.to_parquet(out, index=False)
        logger.success(f"✅ Master features : {len(df)} lignes × {len(df.columns)} colonnes → {out.name}")
        self.features_df = df
        return df

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────
    def _load(self, filename: str) -> pd.DataFrame | None:
        """Charge un parquet depuis le dossier processed/."""
        path = self.output_dir / filename
        if path.exists():
            return pd.read_parquet(path)
        logger.warning(f"⚠️ {filename} introuvable — indicateur ignoré")
        return None

    @staticmethod
    def _linear_trend(values: np.ndarray) -> float:
        """Calcule la tendance linéaire sur une fenêtre (°C/10 ans)."""
        x = np.arange(len(values))
        if len(values) < 2:
            return np.nan
        slope, *_ = np.polyfit(x, values, 1)
        return slope * 10  # Par décennie

    @staticmethod
    def _normalize(series: pd.Series) -> pd.Series:
        """Normalisation min-max entre 0 et 1."""
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series(np.zeros(len(series)), index=series.index)
        return (series - mn) / (mx - mn)

    def _compute_risk_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score de risque climatique composite (0-100).
        Combine anomalie thermique + CO₂ + jours chauds.
        """
        scores = pd.Series(np.zeros(len(df)), index=df.index)
        weights = 0

        if "anomalie_temp_c" in df.columns:
            scores += self._normalize(df["anomalie_temp_c"].fillna(0)) * 40
            weights += 40
        if "co2_ppm" in df.columns:
            scores += self._normalize(df["co2_ppm"].fillna(0)) * 35
            weights += 35
        if "indice_chaleur" in df.columns:
            scores += self._normalize(df["indice_chaleur"].fillna(0)) * 25
            weights += 25

        df["score_risque_climatique"] = (scores / weights * 100).round(1) if weights > 0 else 50
        return df

    def _add_lag_features(self, df: pd.DataFrame, target: str, lags: list) -> pd.DataFrame:
        """Ajoute des variables de décalage temporel pour les modèles ML."""
        if target not in df.columns:
            return df
        for lag in lags:
            df[f"{target}_lag{lag}"] = df[target].shift(lag)
        return df

    def get_summary(self) -> pd.DataFrame:
        """Retourne un résumé statistique des indicateurs."""
        if self.features_df is None:
            raise ValueError("Appeler build_all() d'abord")
        return self.features_df.describe().round(3)


if __name__ == "__main__":
    engineer = ClimateFeatureEngineer()
    df = engineer.build_all()
    print(f"\n📊 Colonnes disponibles ({len(df.columns)}) :")
    for c in df.columns:
        print(f"  - {c}")
