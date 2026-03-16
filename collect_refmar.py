"""
Pôle SHOM / Refmar — Niveaux marégraphiques
============================================

L'API Refmar utilise le protocole SOS (Sensor Observation Service).
Les stations sont identifiées par des IDs numériques (ex: 3 = Brest),
lus depuis stations_refmar.csv (généré par list_stations.py).

Référence : https://refmar.shom.fr/donnees/<ID>
Documentation API : https://services.data.shom.fr/maregraphie/service/help

⚠️  Limite : 31 jours max par requête.

Prérequis :
    python list_stations.py   # génère stations_refmar.csv

Exécution autonome :
    python collect_refmar.py
"""

import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

from config import REFMAR_API, REFMAR_OUTPUT
from helpers import section, save_csv, setup_dirs

STATIONS_CSV      = Path("stations_refmar.csv")
REFMAR_DATE_END   = datetime.utcnow()
REFMAR_DATE_START = REFMAR_DATE_END - timedelta(days=30)


# ── Chargement des stations depuis le CSV ─────────────────────────────────────

def _load_stations() -> list[dict]:
    """Lit stations_refmar.csv et retourne une liste de dicts {Code, Nom, ...}."""
    if not STATIONS_CSV.exists():
        print(f"  ❌ Fichier introuvable : {STATIONS_CSV}")
        print("      → Lancez d'abord : python list_stations.py")
        return []

    df = pd.read_csv(STATIONS_CSV, sep=";", dtype=str)

    # Colonnes attendues : Code, Nom, Latitude, Longitude
    if "Code" not in df.columns:
        print(f"  ❌ Colonne 'Code' absente dans {STATIONS_CSV}")
        return []

    df.dropna(subset=["Code"], inplace=True)
    # Les IDs Refmar sont numériques — on cast proprement
    try:
        df["Code"] = df["Code"].astype(float).astype(int)
    except ValueError:
        print("  ⚠️  Impossible de convertir les codes en entiers — vérifiez le CSV.")
        return []

    stations = df.to_dict(orient="records")
    print(f"  📂 {len(stations)} stations chargées depuis {STATIONS_CSV}")
    return stations


# ── Collecte observations ─────────────────────────────────────────────────────

def _fetch_station(station_id: int, nom: str,
                   dt_start: datetime, dt_end: datetime) -> list[dict]:
    """Interroge le service SOS Refmar pour une station sur une période."""
    rows = []
    try:
        resp = requests.get(
            f"{REFMAR_API}/{station_id}",
            params={
                "sources": 1,
                "dtStart": dt_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "dtEnd":   dt_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        observations = (
            data.get("observations")
            or data.get("data")
            or data.get("values")
            or []
        )
        for obs in observations:
            rows.append({
                "station_id": station_id,
                "nom":        nom,
                "datetime":   obs.get("date") or obs.get("timestamp") or obs.get("t"),
                "niveau_m":   obs.get("value") or obs.get("v") or obs.get("hauteur"),
                "qualite":    obs.get("quality") or obs.get("qualite"),
            })
    except Exception as e:
        print(f"             ❌ Station {station_id} : {e}")
    return rows


# ── Collecteur principal ──────────────────────────────────────────────────────

def collect_refmar() -> Path | None:
    section("PÔLE SHOM / Refmar")

    stations = _load_stations()
    if not stations:
        return None

    print(f"  📅 Période : {REFMAR_DATE_START:%Y-%m-%d} → {REFMAR_DATE_END:%Y-%m-%d}")
    print(f"  📡 {len(stations)} station(s) à collecter\n")

    all_rows = []
    for i, sta in enumerate(stations, 1):
        sid = sta["Code"]
        nom = sta.get("Nom", f"ID {sid}")
        print(f"  [{i:>3}/{len(stations)}] {sid:>5} — {nom}")
        rows = _fetch_station(sid, nom, REFMAR_DATE_START, REFMAR_DATE_END)
        if rows:
            all_rows.extend(rows)
            print(f"             → {len(rows):,} mesures")
        else:
            print(f"             ⚠️  Aucune mesure")
        time.sleep(0.2)

    if not all_rows:
        print("\n  ❌ Aucune donnée récupérée.")
        print("  ℹ️  Vérifiez que les IDs sont corrects : https://refmar.shom.fr/donnees/<ID>")
        return None

    df = pd.DataFrame(all_rows)
    print(f"\n  🔗 Total : {len(df):,} mesures")
    return save_csv(df, "shom_refmar", REFMAR_OUTPUT)


if __name__ == "__main__":
    setup_dirs()
    collect_refmar()
