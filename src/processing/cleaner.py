"""
src/processing/cleaner.py
==========================
Nettoyage des données brutes :
- Gestion des valeurs manquantes
- Détection et traitement des outliers
- Standardisation des formats de dates et unités
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import RAW_DIR, PROCESSED_DIR


class DataCleaner:
    """
    Nettoie les données climatiques brutes.

    Stratégies de gestion des valeurs manquantes :
    - Interpolation linéaire pour séries temporelles courtes (<5% missing)
    - Interpolation polynomiale pour lacunes moyennes
    - Suppression pour lacunes trop importantes
    """

    # Seuils de qualité
    MAX_MISSING_RATIO = 0.15    # Max 15% de valeurs manquantes tolérées
    ZSCORE_THRESHOLD = 3.5      # Seuil Z-score pour les outliers

    def __init__(self):
        self.cleaning_report: dict = {}

    def clean_all(self) -> dict:
        """Nettoie tous les fichiers bruts disponibles."""
        results = {}

        datasets = {
            "temperatures": RAW_DIR / "meteofrance" / "temperatures_annuelles.parquet",
            "co2": RAW_DIR / "noaa" / "co2_annuel.parquet",
            "ch4": RAW_DIR / "noaa" / "ch4_annuel.parquet",
            "ges": RAW_DIR / "citepa" / "ges_france_par_secteur.parquet",
            "empreinte": RAW_DIR / "citepa" / "empreinte_carbone_individuelle.parquet",
        }

        for name, path in datasets.items():
            if path.exists():
                logger.info(f"🧹 Nettoyage : {name}")
                df_clean, report = self.clean_dataset(pd.read_parquet(path), name)
                out = PROCESSED_DIR / f"{name}_clean.parquet"
                df_clean.to_parquet(out, index=False)
                results[name] = {"path": out, "report": report}
                logger.success(f"✅ {name} : {len(df_clean)} lignes → {out.name}")
            else:
                logger.warning(f"⚠️ Fichier manquant : {path}")

        return results

    def clean_dataset(self, df: pd.DataFrame, name: str) -> Tuple[pd.DataFrame, dict]:
        """
        Nettoie un DataFrame selon les étapes standard.

        Returns:
            (df_clean, report_dict)
        """
        report = {"name": name, "initial_rows": len(df), "actions": []}

        # 1. Suppression des doublons
        n_before = len(df)
        df = df.drop_duplicates()
        if len(df) < n_before:
            report["actions"].append(f"Doublons supprimés : {n_before - len(df)}")

        # 2. Colonnes numériques uniquement (hors clés)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        key_cols = ["annee", "annee_mois", "secteur", "station_id", "source"]
        numeric_cols = [c for c in numeric_cols if c not in key_cols]

        # 3. Valeurs manquantes
        for col in numeric_cols:
            missing_ratio = df[col].isna().mean()
            if missing_ratio > self.MAX_MISSING_RATIO:
                logger.warning(f"  ⚠️ {col} : {missing_ratio:.1%} manquants (> seuil {self.MAX_MISSING_RATIO:.0%})")
                report["actions"].append(f"{col}: {missing_ratio:.1%} manquants → colonne marquée")
                df[f"{col}_quality"] = (~df[col].isna()).astype(int)
            elif missing_ratio > 0:
                df[col] = self._interpolate(df, col)
                report["actions"].append(f"{col}: {missing_ratio:.1%} manquants → interpolé")

        # 4. Détection et traitement des outliers (Z-score)
        for col in numeric_cols:
            if col in df.columns:
                z_scores = np.abs(stats.zscore(df[col].dropna()))
                outlier_mask = z_scores > self.ZSCORE_THRESHOLD
                n_outliers = outlier_mask.sum()
                if n_outliers > 0:
                    # Remplace les outliers par interpolation linéaire
                    df.loc[df[col].notna(), col] = self._clip_outliers(
                        df[col].dropna().values, self.ZSCORE_THRESHOLD
                    )
                    report["actions"].append(f"{col}: {n_outliers} outliers traités (Z>{self.ZSCORE_THRESHOLD})")

        # 5. Assurer le tri chronologique
        if "annee" in df.columns:
            df = df.sort_values("annee").reset_index(drop=True)

        report["final_rows"] = len(df)
        report["missing_after"] = {c: df[c].isna().sum() for c in numeric_cols if c in df.columns}

        return df, report

    def _interpolate(self, df: pd.DataFrame, col: str) -> pd.Series:
        """Interpolation temporelle adaptative."""
        s = df[col].copy()
        # Interpolation linéaire si série est bien triée
        s = s.interpolate(method="linear", limit_direction="both")
        # Remplissage des extrêmes
        s = s.ffill().bfill()
        return s

    def _clip_outliers(self, values: np.ndarray, threshold: float) -> np.ndarray:
        """Remplace les valeurs aberrantes par les percentiles 1% / 99%."""
        p1, p99 = np.percentile(values, [1, 99])
        return np.clip(values, p1, p99)

    def print_report(self):
        """Affiche un rapport de nettoyage dans le terminal."""
        from rich.table import Table
        from rich.console import Console
        console = Console()

        table = Table(title="📋 Rapport de nettoyage")
        table.add_column("Dataset", style="cyan")
        table.add_column("Lignes initiales", justify="right")
        table.add_column("Lignes finales", justify="right")
        table.add_column("Actions", style="dim")

        for name, info in self.cleaning_report.items():
            r = info["report"]
            table.add_row(
                name,
                str(r.get("initial_rows", "?")),
                str(r.get("final_rows", "?")),
                f"{len(r.get('actions', []))} action(s)",
            )
        console.print(table)


if __name__ == "__main__":
    cleaner = DataCleaner()
    results = cleaner.clean_all()
    print(f"✅ {len(results)} datasets nettoyés")
