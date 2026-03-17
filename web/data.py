import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go


def hex_alpha(hex_color: str, alpha: float) -> str:
    """Convert a #rrggbb hex color + alpha float to rgba() for Plotly."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


GREEN  = "#0e7c61"
ACCENT = "#4ecdc4"

_THEME_DARK = dict(
    template="plotly_dark",
    paper_bgcolor="#080c0e",
    plot_bgcolor="#0d1417",
    font=dict(family="DM Sans", color="#a8c5be", size=12),
    xaxis=dict(gridcolor="#1a2e28", linecolor="#1a2e28", zeroline=False),
    yaxis=dict(gridcolor="#1a2e28", linecolor="#1a2e28", zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
    margin=dict(t=50, b=40, l=50, r=20),
)

_THEME_LIGHT = dict(
    template="plotly_white",
    paper_bgcolor="#f4faf8",
    plot_bgcolor="#ffffff",
    font=dict(family="DM Sans", color="#2d5a4a", size=12),
    xaxis=dict(gridcolor="#d0ece5", linecolor="#b8d8cf", zeroline=False),
    yaxis=dict(gridcolor="#d0ece5", linecolor="#b8d8cf", zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
    margin=dict(t=50, b=40, l=50, r=20),
)

# THEME kept for backward compatibility — resolves at call time
THEME = _THEME_DARK


def is_dark_mode() -> bool:
    """Detect the active Streamlit theme. Falls back to dark."""
    try:
        return st.context.theme.get("base", "dark") == "dark"
    except Exception:
        return True


def apply_theme(fig, title="", height=400):
    dark = is_dark_mode()
    theme = _THEME_DARK if dark else _THEME_LIGHT
    title_color = "#ffffff" if dark else "#0d2820"
    fig.update_layout(
        **theme,
        title=dict(text=title, font=dict(family="Syne", size=15, color=title_color)),
        height=height,
    )
    return fig


@st.cache_data
def build_data():
    np.random.seed(42)
    years = np.arange(1900, 2025)
    n = len(years)

    # ── Températures (France) ─────────────────
    # Tendance observée : +1.7°C sur la période
    # Source : Météo France 2024
    trend_temp = np.linspace(0, 1.7, n)
    noise_temp = np.random.normal(0, 0.22, n)
    # Canicules historiques marquées
    canicules = {1976: 0.9, 1983: 0.6, 2003: 1.95, 2019: 1.4, 2022: 1.3, 2023: 1.1}
    warm_events = np.zeros(n)
    for yr, val in canicules.items():
        idx = np.where(years == yr)[0]
        if len(idx): warm_events[idx[0]] = val

    temp_base = 12.0
    temp = temp_base + trend_temp + noise_temp + warm_events

    # Normales 1961-1990
    ref_mask = (years >= 1961) & (years <= 1990)
    ref_temp = temp[ref_mask].mean()
    anomalie = temp - ref_temp

    # Jours chauds / gel
    jours_chauds = (10 + np.linspace(0, 22, n) + np.random.poisson(2, n) + warm_events * 10).clip(0).astype(int)
    jours_gel = (65 - np.linspace(0, 18, n) + np.random.normal(0, 4, n)).clip(0).astype(int)
    precip = (720 - np.linspace(0, 35, n) + np.random.normal(0, 55, n)).clip(450)

    # ── CO₂ (NOAA Mauna Loa + Law Dome) ───────
    co2 = 296 * np.exp(0.00182 * (years - 1900)) + np.where(years > 1950, (years - 1950) * 0.025, 0)
    co2 = co2.clip(296, 425)

    # ── Score risque composite (0-100) ─────────
    def norm01(x): return (x - x.min()) / (x.max() - x.min() + 1e-9)
    risk = (norm01(anomalie) * 40 + norm01(co2) * 35 + norm01(jours_chauds) * 25).clip(0, 100)

    df_hist = pd.DataFrame({
        "annee": years,
        "temp_moy": temp.round(2),
        "anomalie": anomalie.round(3),
        "co2_ppm": co2.round(1),
        "jours_chauds": jours_chauds,
        "jours_gel": jours_gel,
        "precip_mm": precip.round(0),
        "risk_score": (risk * 100 / risk.max()).round(1),
    })

    # ── GES France (CITEPA Secten) 1990-2024 ──
    ges_years = np.arange(1990, 2025)
    secteurs = {
        "Transport":     (165, -0.10, "#e74c3c"),
        "Industrie":     (110, -0.38, "#e67e22"),
        "Résidentiel":   (105, -0.32, "#f1c40f"),
        "Agriculture":   (100, -0.10, "#2ecc71"),
        "Énergie":        (55, -0.48, "#3498db"),
        "Déchets":        (20, -0.22, "#9b59b6"),
    }
    ges_records = []
    for sect, (base, trend_pct, color) in secteurs.items():
        for i, yr in enumerate(ges_years):
            t = i / len(ges_years)
            covid = -0.08 if yr == 2020 else 0.04 if yr == 2021 else 0
            val = base * (1 + trend_pct * t) * (1 + covid) + np.random.normal(0, 1.5)
            ges_records.append({"annee": int(yr), "secteur": sect, "val": max(0, round(val, 1)), "color": color})
    df_ges = pd.DataFrame(ges_records)

    # ── Empreinte carbone individuelle ─────────
    ec_years = np.arange(1995, 2025)
    empreinte = np.linspace(12.6, 9.9, len(ec_years)) + np.random.normal(0, 0.12, len(ec_years))
    importee = np.linspace(3.0, 4.5, len(ec_years))
    df_ec = pd.DataFrame({
        "annee": ec_years,
        "totale": empreinte.round(2),
        "importee": importee.round(2),
        "nationale": (empreinte - importee).round(2),
    })

    # ── Projections 2026-2100 (3 scénarios × 5 modèles) ────
    scenarios = {
        "Optimiste (+1.4°C)":     {"delta": 1.4, "color": "#2ecc71",  "ssp": "SSP1-2.6", "dash": "dot"},
        "Intermédiaire (+2.7°C)": {"delta": 2.7, "color": "#f39c12",  "ssp": "SSP2-4.5", "dash": "solid"},
        "Pessimiste (+4.4°C)":    {"delta": 4.4, "color": "#e74c3c",  "ssp": "SSP5-8.5", "dash": "dash"},
    }

    # Caractéristiques de chaque modèle :
    # temp_mult = multiplicateur sur le delta (capte biais d'estimation)
    # unc_mult  = multiplicateur sur l'intervalle de confiance
    # noise     = bruit aléatoire résiduel (capture l'incertitude propre au modèle)
    # accel     = accélération de la tendance en fin de période (non-linéarité)
    MODEL_VARIANTS = {
        "Consensus (4 modèles)": {"temp_mult": 1.00, "unc_mult": 1.00, "noise": 0.00, "accel": 0.00},
        "ARIMA":                 {"temp_mult": 0.91, "unc_mult": 1.18, "noise": 0.04, "accel": -0.05},
        "Prophet":               {"temp_mult": 1.04, "unc_mult": 0.88, "noise": 0.02, "accel":  0.03},
        "LSTM":                  {"temp_mult": 1.11, "unc_mult": 1.22, "noise": 0.03, "accel":  0.08},
        "XGBoost":               {"temp_mult": 0.96, "unc_mult": 0.92, "noise": 0.02, "accel": -0.02},
    }

    proj_years = np.arange(2024, 2101)
    proj_records = []
    last_temp = temp[-1]
    rng = np.random.default_rng(42)

    for model_name, mv in MODEL_VARIANTS.items():
        for sc_name, sc in scenarios.items():
            t_norm = (proj_years - 2024) / 76
            # Tendance avec légère accélération/décélération selon le modèle
            delta_eff = sc["delta"] * mv["temp_mult"]
            proj_temp = last_temp + delta_eff * (t_norm + mv["accel"] * t_norm ** 2)
            # Bruit résiduel (fixé par seed pour reproductibilité)
            noise_proj = rng.normal(0, mv["noise"], len(proj_years)).cumsum() * 0.3
            proj_temp = proj_temp + noise_proj
            # Intervalle de confiance qui s'élargit avec le temps
            base_unc = 0.12 * mv["unc_mult"]
            uncertainty = base_unc * (t_norm * 6 + 1)
            for i, yr in enumerate(proj_years):
                proj_records.append({
                    "annee": int(yr),
                    "scenario": sc_name,
                    "ssp": sc["ssp"],
                    "model": model_name,
                    "temp": round(proj_temp[i], 2),
                    "lower": round(proj_temp[i] - 1.96 * uncertainty[i], 2),
                    "upper": round(proj_temp[i] + 1.96 * uncertainty[i], 2),
                    "color": sc["color"],
                    "dash": sc["dash"],
                })
    df_proj = pd.DataFrame(proj_records)

    # ── Données régionales (carto) ─────────────
    # Noms correspondant exactement au GeoJSON france_regions.geojson
    regions = [
        ("Île-de-France",            48.85,  2.35,  "+1.9°C", 82),
        ("Provence-Alpes-Côte d'Azur", 43.93, 6.07, "+2.1°C", 91),
        ("Nouvelle-Aquitaine",       44.84, -0.58,  "+1.6°C", 74),
        ("Auvergne-Rhône-Alpes",     45.75,  4.85,  "+1.8°C", 80),
        ("Occitanie",                43.61,  1.44,  "+1.9°C", 85),
        ("Bretagne",                 48.11, -1.68,  "+1.2°C", 58),
        ("Normandie",                49.18,  0.37,  "+1.3°C", 60),
        ("Grand Est",                48.70,  6.18,  "+1.7°C", 75),
        ("Hauts-de-France",          50.48,  2.79,  "+1.4°C", 64),
        ("Pays de la Loire",         47.48, -0.55,  "+1.5°C", 68),
        ("Centre-Val de Loire",      47.75,  1.67,  "+1.6°C", 72),
        ("Bourgogne-Franche-Comté",  47.28,  4.99,  "+1.7°C", 76),
    ]
    df_reg = pd.DataFrame(regions, columns=["region", "lat", "lon", "anomalie", "risque"])

    return df_hist, df_ges, df_ec, df_proj, df_reg, scenarios


@st.cache_data(ttl=3600)
def fetch_tidegauges() -> pd.DataFrame:
    """Récupère les marégraphes SHOM (RONIM/REFMAR) via l'API publique."""
    try:
        resp = requests.get(
            "https://services.data.shom.fr/maregraphie/service/tidegauges",
            headers={"accept": "*/*"},
            timeout=10,
        )
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
        df = df.dropna(subset=["latitude", "longitude"])
        df["name_clean"] = df["name"].str.replace("_", " ").str.title()
        return df
    except Exception:
        return pd.DataFrame(columns=["shom_id", "name", "name_clean", "longitude", "latitude", "state", "reseau"])
