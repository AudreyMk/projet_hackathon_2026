"""
Utilitaires partagés — création des répertoires, sauvegarde CSV, affichage.
"""

from pathlib import Path
import pandas as pd
from config import CACHE_DIR, POLES


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
