"""
fetch_georisques.py
===================
Récupère les données de l'API GeoRisques et génère des CSV.

Stratégie : requêtes par code_insee (pas de coordonnées GPS),
avec pagination page / page_size — seul mode stable de l'API v1.

Endpoints confirmés :
  GET /api/v1/gaspar/catnat?code_insee=XXXXX&page=1&page_size=500
  GET /api/v1/gaspar/risques?code_insee=XXXXX
  GET /api/v1/zonage-sismique?code_insee=XXXXX
  GET /api/v1/cavites?code_insee=XXXXX&page=1&page_size=500
  GET /api/v1/radon?code_insee=XXXXX

On itère sur la liste des ~35 000 communes françaises (récupérée depuis
l'API découpage administratif de data.gouv.fr) OU sur une liste réduite
de communes chefs-lieux si --dept est fourni.

Usage :
    python fetch_georisques.py --dept 35          # Ille-et-Vilaine (test rapide)
    python fetch_georisques.py --only catnat       # CatNat France entière
    python fetch_georisques.py                     # tout

Sorties dans data/raw/ :
    georisques_catnat.csv
    georisques_risques.csv
    georisques_sismique.csv
    georisques_cavites.csv
    georisques_radon.csv

Dépendances : pip install requests pandas loguru
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from loguru import logger

# ── Config ─────────────────────────────────────────────────────────────────
BASE_URL  = "https://georisques.gouv.fr/api/v1"
API_GEO   = "https://geo.api.gouv.fr"          # pour la liste des communes
DATA_RAW  = Path(__file__).parent / "data" / "raw"
DATA_RAW.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 500
SLEEP_SEC = 0.25   # politesse (limite : 1000 req/min par IP)

HEADERS = {
    "Accept":     "application/json",
    "User-Agent": "ClimaDash-Hackathon26/1.0",
}


# ╔══════════════════════════════════════════════════════════════╗
# ║  COMMUNES                                                   ║
# ╚══════════════════════════════════════════════════════════════╝

def get_communes(dept: str | None = None) -> list[dict]:
    """
    Retourne la liste des communes (code INSEE + nom) via l'API Découpage Admin.
    Si dept est fourni, filtre sur ce département.
    """
    logger.info(f"📋 Récupération des communes{'  dept='+dept if dept else ' (France entière)'}…")
    url = f"{API_GEO}/communes"
    params: dict = {"fields": "code,nom,codeDepartement", "format": "json", "geometry": "centre"}
    if dept:
        params["codeDepartement"] = dept

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        communes = resp.json()
        logger.success(f"   {len(communes):,} communes chargées")
        return communes
    except Exception as e:
        logger.error(f"Erreur chargement communes : {e}")
        return []


# ╔══════════════════════════════════════════════════════════════╗
# ║  HELPER GET                                                 ║
# ╚══════════════════════════════════════════════════════════════╝

def _get(endpoint: str, params: dict) -> dict | list | None:
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        code = getattr(resp, "status_code", "?")
        if code != 404:   # 404 = commune sans donnée → silence
            logger.debug(f"HTTP {code} — {endpoint} {params} | {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Réseau — {endpoint} | {e}")
    return None


def _extract_list(result: dict | list | None) -> list[dict]:
    """Extrait une liste depuis n'importe quelle forme de réponse."""
    if result is None:
        return []
    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    if isinstance(result, dict):
        for key in ("data", "features", "results", "items"):
            if key in result and isinstance(result[key], list):
                return [r for r in result[key] if isinstance(r, dict)]
        return [result] if result else []
    return []


def _fetch_paginated(endpoint: str, base_params: dict) -> list[dict]:
    """Pagine sur un endpoint GeoRisques avec page / page_size."""
    records: list[dict] = []
    page = 1
    while True:
        result = _get(endpoint, {**base_params, "page": page, "page_size": PAGE_SIZE})
        batch = _extract_list(result)
        if not batch:
            break
        records.extend(batch)
        total = None
        if isinstance(result, dict):
            total = result.get("total") or result.get("totalElements")
        if total and len(records) >= int(total):
            break
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        time.sleep(SLEEP_SEC)
    return records


