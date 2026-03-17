"""
config/settings.py
==================
Configuration centrale du projet Hackathon #26 — Changement Climatique.
Modifier ce fichier pour adapter le projet au territoire d'étude.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict

# ─────────────────────────────────────────────
# 📁 CHEMINS
# ─────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"
REPORTS_DIR = ROOT_DIR / "reports"
MLFLOW_DIR = ROOT_DIR / "mlflow_runs"

# Créer les dossiers si besoin
for d in [RAW_DIR, PROCESSED_DIR, EXTERNAL_DIR, REPORTS_DIR, MLFLOW_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# 🗺️  TERRITOIRE D'ÉTUDE
# ─────────────────────────────────────────────
@dataclass
class Territory:
    """Définit le territoire d'analyse."""
    name: str = "France"
    level: str = "national"          # "national" | "regional" | "commune"
    region_code: str = None          # Ex: "11" (Île-de-France)
    commune_insee: str = None        # Ex: "75056" (Paris)
    bbox: Dict = field(default_factory=lambda: {
        "lat_min": 41.0, "lat_max": 51.5,
        "lon_min": -5.5, "lon_max": 10.0
    })

# 👇 CHANGER ICI selon votre territoire
TERRITORY = Territory(
    name="France",
    level="national",
)

# Exemples commentés :
# TERRITORY = Territory(name="Île-de-France", level="regional", region_code="11")
# TERRITORY = Territory(name="Paris", level="commune", commune_insee="75056")


# ─────────────────────────────────────────────
# 📅 PÉRIODES TEMPORELLES
# ─────────────────────────────────────────────
HISTORICAL_START_YEAR = 1900
HISTORICAL_END_YEAR = 2024
PROJECTION_YEARS = [2030, 2050, 2100]

# Scénarios GIEC (SSP = Shared Socioeconomic Pathways)
SCENARIOS = {
    "optimiste":     {"label": "SSP1-2.6",  "delta_temp": +1.4, "color": "#2ecc71"},
    "intermediaire": {"label": "SSP2-4.5",  "delta_temp": +2.7, "color": "#f39c12"},
    "pessimiste":    {"label": "SSP5-8.5",  "delta_temp": +4.4, "color": "#e74c3c"},
}


# ─────────────────────────────────────────────
# 📊 INDICATEURS CLIMATIQUES
# ─────────────────────────────────────────────
INDICATORS = {
    # --- Évolution climatique ---
    "temp_moyenne_annuelle": {
        "label": "Température moyenne annuelle (°C)",
        "source": "meteofrance",
        "unit": "°C",
        "category": "evolution",
        "narrative_score": 10,   # Potentiel narratif /10
    },
    "jours_chauds_30": {
        "label": "Nombre de jours > 30°C",
        "source": "meteofrance",
        "unit": "jours/an",
        "category": "evolution",
        "narrative_score": 9,
    },
    "jours_gel": {
        "label": "Nombre de jours de gel (T < 0°C)",
        "source": "meteofrance",
        "unit": "jours/an",
        "category": "evolution",
        "narrative_score": 7,
    },
    "precipitations_annuelles": {
        "label": "Précipitations annuelles (mm)",
        "source": "meteofrance",
        "unit": "mm",
        "category": "evolution",
        "narrative_score": 7,
    },
    "niveau_mers": {
        "label": "Niveau des mers (mm vs 1990)",
        "source": "psmsl",
        "unit": "mm",
        "category": "evolution",
        "narrative_score": 9,
    },
    # --- Pressions humaines ---
    "co2_concentration": {
        "label": "Concentration CO₂ atmosphérique (ppm)",
        "source": "noaa",
        "unit": "ppm",
        "category": "pression_humaine",
        "narrative_score": 10,
    },
    "ges_total_france": {
        "label": "Émissions GES totales France (MtCO₂eq)",
        "source": "citepa",
        "unit": "MtCO₂eq",
        "category": "pression_humaine",
        "narrative_score": 9,
    },
    "empreinte_carbone_individuelle": {
        "label": "Empreinte carbone par habitant (tCO₂eq/an)",
        "source": "insee_sdes",
        "unit": "tCO₂eq/hab",
        "category": "pression_humaine",
        "narrative_score": 10,
    },
    # --- Impacts visibles ---
    "feux_foret_surfaces": {
        "label": "Surfaces brûlées feux de forêt (ha)",
        "source": "bdiff",
        "unit": "ha",
        "category": "impact_visible",
        "narrative_score": 9,
    },
    "depart_vendanges": {
        "label": "Date de départ des vendanges (jour julien)",
        "source": "inrae",
        "unit": "jour",
        "category": "impact_visible",
        "narrative_score": 8,
    },
}


# ─────────────────────────────────────────────
# 🤖 MODÈLES IA
# ─────────────────────────────────────────────
MODEL_CONFIG = {
    "arima": {
        "enabled": True,
        "auto_order": True,
        "max_p": 5, "max_d": 2, "max_q": 5,
        "seasonal": True,
        "m": 12,  # saisonnalité mensuelle
    },
    "prophet": {
        "enabled": True,
        "changepoint_prior_scale": 0.05,
        "seasonality_mode": "multiplicative",
        "yearly_seasonality": True,
    },
    "lstm": {
        "enabled": True,
        "sequence_length": 10,
        "units": [64, 32],
        "dropout": 0.2,
        "epochs": 100,
        "batch_size": 32,
        "patience": 15,
    },
    "gradient_boosting": {
        "enabled": True,
        "engine": "xgboost",   # "xgboost" | "lightgbm"
        "n_estimators": 500,
        "max_depth": 6,
        "learning_rate": 0.05,
        "n_lags": 12,
    },
}

# Métrique principale de comparaison
EVALUATION_METRICS = ["rmse", "mae", "mape", "r2"]
PRIMARY_METRIC = "rmse"

# Ratio train/test
TEST_SIZE = 0.2
RANDOM_STATE = 42


# ─────────────────────────────────────────────
# 🌐 SOURCES DE DONNÉES
# ─────────────────────────────────────────────
DATA_SOURCES = {
    "meteofrance": {
        "base_url": "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets",
        "dataset_clim": "donnees-climatologiques-de-base-quotidiennes",
        "dataset_ref": "valeurs-climatologiques-de-reference-mensuelles",
    },
    "noaa_co2": {
        "url_monthly": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt",
        "url_annual": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.txt",
    },
    "citepa": {
        "url": "https://www.citepa.org/wp-content/uploads/Secten_ed2024_a.xlsx",
    },
    "drias": {
        "base_url": "https://www.drias-climat.fr/",
        "note": "Nécessite une inscription. Données RCP/SSP disponibles.",
    },
}


# ─────────────────────────────────────────────
# 🖥️  DASHBOARD
# ─────────────────────────────────────────────
DASHBOARD_CONFIG = {
    "title": "🌍 ClimaDash — Analyse Climatique France",
    "theme": "dark",
    "map_center": [46.6, 2.3],
    "map_zoom": 5,
    "primary_color": "#6c5ce7",
    "alert_thresholds": {
        "temp_anomalie_critique": 2.0,   # °C au-dessus de la normale
        "co2_alerte": 450,               # ppm
        "jours_chauds_alerte": 30,       # jours/an
    },
}


# ─────────────────────────────────────────────
# 📋 LOGGING
# ─────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE = ROOT_DIR / "logs" / "pipeline.log"
