"""
Pôle Vigicrues / Hub'Eau — Hauteurs et débits hydrologiques
============================================================

Sources :
  - Liste des stations : stations_vigicrues.csv  (généré par list_stations.py)
  - Observations       : API Hub'Eau v2  → hubeau.eaufrance.fr

L'API Hub'Eau maintient 1 mois d'historique temps-réel (màj toutes les 5 min)
+ observations élaborées (débits journaliers/mensuels) depuis 1900.

Prérequis :
    python list_stations.py   # génère stations_vigicrues.csv

Exécution autonome :
    python collect_vigicrues.py
"""

import time
import requests
import pandas as pd
from pathlib import Path

from config import VIGICRUES_OUTPUT
from helpers import section, save_csv, setup_dirs

HUBEAU_API          = "https://hubeau.eaufrance.fr/api/v2/hydrometrie"
STATIONS_CSV        = Path("stations_vigicrues.csv")


# ── Chargement des stations depuis le CSV ─────────────────────────────────────

def _load_stations() -> list[dict]:
    """Lit stations_vigicrues.csv et retourne une liste de dicts {code, nom, ...}."""
    if not STATIONS_CSV.exists():
        print(f"  ❌ Fichier introuvable : {STATIONS_CSV}")
        print("      → Lancez d'abord : python list_stations.py")
        return []

    df = pd.read_csv(STATIONS_CSV, sep=";", dtype=str)

    # Colonnes attendues : Code, Nom, Cours_deau, Departement, Num_dept, Longitude, Latitude
    if "Code" not in df.columns:
        print(f"  ❌ Colonne 'Code' absente dans {STATIONS_CSV}")
        return []

    df.dropna(subset=["Code"], inplace=True)
    stations = df.to_dict(orient="records")
    print(f"  📂 {len(stations)} stations chargées depuis {STATIONS_CSV}")
    return stations


# ── Collecte observations ─────────────────────────────────────────────────────

def _fetch_observations(code: str) -> list[dict]:
    """Récupère les observations temps-réel d'une station via Hub'Eau."""
    rows = []
    try:
        resp = requests.get(
            f"{HUBEAU_API}/observations_tr",
            params={
                "code_entite":    code,
                "grandeur_hydro": "H",
                "size":           1000,
                "sort":           "desc",
            },
            timeout=30,
        )
        resp.raise_for_status()
        for obs in resp.json().get("data", []):
            rows.append({
                "CdStation":  code,
                "DateObs":    obs.get("date_obs"),
                "Valeur":     obs.get("resultat_obs"),
                "Qualif":     obs.get("qualification_obs"),
                "Continuite": obs.get("continuite_obs_hydro"),
            })
    except Exception as e:
        print(f"             ❌ Hub'Eau {code} : {e}")
    return rows


# ── Collecteur principal ──────────────────────────────────────────────────────

def collect_vigicrues() -> Path | None:
    section("PÔLE Vigicrues / Hub'Eau")

    stations = _load_stations()
    if not stations:
        return None

    all_rows = []
    for i, sta in enumerate(stations, 1):
        code = sta["Code"]
        nom  = sta.get("Nom", "")
        dept = sta.get("Departement", "")
        print(f"  [{i:>4}/{len(stations)}] {code}  {nom}  ({dept})")
        rows = _fetch_observations(code)
        if rows:
            all_rows.extend(rows)
            print(f"             → {len(rows):,} observations")
        time.sleep(0.05)

    if not all_rows:
        print("  ❌ Aucune observation récupérée.")
        return None

    df = pd.DataFrame(all_rows)
    print(f"\n  🔗 Total : {len(df):,} observations")
    return save_csv(df, "vigicrues", VIGICRUES_OUTPUT)


if __name__ == "__main__":
    setup_dirs()
    collect_vigicrues()
