"""
Téléchargement et consolidation de données climatologiques multi-sources
========================================================================

Arborescence produite :

  outputs_climat/
  ├── datagouv/
  │   ├── meteo_quotidien_france.csv
  │   ├── meteo_mensuel_france.csv
  │   └── bdiff_incendies.csv
  ├── vigicrues/
  │   └── vigicrues_hauteurs.csv
  ├── shom_refmar/
  │   └── refmar_niveaux_mer.csv
  └── noaa/
      ├── noaa_co2_mauna_loa.csv
      └── noaa_ch4_global.csv

Sources :
  [A] data.gouv.fr  – Météo-France quotidien   (csv.gz par département)
  [B] data.gouv.fr  – Météo-France mensuel     (csv.gz par département)
  [C] data.gouv.fr  – BDIFF incendies de forêt (csv)
  [D] Vigicrues     – Hauteurs/débits hydrologiques (JSON REST)
  [E] SHOM / Refmar – Niveaux marégraphiques   (JSON REST)
  [F] NOAA GML      – CO₂ atmosphérique global (txt → csv)
  [G] NOAA GML      – CH₄ atmosphérique global (txt → csv)

Licences :
  Météo-France / data.gouv.fr → Licence Ouverte 2.0
  BDIFF / data.gouv.fr        → Licence Ouverte 2.0
  Vigicrues                   → Licence Ouverte 2.0
  SHOM / Refmar               → Licence Ouverte 2.0
  NOAA GML                    → Données publiques (US Government)

Sources NON-automatisables (consultation manuelle) :
  – DRIAS-Climat  : portail interactif, pas d'API publique ouverte
  – CITEPA Secten : données en PDF/Excel, téléchargement manuel
  – INSEE 8654458 : extraction HTML complexe
  – SDES empreinte carbone : tableaux HTML/Excel manuels
  – GéoRisques    : portail carto (WMS/WFS très volumineux)
"""

import gzip
import io
import os
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — adaptez selon vos besoins
# ═══════════════════════════════════════════════════════════════════════════════

# Racine de tous les outputs et du cache
ROOT_DIR  = Path("./outputs_climat")
CACHE_DIR = Path("./cache_multi_sources")

# Sous-dossiers par pôle (créés automatiquement)
POLES = {
    "datagouv":    ROOT_DIR / "datagouv",
    "vigicrues":   ROOT_DIR / "vigicrues",
    "shom_refmar": ROOT_DIR / "shom_refmar",
    "noaa":        ROOT_DIR / "noaa",
}

# ── Pôle data.gouv.fr ─────────────────────────────────────────────────────────
DATAGOUV_API = "https://www.data.gouv.fr/api/1"

DATAGOUV_SOURCES = {
    "meteo_quotidien": {
        "slug":        "donnees-climatologiques-de-base-quotidiennes",
        "description": "Météo-France – Données quotidiennes",
        "output":      "meteo_quotidien_france.csv",
        "filter_ext":  ".csv.gz",
    },
    "meteo_mensuel": {
        "slug":        "donnees-climatologiques-de-base-mensuelles",
        "description": "Météo-France – Données mensuelles",
        "output":      "meteo_mensuel_france.csv",
        "filter_ext":  ".csv.gz",
    },
    "bdiff_incendies": {
        "slug":        "base-de-donnees-sur-les-incendies-de-forets-en-france-bdiff",
        "description": "BDIFF – Incendies de forêts en France",
        "output":      "bdiff_incendies.csv",
        "filter_ext":  ".csv",
    },
}

# ── Pôle Vigicrues ────────────────────────────────────────────────────────────
# Laissez [] pour récupérer TOUTES les stations (très long).
# Codes disponibles sur https://www.vigicrues.gouv.fr/
VIGICRUES_STATIONS = [
    # "J0344010",   # La Vilaine à Rennes
    # "K2673310",   # La Loire à Nantes
    # "O9999010",   # La Seine à Paris-Austerlitz
]
VIGICRUES_API    = "https://www.vigicrues.gouv.fr/services/v1.1"
VIGICRUES_OUTPUT = "vigicrues_hauteurs.csv"

