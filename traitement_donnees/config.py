"""
Configuration centrale — Collecte climatologique multi-sources
==============================================================
Adaptez ce fichier selon vos besoins avant de lancer les collecteurs.
"""

from pathlib import Path

# ── Répertoires ───────────────────────────────────────────────────────────────
ROOT_DIR  = Path("./outputs_climat")
CACHE_DIR = Path("./cache_multi_sources")

# Sous-dossiers par pôle (créés automatiquement par setup_dirs)
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