# ╔══════════════════════════════════════════════════════════════╗
# ║  1. CATNAT                                                  ║
# ╚══════════════════════════════════════════════════════════════╝

CATNAT_RENAME = {
    "cod_commune":        "code_commune",  "codeCommune":       "code_commune",
    "lib_commune":        "commune",       "libelleCommune":    "commune",
    "cod_departement":    "departement",   "codeDepartement":   "departement",
    "lib_departement":    "lib_departement","libelleDepartement":"lib_departement",
    "lib_risque_jo":      "type_risque",   "libelleRisqueJo":   "type_risque",
    "dat_deb":            "date_debut",    "dateDebut":         "date_debut",
    "dat_fin":            "date_fin",      "dateFin":           "date_fin",
    "dat_pub_arrete":     "date_arrete",   "datePubArrete":     "date_arrete",
    "num_risque_jo":      "code_risque",   "numRisqueJo":       "code_risque",
}

RISQUE_COURT = {
    "Inondations et coulées de boue":                        "Inondation",
    "Mouvements de terrain":                                 "Mouvement terrain",
    "Sécheresse":                                            "Sécheresse",
    "Séismes":                                               "Séisme",
    "Vents cycloniques":                                     "Cyclone",
    "Chocs mécaniques liés à l'action des vagues":           "Submersion marine",
    "Avalanches":                                            "Avalanche",
    "Inondations, coulées de boue et mouvements de terrain": "Inondation+MvtTerrain",
}


