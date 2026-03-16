"""
src/processing/transformer.py
==============================
Transformations avancées des données nettoyées :
- Agrégations temporelles (mensuel → annuel, décennal)
- Jointures multi-sources
- Normalisation pour les modèles ML
- Export vers formats multiples (Parquet, CSV, JSON)

Usage:
    python -m src.processing.transformer
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.preprocessing import StandardScaler, MinMaxScaler

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import PROCESSED_DIR, HISTORICAL_START_YEAR, HISTORICAL_END_YEAR


class DataTransformer:
    """
    Transforme et enrichit les données climatiques nettoyées.

    Pipeline :
    1. Chargement des données individuelles
    2. Agrégation multi-échelle
    3. Jointure (merge) sur l'axe temporel (annee)
    4. Normalisation pour les modèles
    5. Export des jeux de données finaux
    """

    def __init__(self):
        self.output_dir = PROCESSED_DIR
        self._scalers: dict = {}
        self._master_df: Optional[pd.DataFrame] = None

    # ─────────────────────────────────────────────
    # POINT D'ENTRÉE
    # ─────────────────────────────────────────────
    def run(self) -> dict:
        """Lance toutes les transformations. Retourne les chemins de sortie."""
        logger.info("🔄 Transformation des données...")
        results = {}

        # 1. Chargement
        datasets = self._load_cleaned_datasets()

        # 2. Agrégations
        if "temperatures" in datasets:
            results["temp_decennal"] = self._aggregate_decennal(
                datasets["temperatures"], "temp_moy_c"
            )

        # 3. Merge multi-source
        master = self._build_master_dataset(datasets)
        if master is not None:
            self._master_df = master
            out = self.output_dir / "master_features.parquet"
            master.to_parquet(out, index=False)
            master.to_csv(self.output_dir / "master_features.csv", index=False)
            results["master"] = out
            logger.success(
                f"✅ Master dataset : {len(master)} lignes × {len(master.columns)} cols"
            )

        # 4. Jeu de données modèle (normalisé)
        if master is not None:
            results["model_ready"] = self._export_model_ready(master)

        # 5. Export GeoJSON simplifié pour la carto
        results["geojson"] = self._export_geojson_summary(master)

        return results

    # ─────────────────────────────────────────────
    # CHARGEMENT
    # ─────────────────────────────────────────────
    def _load_cleaned_datasets(self) -> dict:
        datasets = {}
        files = {
            "temperatures": "temperatures_clean.parquet",
            "co2":          "co2_clean.parquet",
            "ch4":          "ch4_clean.parquet",
            "ges":          "ges_clean.parquet",
            "empreinte":    "empreinte_clean.parquet",
        }
        for name, fname in files.items():
            path = self.output_dir / fname
            if path.exists():
                datasets[name] = pd.read_parquet(path)
                logger.info(f"  ✓ {name} chargé ({len(datasets[name])} lignes)")
            else:
                # Génération de données synthétiques pour les fichiers manquants
                datasets[name] = self._generate_fallback(name)
                if datasets[name] is not None:
                    logger.warning(f"  ⚠️ {name} → données synthétiques (fallback)")
        return datasets

    def _generate_fallback(self, name: str) -> Optional[pd.DataFrame]:
        """Génère des données de remplacement si le fichier nettoyé est absent."""
        np.random.seed(42)
        years = list(range(HISTORICAL_START_YEAR, HISTORICAL_END_YEAR + 1))
        n = len(years)

        if name == "temperatures":
            trend = np.linspace(0, 1.7, n)
            noise = np.random.normal(0, 0.25, n)
            return pd.DataFrame({
                "annee": years,
                "temp_moy_c": (12.0 + trend + noise).round(2),
                "anomalie_temp_c": (trend + noise).round(3),
                "jours_chauds_30": (10 + np.linspace(0, 20, n) + np.random.poisson(2, n)).clip(0).astype(int),
                "jours_gel": (60 - np.linspace(0, 15, n) + np.random.normal(0, 4, n)).clip(0).astype(int),
                "precip_mm": (700 - np.linspace(0, 30, n) + np.random.normal(0, 50, n)).round(1),
            })
        elif name == "co2":
            co2_values = (296 + np.linspace(0, 127, n) + np.random.normal(0, 0.3, n)).round(2)
            return pd.DataFrame({"annee": years, "co2_ppm": co2_values})
        elif name == "ch4":
            ch4_values = (900 + np.linspace(0, 1023, n)).round(1)
            return pd.DataFrame({"annee": years, "ch4_ppb": ch4_values})
        elif name == "ges":
            ges_years = list(range(1990, HISTORICAL_END_YEAR + 1))
            rows = []
            for yr in ges_years:
                total = 560 - (yr - 1990) * 5 + np.random.normal(0, 3)
                rows.append({"annee": yr, "secteur": "TOTAL", "emissions_mtco2eq": round(max(0, total), 1)})
            return pd.DataFrame(rows)
        elif name == "empreinte":
            e_years = list(range(1995, HISTORICAL_END_YEAR + 1))
            return pd.DataFrame({
                "annee": e_years,
                "empreinte_totale_tco2eq": (np.linspace(12.5, 9.9, len(e_years)) + np.random.normal(0, 0.1, len(e_years))).round(2),
                "part_importee_tco2eq": np.linspace(3.2, 4.4, len(e_years)).round(2),
            })
        return None

    # ─────────────────────────────────────────────
    # AGRÉGATIONS
    # ─────────────────────────────────────────────
    def _aggregate_decennal(self, df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Agrège une variable par décennie."""
        df = df.copy()
        df["decennie"] = (df["annee"] // 10 * 10)
        agg = df.groupby("decennie").agg(
            moyenne=(col, "mean"),
            min_val=(col, "min"),
            max_val=(col, "max"),
            std_val=(col, "std"),
            count=(col, "count"),
        ).reset_index()
        agg.columns = ["decennie", f"{col}_moy", f"{col}_min", f"{col}_max", f"{col}_std", "n_obs"]

        out = self.output_dir / f"{col}_decennal.parquet"
        agg.to_parquet(out, index=False)
        logger.info(f"  ✓ Agrégat décennal '{col}' → {out.name}")
        return agg

    # ─────────────────────────────────────────────
    # MERGE MULTI-SOURCE
    # ─────────────────────────────────────────────
    def _build_master_dataset(self, datasets: dict) -> Optional[pd.DataFrame]:
        """
        Construit le dataset maître par jointure sur l'année.

        Stratégie : left join à partir de la table températures (référence).
        Les variables de sources plus courtes (GES depuis 1990, empreinte depuis 1995)
        auront des NaN pour les années antérieures → gérés par les modèles.
        """
        if "temperatures" not in datasets:
            logger.error("❌ Températures manquantes — impossible de construire le master dataset")
            return None

        master = datasets["temperatures"].copy()

        # CO₂
        if "co2" in datasets:
            master = master.merge(
                datasets["co2"][["annee", "co2_ppm"]],
                on="annee", how="left"
            )

        # CH₄
        if "ch4" in datasets:
            master = master.merge(
                datasets["ch4"][["annee", "ch4_ppb"]],
                on="annee", how="left"
            )

        # GES total
        if "ges" in datasets:
            ges_total = datasets["ges"][datasets["ges"]["secteur"] == "TOTAL"][
                ["annee", "emissions_mtco2eq"]
            ].rename(columns={"emissions_mtco2eq": "ges_total_mtco2eq"})
            master = master.merge(ges_total, on="annee", how="left")

        # Empreinte carbone
        if "empreinte" in datasets:
            master = master.merge(
                datasets["empreinte"][["annee", "empreinte_totale_tco2eq", "part_importee_tco2eq"]],
                on="annee", how="left"
            )

        # ── Features dérivées ─────────────────────
        master = self._add_derived_features(master)

        # Tri chronologique + reset index
        master = master.sort_values("annee").reset_index(drop=True)

        logger.info(
            f"  ✓ Master dataset construit : {len(master)} lignes × {len(master.columns)} colonnes"
        )
        return master

    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute les features calculées au master dataset."""
        df = df.copy()

        # Anomalie de température vs normale 1961-1990
        if "temp_moy_c" in df.columns:
            ref = df[df["annee"].between(1961, 1990)]["temp_moy_c"].mean()
            df["anomalie_temp_c"] = (df["temp_moy_c"] - ref).round(3)

            # Tendance mobile 10 ans (°C/décennie)
            df["trend_10ans"] = (
                df["temp_moy_c"]
                .rolling(10, min_periods=5, center=True)
                .apply(lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] * 10, raw=True)
            ).round(3)

        # Accélération du CO₂
        if "co2_ppm" in df.columns:
            df["co2_delta_ann"] = df["co2_ppm"].diff().round(3)

        # Score de risque composite (0-100)
        df = self._compute_risk_score(df)

        # Variables de lag pour ML
        for col in ["temp_moy_c", "co2_ppm", "anomalie_temp_c"]:
            if col in df.columns:
                for lag in [1, 2, 3, 5, 10]:
                    df[f"{col}_lag{lag}"] = df[col].shift(lag)

        return df

    def _compute_risk_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score de risque climatique composite normalisé 0-100."""
        score = pd.Series(np.zeros(len(df)), index=df.index)
        w_total = 0

        def norm(s):
            mn, mx = s.min(), s.max()
            return (s - mn) / (mx - mn) if mx > mn else pd.Series(0.5, index=s.index)

        if "anomalie_temp_c" in df.columns:
            score += norm(df["anomalie_temp_c"].fillna(0)) * 40
            w_total += 40
        if "co2_ppm" in df.columns:
            score += norm(df["co2_ppm"].fillna(0)) * 35
            w_total += 35
        if "jours_chauds_30" in df.columns:
            score += norm(df["jours_chauds_30"].fillna(0)) * 25
            w_total += 25

        df["score_risque_climatique"] = (score / w_total * 100).round(1) if w_total > 0 else 50.0
        return df

    # ─────────────────────────────────────────────
    # EXPORT MODÈLE
    # ─────────────────────────────────────────────
    def _export_model_ready(self, df: pd.DataFrame) -> Path:
        """
        Exporte un jeu de données normalisé, prêt pour l'entraînement des modèles.
        Exclut les colonnes avec trop de NaN et normalise les features numériques.
        """
        df_model = df.copy()

        # Exclure les colonnes non-numériques et les colonnes de qualité
        exclude = ["annee", "source"] + [c for c in df_model.columns if c.endswith("_quality")]
        num_cols = [c for c in df_model.columns
                    if c not in exclude and df_model[c].dtype in [np.float64, np.int64, np.float32]]

        # Garder seulement les colonnes avec < 30% de NaN
        valid_cols = [c for c in num_cols if df_model[c].isna().mean() < 0.30]

        # Interpolation des NaN restants
        for col in valid_cols:
            df_model[col] = df_model[col].interpolate(method="linear").ffill().bfill()

        # Normalisation Standard (μ=0, σ=1)
        scaler = StandardScaler()
        df_scaled = df_model[["annee"] + valid_cols].copy()
        df_scaled[valid_cols] = scaler.fit_transform(df_model[valid_cols])
        self._scalers["standard"] = scaler

        out = self.output_dir / "model_ready_scaled.parquet"
        df_scaled.to_parquet(out, index=False)
        logger.info(f"  ✓ Données modèle normalisées : {out.name} ({len(valid_cols)} features)")
        return out

    # ─────────────────────────────────────────────
    # EXPORT GEOJSON
    # ─────────────────────────────────────────────
    def _export_geojson_summary(self, df: Optional[pd.DataFrame]) -> Path:
        """
        Exporte un résumé GeoJSON simplifié pour la cartographie Streamlit.
        Contient les valeurs actuelles par département (simulées).
        """
        import json

        # Simulation de données par département pour la carto
        departements = {
            "75": {"nom": "Paris", "lat": 48.85, "lon": 2.35},
            "69": {"nom": "Rhône", "lat": 45.74, "lon": 4.82},
            "13": {"nom": "Bouches-du-Rhône", "lat": 43.30, "lon": 5.36},
            "33": {"nom": "Gironde", "lat": 44.84, "lon": -0.58},
            "67": {"nom": "Bas-Rhin", "lat": 48.57, "lon": 7.75},
            "31": {"nom": "Haute-Garonne", "lat": 43.60, "lon": 1.44},
            "06": {"nom": "Alpes-Maritimes", "lat": 43.70, "lon": 7.26},
            "59": {"nom": "Nord", "lat": 50.63, "lon": 3.06},
            "76": {"nom": "Seine-Maritime", "lat": 49.44, "lon": 1.09},
            "34": {"nom": "Hérault", "lat": 43.61, "lon": 3.87},
        }

        np.random.seed(42)
        features = []
        for code, info in departements.items():
            anomalie = round(1.5 + float(code[:2]) * 0.005 + np.random.normal(0, 0.2), 2)
            features.append({
                "type": "Feature",
                "properties": {
                    "code_dept": code,
                    "nom": info["nom"],
                    "anomalie_temp_c": anomalie,
                    "score_risque": min(100, round(40 + anomalie * 20 + np.random.uniform(0, 10), 1)),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [info["lon"], info["lat"]],
                }
            })

        geojson = {"type": "FeatureCollection", "features": features}
        out = self.output_dir / "france_departements_summary.geojson"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        logger.info(f"  ✓ GeoJSON carto : {out.name}")
        return out

    def get_summary_stats(self) -> pd.DataFrame:
        """Statistiques descriptives du master dataset."""
        if self._master_df is None:
            raise RuntimeError("Appeler run() d'abord.")
        return self._master_df.describe().round(3)


if __name__ == "__main__":
    transformer = DataTransformer()
    results = transformer.run()
    print(f"\n✅ Transformations terminées :")
    for k, v in results.items():
        print(f"  {k} → {v}")
