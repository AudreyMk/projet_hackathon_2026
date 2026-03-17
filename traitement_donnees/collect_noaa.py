"""
Pôle NOAA GML — CO₂ et CH₄ atmosphériques
==========================================
Exécution autonome :
    python collect_noaa.py
"""

import io
import requests
import pandas as pd

from config import NOAA_SOURCES, CACHE_DIR
from helpers import section, save_csv, setup_dirs


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


if __name__ == "__main__":
    setup_dirs()
    collect_noaa()