# ── Pôle SHOM / Refmar ────────────────────────────────────────────────────────
# Codes disponibles sur https://data.shom.fr/refmar
REFMAR_STATIONS = [
    # "BREST",
    # "ST_MALO",
    # "SAINT_NAZAIRE",
]
REFMAR_API    = "https://services.data.shom.fr/support/fr/services/refmar"
REFMAR_OUTPUT = "refmar_niveaux_mer.csv"

# ── Pôle NOAA GML ─────────────────────────────────────────────────────────────
NOAA_SOURCES = {
    "co2_global": {
        "url":          "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt",
        "description":  "NOAA GML – CO₂ mensuel (Mauna Loa)",
        "output":       "noaa_co2_mauna_loa.csv",
        "comment_char": "#",
        "col_names":    ["year", "month", "decimal_date", "average",
                         "deseasonalized", "ndays", "sdev", "unc"],
    },
    "ch4_global": {
        "url":          "https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.txt",
        "description":  "NOAA GML – CH₄ mensuel (global)",
        "output":       "noaa_ch4_global.csv",
        "comment_char": "#",
        "col_names":    ["year", "month", "decimal_date", "average",
                         "average_unc", "trend", "trend_unc"],
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def setup_dirs():
    """Crée l'arborescence complète outputs + cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    for pole, path in POLES.items():
        path.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / pole).mkdir(exist_ok=True)


def save_csv(df: pd.DataFrame, pole: str, filename: str, sep: str = ";") -> Path:
    """Sauvegarde un DataFrame dans le sous-dossier du pôle."""
    path = POLES[pole] / filename
    df.to_csv(path, index=False, encoding="utf-8-sig", sep=sep)
    size_mb = path.stat().st_size / 1_048_576
    print(f"   💾  {path}  ({size_mb:.2f} Mo — {len(df):,} lignes)")
    return path


def section(title: str):
    print(f"\n{'═' * 64}")
    print(f"  {title}")
    print(f"{'═' * 64}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PÔLE data.gouv.fr
# ═══════════════════════════════════════════════════════════════════════════════

def _datagouv_resources(slug: str) -> list[dict]:
    resp = requests.get(f"{DATAGOUV_API}/datasets/{slug}/", timeout=30)
    resp.raise_for_status()
    return resp.json().get("resources", [])


def _is_data_resource(resource: dict, filter_ext: str) -> bool:
    title = resource.get("title", "").lower()
    fmt   = resource.get("format", "").lower()
    ext   = filter_ext.lstrip(".")
    return fmt == ext or title.endswith(filter_ext.lower())


def _fetch_one(resource: dict, cache_dir: Path, filter_ext: str) -> pd.DataFrame | None:
    title   = resource.get("title", "inconnu")
    url     = resource.get("url")
    file_id = resource.get("id", "")
    if not url:
        return None

    suffix     = ".csv.gz" if filter_ext == ".csv.gz" else ".csv"
    cache_file = cache_dir / f"{file_id}{suffix}"

    if cache_file.exists():
        raw = cache_file.read_bytes()
    else:
        try:
            resp = requests.get(url, timeout=120, stream=True)
            resp.raise_for_status()
            raw = resp.content
            cache_file.write_bytes(raw)
        except Exception as e:
            print(f"      ❌  Téléchargement {title} : {e}")
            return None

    try:
        if filter_ext == ".csv.gz":
            with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8-sig",
                           errors="replace") as f:
                df = pd.read_csv(f, sep=";", low_memory=False)
        else:
            df = pd.read_csv(io.BytesIO(raw), sep=";", encoding="utf-8-sig",
                             low_memory=False)
        df["NOM_FICHIER"] = title
        return df
    except Exception as e:
        print(f"      ❌  Lecture {title} : {e}")
        return None


def collect_datagouv() -> dict:
    section("PÔLE data.gouv.fr")
    results = {}

    for key, cfg in DATAGOUV_SOURCES.items():
        print(f"\n  ▸ {cfg['description']}  [{cfg['slug']}]")
        cache_sub = CACHE_DIR / "datagouv" / key
        cache_sub.mkdir(exist_ok=True)

        resources = _datagouv_resources(cfg["slug"])
        data_res  = [r for r in resources if _is_data_resource(r, cfg["filter_ext"])]
        print(f"    📦 {len(data_res)} fichiers trouvés")

        if not data_res:
            print("    ⚠️  Aucun fichier. Vérifiez le slug ou la connexion.")
            continue

        frames = []
        for i, res in enumerate(data_res, 1):
            title = res.get("title", "?")
            print(f"    [{i:>3}/{len(data_res)}] {title}")
            df = _fetch_one(res, cache_sub, cfg["filter_ext"])
            if df is not None:
                frames.append(df)
                print(f"              → {len(df):,} lignes")
            time.sleep(0.1)

        if not frames:
            print("    ❌ Aucune donnée collectée.")
            continue

        full = pd.concat(frames, ignore_index=True, sort=False)
        full.dropna(axis=1, how="all", inplace=True)
        print(f"\n    🔗 Consolidé : {len(full):,} lignes — {len(full.columns)} colonnes")
        results[key] = save_csv(full, "datagouv", cfg["output"])

    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  PÔLE Vigicrues
# ═══════════════════════════════════════════════════════════════════════════════

def collect_vigicrues() -> Path | None:
    section("PÔLE Vigicrues")

    stations = list(VIGICRUES_STATIONS)

    if not stations:
        print("  🔍 Récupération de la liste des stations...")
        try:
            resp     = requests.get(f"{VIGICRUES_API}/TronconVigiCru.json", timeout=60)
            resp.raise_for_status()
            troncons = resp.json().get("TronconVigiCru", [])
            seen     = set()
            for t in troncons:
                for s in t.get("LisSta", []):
                    code = s.get("CdStationHydro")
                    if code and code not in seen:
                        stations.append(code)
                        seen.add(code)
            print(f"  ✅ {len(stations)} stations trouvées")
        except Exception as e:
            print(f"  ❌ Impossible de lister les stations : {e}")
            return None

    if not stations:
        print("  ⚠️  Aucune station à traiter.")
        return None

    all_rows = []
    for i, code in enumerate(stations, 1):
        print(f"  [{i:>4}/{len(stations)}] Station {code}")
        try:
            url  = (f"{VIGICRUES_API}/Observations.json/"
                    f"?CdStationHydro={code}&GrdSerie=H")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            for obs in resp.json().get("Serie", {}).get("ObssHydro", []):
                all_rows.append({
                    "CdStation": code,
                    "DateObs":   obs.get("DtObsHydro"),
                    "Valeur":    obs.get("ResObsHydro"),
                    "Qualif":    obs.get("QualifObsHydro"),
                })
        except Exception as e:
            print(f"             ❌ {e}")
        time.sleep(0.05)

    if not all_rows:
        print("  ❌ Aucune observation récupérée.")
        return None

    df = pd.DataFrame(all_rows)
    print(f"\n  🔗 Total : {len(df):,} observations")
    return save_csv(df, "vigicrues", VIGICRUES_OUTPUT)


# ═══════════════════════════════════════════════════════════════════════════════
#  PÔLE SHOM / Refmar
# ═══════════════════════════════════════════════════════════════════════════════

def collect_refmar() -> Path | None:
    section("PÔLE SHOM / Refmar")

    if not REFMAR_STATIONS:
        print("  ℹ️  Aucune station configurée dans REFMAR_STATIONS.")
        print("      → Renseignez des codes depuis https://data.shom.fr/refmar")
        return None

    all_rows = []
    for code in REFMAR_STATIONS:
        print(f"  📡 Station {code}")
        try:
            url  = f"{REFMAR_API}/observations?station={code}&format=json"
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            for obs in resp.json().get("observations", []):
                all_rows.append({
                    "station":  code,
                    "datetime": obs.get("date"),
                    "niveau_m": obs.get("value"),
                })
        except Exception as e:
            print(f"         ❌ {e}")
        time.sleep(0.1)

    if not all_rows:
        print("  ⚠️  Aucune donnée (vérifiez les codes stations).")
        return None

    df = pd.DataFrame(all_rows)
    print(f"\n  🔗 Total : {len(df):,} mesures")
    return save_csv(df, "shom_refmar", REFMAR_OUTPUT)


# ═══════════════════════════════════════════════════════════════════════════════
#  PÔLE NOAA GML
# ═══════════════════════════════════════════════════════════════════════════════

def collect_noaa() -> dict:
    section("PÔLE NOAA GML")
    results = {}

    for key, cfg in NOAA_SOURCES.items():
        print(f"\n  ▸ {cfg['description']}")
        cache_file = CACHE_DIR / "noaa" / f"{key}.txt"

        if cache_file.exists():
            content = cache_file.read_text(encoding="utf-8")
            print("    📂 Chargé depuis le cache")
        else:
            try:
                resp = requests.get(cfg["url"], timeout=60)
                resp.raise_for_status()
                content = resp.text
                cache_file.write_text(content, encoding="utf-8")
                print(f"    ✅ Téléchargé ({len(content):,} caractères)")
            except Exception as e:
                print(f"    ❌ Erreur téléchargement : {e}")
                continue

        lines = [l for l in content.splitlines()
                 if l.strip() and not l.strip().startswith(cfg["comment_char"])]
        if not lines:
            print("    ❌ Aucune donnée trouvée.")
            continue

        try:
            df = pd.read_csv(
                io.StringIO("\n".join(lines)),
                sep=r"\s+",
                header=None,
                names=cfg["col_names"],
            )
            df.replace([-99.99, -999.99, -9.99], pd.NA, inplace=True)
            print(f"    🔗 {len(df):,} lignes — colonnes : {list(df.columns)}")
            results[key] = save_csv(df, "noaa", cfg["output"])
        except Exception as e:
            print(f"    ❌ Erreur parsing : {e}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
#  PROGRAMME PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    setup_dirs()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'═' * 64}")
    print(f"  Collecte climatologique multi-sources — {ts}")
    print(f"{'═' * 64}")

    all_results: dict[str, Path] = {}

    all_results.update(collect_datagouv())

    p = collect_vigicrues()
    if p:
        all_results["vigicrues"] = p

    p = collect_refmar()
    if p:
        all_results["shom_refmar"] = p

    all_results.update(collect_noaa())

    # ── Récapitulatif en arbre ─────────────────────────────────────────────────
    print(f"\n{'═' * 64}")
    print("  RÉCAPITULATIF — fichiers produits")
    print(f"{'═' * 64}")
    print(f"\n  📁 {ROOT_DIR}/")

    if all_results:
        by_pole: dict[str, list[Path]] = {}
        for path in all_results.values():
            by_pole.setdefault(path.parent.name, []).append(path)

        for pole in sorted(by_pole):
            print(f"  ├── {pole}/")
            paths = sorted(by_pole[pole])
            for i, p in enumerate(paths):
                size_mb  = p.stat().st_size / 1_048_576
                branch   = "└──" if i == len(paths) - 1 else "├──"
                print(f"  │   {branch} ✅  {p.name:<40} {size_mb:>6.2f} Mo")
    else:
        print("  └── (aucun fichier produit)")

    print(f"\n  ⚠️  Sources à traiter manuellement :")
    manual = [
        ("DRIAS-Climat",   "https://www.drias-climat.fr/                   portail interactif"),
        ("CITEPA Secten",  "https://www.citepa.org/                        PDF / Excel"),
        ("INSEE 8654458",  "https://www.insee.fr/fr/statistiques/8654458"),
        ("SDES empreinte", "https://statistiques.developpement-durable.gouv.fr/empreinte-carbone-2"),
        ("GéoRisques",     "https://www.georisques.gouv.fr/                WMS/WFS carto"),
    ]
    for name, url in manual:
        print(f"     – {name:<18}  {url}")
    print()


if __name__ == "__main__":
    main()