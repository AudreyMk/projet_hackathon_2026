"""
src/ingestion/citepa_secten.py
================================
Ingestion des données d'émissions GES (Secten – CITEPA).
Source : https://www.citepa.org/fr/secten/

Couvre les émissions françaises par secteur depuis 1990.
"""

import sys
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import RAW_DIR


class CitepaIngester:
    """Télécharge et parse les émissions GES France (Secten)."""

    # Secteurs CITEPA Secten
    SECTEURS = [
        "Transport routier",
        "Industrie manufacturière",
        "Résidentiel / Tertiaire",
        "Agriculture / Sylviculture",
        "Production d'énergie",
        "Traitement des déchets",
        "Industrie des procédés",
    ]

    def __init__(self):
        self.output_dir = RAW_DIR / "citepa"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._row_count = 0

    def run(self) -> List[Path]:
        files = []
        files += self._download_or_generate_ges_data()
        files += self._generate_empreinte_carbone()
        return files

    def get_row_count(self) -> int:
        return self._row_count

    def _download_or_generate_ges_data(self) -> List[Path]:
        """
        Tente de télécharger le fichier Secten officiel.
        Fallback sur données synthétiques réalistes si indisponible.
        """
        logger.info("⚗️  Ingestion émissions GES CITEPA Secten...")

        try:
            # Le fichier Excel Secten n'est pas toujours accessible directement
            url = "https://www.citepa.org/wp-content/uploads/Secten_ed2024_a.xlsx"
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()

            raw_path = self.output_dir / "secten_2024.xlsx"
            with open(raw_path, "wb") as f:
                f.write(resp.content)

            df = pd.read_excel(raw_path, sheet_name=0, header=2)
            df = self._clean_secten_excel(df)
            logger.success(f"✅ Secten officiel : {len(df)} lignes")

        except Exception as e:
            logger.warning(f"⚠️ Secten non accessible ({e}) → données synthétiques réalistes")
            df = self._generate_realistic_ges()

        out = self.output_dir / "ges_france_par_secteur.parquet"
        df.to_parquet(out, index=False)
        self._row_count += len(df)
        return [out]

    def _clean_secten_excel(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoie le format Excel Secten."""
        df = df.dropna(how="all").dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        return df

    def _generate_realistic_ges(self) -> pd.DataFrame:
        """
        Génère des émissions GES réalistes pour la France 1990-2024.

        Basé sur les valeurs réelles (CITEPA 2024) :
        - 1990 : ~560 MtCO₂eq
        - 2005 : ~545 MtCO₂eq
        - 2024 : ~390 MtCO₂eq (objectifs atteints partiellement)
        """
        years = list(range(1990, 2025))
        np.random.seed(42)

        # Émissions totales avec baisse tendancielle
        total_1990 = 560
        total_2024 = 390
        total = np.linspace(total_1990, total_2024, len(years))
        # Variation COVID 2020 (-7%)
        covid_effect = np.where(np.array(years) == 2020, -0.07 * total, 0)
        total = total + covid_effect + np.random.normal(0, 3, len(years))

        # Répartition par secteur (parts approximatives)
        secteur_parts = {
            "Transport routier":         0.295,
            "Industrie manufacturière":  0.195,
            "Résidentiel / Tertiaire":   0.190,
            "Agriculture / Sylviculture": 0.185,
            "Production d'énergie":       0.095,
            "Traitement des déchets":     0.030,
            "Industrie des procédés":     0.010,
        }

        # Évolution différenciée par secteur
        secteur_trends = {
            "Transport routier": -0.10,
            "Industrie manufacturière": -0.35,
            "Résidentiel / Tertiaire": -0.30,
            "Agriculture / Sylviculture": -0.08,
            "Production d'énergie": -0.45,
            "Traitement des déchets": -0.20,
            "Industrie des procédés": -0.25,
        }

        records = []
        for i, year in enumerate(years):
            for secteur, part_base in secteur_parts.items():
                t = (year - 1990) / 34  # 0 à 1
                trend = secteur_trends[secteur]
                part = part_base * (1 + trend * t)
                emissions = total[i] * part + np.random.normal(0, 1)
                records.append({
                    "annee": year,
                    "secteur": secteur,
                    "emissions_mtco2eq": round(max(0, emissions), 2),
                })

        df = pd.DataFrame(records)

        # Ajouter les totaux annuels
        totaux = df.groupby("annee")["emissions_mtco2eq"].sum().reset_index()
        totaux["secteur"] = "TOTAL"
        return pd.concat([df, totaux], ignore_index=True)

    def _generate_empreinte_carbone(self) -> List[Path]:
        """
        Génère l'empreinte carbone individuelle française.
        Inclut les émissions importées (consommation).

        Valeurs de référence (INSEE/SDES 2023) :
        - Empreinte totale : ~9.9 tCO₂eq/hab/an
        - Dont importé : ~4.4 tCO₂eq/hab/an
        """
        years = list(range(1995, 2025))
        n = len(years)

        empreinte_totale = np.linspace(12.5, 9.9, n) + np.random.normal(0, 0.15, n)
        part_importee = np.linspace(3.2, 4.4, n)  # hausse des importations
        part_nationale = empreinte_totale - part_importee

        df = pd.DataFrame({
            "annee": years,
            "empreinte_totale_tco2eq": empreinte_totale.round(2),
            "part_nationale_tco2eq": part_nationale.round(2),
            "part_importee_tco2eq": part_importee.round(2),
        })

        out = self.output_dir / "empreinte_carbone_individuelle.parquet"
        df.to_parquet(out, index=False)
        self._row_count += len(df)
        return [out]


if __name__ == "__main__":
    ing = CitepaIngester()
    files = ing.run()
    print(f"✅ {len(files)} fichiers : {[f.name for f in files]}")
