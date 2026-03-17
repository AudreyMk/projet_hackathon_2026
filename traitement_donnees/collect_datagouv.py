"""
Pôle data.gouv.fr — Météo-France quotidien/mensuel + BDIFF incendies
=====================================================================
Exécution autonome :
    python collect_datagouv.py
"""

import gzip
import io
import time
import requests
import pandas as pd

from config import DATAGOUV_API, DATAGOUV_SOURCES, CACHE_DIR
from helpers import section, save_csv, setup_dirs


# ── Helpers internes ──────────────────────────────────────────────────────────

def _datagouv_resources(slug: str) -> list[dict]:
    resp = requests.get(f"{DATAGOUV_API}/datasets/{slug}/", timeout=30)
    resp.raise_for_status()
    return resp.json().get("resources", [])


def _is_data_resource(resource: dict, filter_ext: str) -> bool:
    title = resource.get("title", "").lower()
    fmt   = resource.get("format", "").lower()
    ext   = filter_ext.lstrip(".")
    return fmt == ext or title.endswith(filter_ext.lower())


def _fetch_one(resource: dict, cache_dir, filter_ext: str) -> pd.DataFrame | None:
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


# ── Collecteur principal ──────────────────────────────────────────────────────

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


if __name__ == "__main__":
    setup_dirs()
    collect_datagouv()