def fetch_catnat(communes: list[dict]) -> pd.DataFrame:
    logger.info(f"=== CatNat ({len(communes):,} communes) ===")
    all_records: list[dict] = []
    seen: set = set()

    for i, c in enumerate(communes):
        code = c.get("code", "")
        if not code:
            continue
        records = _fetch_paginated("gaspar/catnat", {"code_insee": code})
        new = 0
        for r in records:
            key = (
                r.get("cod_commune", r.get("codeCommune", code)),
                r.get("dat_deb",     r.get("dateDebut", "")),
                r.get("num_risque_jo", r.get("numRisqueJo", "")),
            )
            if key not in seen:
                seen.add(key)
                all_records.append(r)
                new += 1
        if new:
            logger.debug(f"  {code} {c.get('nom','')} +{new}")
        if (i + 1) % 100 == 0:
            logger.info(f"  … {i+1}/{len(communes)} communes traitées — {len(all_records):,} arrêtés")
        time.sleep(SLEEP_SEC)

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    df = df.rename(columns={k: v for k, v in CATNAT_RENAME.items() if k in df.columns})
    for col in ["date_debut","date_fin","date_arrete"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "date_debut" in df.columns:
        df["annee"] = df["date_debut"].dt.year.astype("Int64")
        df["mois"]  = df["date_debut"].dt.month.astype("Int64")
    if "type_risque" in df.columns:
        df["type_risque_court"] = df["type_risque"].map(RISQUE_COURT).fillna(df["type_risque"])
    if "date_debut" in df.columns and "date_fin" in df.columns:
        df["duree_jours"] = (df["date_fin"] - df["date_debut"]).dt.days.clip(lower=0)

    logger.success(f"✅ CatNat : {len(df):,} arrêtés")
    return df


# ╔══════════════════════════════════════════════════════════════╗
# ║  2. RISQUES (multi-aléas par commune)                      ║
# ╚══════════════════════════════════════════════════════════════╝

def fetch_risques(communes: list[dict]) -> pd.DataFrame:
    """
    /api/v1/gaspar/risques?code_insee=XXXXX
    Retourne pour chaque commune la liste des types de risques présents.
    """
    logger.info(f"=== Risques par commune ({len(communes):,} communes) ===")
    all_records: list[dict] = []

    for i, c in enumerate(communes):
        code = c.get("code", "")
        nom  = c.get("nom", "")
        if not code:
            continue
        result = _get("gaspar/risques", {"code_insee": code})
        records = _extract_list(result)
        for r in records:
            r.setdefault("code_commune", code)
            r.setdefault("commune", nom)
            r.setdefault("departement", c.get("codeDepartement", ""))
            all_records.append(r)
        if (i + 1) % 200 == 0:
            logger.info(f"  … {i+1}/{len(communes)} communes — {len(all_records):,} entrées")
        time.sleep(SLEEP_SEC)

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    logger.success(f"✅ Risques communes : {len(df):,} entrées")
    return df


# ╔══════════════════════════════════════════════════════════════╗
# ║  3. ZONAGE SISMIQUE                                        ║
# ╚══════════════════════════════════════════════════════════════╝

SISMIQUE_RENAME = {
    "codeZone":       "zone_sismique",  "code_zone":      "zone_sismique",
    "libelleZone":    "lib_zone",       "libelle_zone":   "lib_zone",
    "niveauAlea":     "niveau_alea",    "niveau_alea":    "niveau_alea",
    "codeInsee":      "code_commune",   "code_insee":     "code_commune",
    "codeDepartement":"departement",    "code_departement":"departement",
}


def fetch_sismique(communes: list[dict]) -> pd.DataFrame:
    logger.info(f"=== Zonage sismique ({len(communes):,} communes) ===")
    all_records: list[dict] = []
    seen: set = set()

    for i, c in enumerate(communes):
        code = c.get("code", "")
        if not code:
            continue
        result = _get("zonage-sismique", {"code_insee": code})
        records = _extract_list(result)
        for r in records:
            key = (code, r.get("codeZone", r.get("code_zone", "")))
            if key not in seen:
                seen.add(key)
                r.setdefault("code_commune", code)
                r.setdefault("commune",      c.get("nom",""))
                r.setdefault("departement",  c.get("codeDepartement",""))
                all_records.append(r)
        if (i + 1) % 200 == 0:
            logger.info(f"  … {i+1}/{len(communes)} — {len(all_records):,} zones")
        time.sleep(SLEEP_SEC)

    if not all_records:
        return pd.DataFrame()
    df = pd.DataFrame(all_records)
    df = df.rename(columns={k: v for k, v in SISMIQUE_RENAME.items() if k in df.columns})
    logger.success(f"✅ Sismique : {len(df):,} enregistrements")
    return df


# ╔══════════════════════════════════════════════════════════════╗
# ║  4. CAVITÉS                                                 ║
# ╚══════════════════════════════════════════════════════════════╝

CAVITES_RENAME = {
    "idCavite":    "id_cavite",    "id_cavite":    "id_cavite",
    "typeCavite":  "type_cavite",  "type_cavite":  "type_cavite",
    "codeInsee":   "code_commune", "code_insee":   "code_commune",
    "coordWGS84X": "lon",          "coord_wgs84_x":"lon",
    "coordWGS84Y": "lat",          "coord_wgs84_y":"lat",
}


def fetch_cavites(communes: list[dict]) -> pd.DataFrame:
    logger.info(f"=== Cavités ({len(communes):,} communes) ===")
    all_records: list[dict] = []
    seen: set = set()

    for i, c in enumerate(communes):
        code = c.get("code", "")
        if not code:
            continue
        records = _fetch_paginated("cavites", {"code_insee": code})
        for r in records:
            key = r.get("idCavite", r.get("id_cavite", id(r)))
            if key not in seen:
                seen.add(key)
                r.setdefault("departement", c.get("codeDepartement",""))
                all_records.append(r)
        if (i + 1) % 200 == 0:
            logger.info(f"  … {i+1}/{len(communes)} — {len(all_records):,} cavités")
        time.sleep(SLEEP_SEC)

    if not all_records:
        return pd.DataFrame()
    df = pd.DataFrame(all_records)
    df = df.rename(columns={k: v for k, v in CAVITES_RENAME.items() if k in df.columns})
    for col in ["lat","lon"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    logger.success(f"✅ Cavités : {len(df):,} enregistrements")
    return df


# ╔══════════════════════════════════════════════════════════════╗
# ║  5. RADON                                                   ║
# ╚══════════════════════════════════════════════════════════════╝

def fetch_radon(communes: list[dict]) -> pd.DataFrame:
    """
    /api/v1/radon?code_insee=XXXXX
    Potentiel radon par commune (classe 1 / 2 / 3).
    """
    logger.info(f"=== Radon ({len(communes):,} communes) ===")
    all_records: list[dict] = []

    for i, c in enumerate(communes):
        code = c.get("code", "")
        if not code:
            continue
        result = _get("radon", {"code_insee": code})
        records = _extract_list(result)
        for r in records:
            r.setdefault("code_commune", code)
            r.setdefault("commune",     c.get("nom",""))
            r.setdefault("departement", c.get("codeDepartement",""))
            all_records.append(r)
        if (i + 1) % 500 == 0:
            logger.info(f"  … {i+1}/{len(communes)} — {len(all_records):,} résultats")
        time.sleep(SLEEP_SEC)

    if not all_records:
        return pd.DataFrame()
    df = pd.DataFrame(all_records)
    logger.success(f"✅ Radon : {len(df):,} communes")
    return df


# ╔══════════════════════════════════════════════════════════════╗
# ║  SAUVEGARDE                                                 ║
# ╚══════════════════════════════════════════════════════════════╝

def _save(df: pd.DataFrame, filename: str) -> None:
    path = DATA_RAW / filename
    df.to_csv(path, index=False, encoding="utf-8")
    logger.success(f"💾 {path}  ({len(df):,} lignes, {len(df.columns)} colonnes)")


# ╔══════════════════════════════════════════════════════════════╗
# ║  MAIN                                                       ║
# ╚══════════════════════════════════════════════════════════════╝

def run(only: str | None = None, dept: str | None = None) -> None:
    communes = get_communes(dept=dept)
    if not communes:
        logger.error("Impossible de récupérer la liste des communes.")
        sys.exit(1)

    logger.info(f"→ {len(communes):,} communes à traiter")
    summary: list[str] = []

    if only in (None, "catnat"):
        df = fetch_catnat(communes)
        if not df.empty:
            _save(df, "georisques_catnat.csv")
            summary.append(f"catnat   : {len(df):>7,} lignes")

    if only in (None, "risques"):
        df = fetch_risques(communes)
        if not df.empty:
            _save(df, "georisques_risques.csv")
            summary.append(f"risques  : {len(df):>7,} lignes")

    if only in (None, "sismique"):
        df = fetch_sismique(communes)
        if not df.empty:
            _save(df, "georisques_sismique.csv")
            summary.append(f"sismique : {len(df):>7,} lignes")

    if only in (None, "cavites"):
        df = fetch_cavites(communes)
        if not df.empty:
            _save(df, "georisques_cavites.csv")
            summary.append(f"cavites  : {len(df):>7,} lignes")

    if only in (None, "radon"):
        df = fetch_radon(communes)
        if not df.empty:
            _save(df, "georisques_radon.csv")
            summary.append(f"radon    : {len(df):>7,} lignes")

    logger.info("\n📋 Résumé :")
    for line in summary:
        logger.info(f"   {line}")

    if not summary:
        logger.error("Aucune donnée récupérée.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Données GeoRisques → CSV")
    parser.add_argument(
        "--only",
        choices=["catnat", "risques", "sismique", "cavites", "radon"],
        default=None,
        help="Endpoint unique (défaut : tous)",
    )
    parser.add_argument(
        "--dept", type=str, default=None,
        help="Code département ex: '35'. Défaut : France entière.",
    )
    args = parser.parse_args()
    run(only=args.only, dept=args.dept)
