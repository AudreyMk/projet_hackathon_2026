"""
src/visualization/dashboard.py
================================
Dashboard Streamlit interactif — ClimaDash
Analyse Climatique Multi-Échelle & Sensibilisation Citoyenne

Lancement : streamlit run src/visualization/dashboard.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    PROCESSED_DIR, REPORTS_DIR, SCENARIOS, PROJECTION_YEARS,
    DASHBOARD_CONFIG, INDICATORS, TERRITORY
)
from src.recommendations.citizen_actions import RecommendationEngine

# ─────────────────────────────────────────────
# CONFIG PAGE
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🌍 ClimaDash — Changement Climatique France",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS custom
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #6c5ce7;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .alert-card {
        background: linear-gradient(135deg, #2d1b1b 0%, #3d1515 100%);
        border: 2px solid #e74c3c;
        border-radius: 12px;
        padding: 15px;
    }
    .stMetric { background-color: #1a1a2e; border-radius: 8px; padding: 10px; }
    h1 { color: #6c5ce7 !important; }
    h2 { color: #a29bfe !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CHARGEMENT DONNÉES
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data() -> dict:
    """Charge tous les datasets. Génère des données de démo si absents."""
    data = {}

    # Master features
    features_path = PROCESSED_DIR / "master_features.parquet"
    if features_path.exists():
        data["features"] = pd.read_parquet(features_path)
    else:
        data["features"] = _generate_demo_data()

    # Projections
    proj_path = REPORTS_DIR / "projections_all_models.csv"
    if proj_path.exists():
        data["projections"] = pd.read_csv(proj_path)
    else:
        data["projections"] = _generate_demo_projections(data["features"])

    # GES
    ges_path = PROCESSED_DIR / "ges_clean.parquet"
    if ges_path.exists():
        data["ges"] = pd.read_parquet(ges_path)
    else:
        data["ges"] = _generate_demo_ges()

    return data


def _generate_demo_data() -> pd.DataFrame:
    """Données de démonstration pour le dashboard."""
    np.random.seed(42)
    years = list(range(1900, 2025))
    n = len(years)
    trend = np.linspace(0, 1.7, n)
    noise = np.random.normal(0, 0.25, n)
    return pd.DataFrame({
        "annee": years,
        "temp_moy_c": (12.0 + trend + noise).round(2),
        "anomalie_temp_c": (trend + noise).round(3),
        "jours_chauds_30": (10 + np.linspace(0, 20, n) + np.random.poisson(2, n)).clip(0).astype(int),
        "jours_gel": (60 - np.linspace(0, 15, n) + np.random.normal(0, 4, n)).clip(0).astype(int),
        "co2_ppm": (296 + np.linspace(0, 127, n)).round(1),
        "score_risque_climatique": (10 + np.linspace(0, 80, n) + np.random.normal(0, 3, n)).clip(0, 100).round(1),
    })


def _generate_demo_projections(df_hist: pd.DataFrame) -> pd.DataFrame:
    rows = []
    last_temp = df_hist["temp_moy_c"].iloc[-1]
    last_co2 = df_hist["co2_ppm"].iloc[-1] if "co2_ppm" in df_hist.columns else 420
    for scenario_name, sc in SCENARIOS.items():
        for yr in PROJECTION_YEARS:
            dt = (yr - 2024) / 74 * sc["delta_temp"]
            rows.append({
                "annee": yr, "scenario": scenario_name,
                "scenario_label": sc["label"],
                "prediction": round(last_temp + dt, 2),
                "lower_ci": round(last_temp + dt - 0.3, 2),
                "upper_ci": round(last_temp + dt + 0.3, 2),
                "color": sc["color"], "model": "Demo",
            })
    return pd.DataFrame(rows)


def _generate_demo_ges() -> pd.DataFrame:
    rows = []
    for yr in range(1990, 2025):
        for sect in ["Transport routier", "Industrie", "Résidentiel", "Agriculture"]:
            rows.append({
                "annee": yr, "secteur": sect,
                "emissions_mtco2eq": round(80 - (yr - 1990) * 0.5 + np.random.normal(0, 2), 1)
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar(data: dict) -> dict:
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/globe--v1.png", width=80)
        st.title("🌍 ClimaDash")
        st.caption("Hackathon #26 · Sup²Vinci")
        st.divider()

        st.subheader("⚙️ Paramètres")
        annee_min = int(data["features"]["annee"].min())
        annee_max = int(data["features"]["annee"].max())
        periode = st.slider("Période historique", annee_min, annee_max, (1950, annee_max))

        st.divider()
        st.subheader("🎯 Scénarios")
        scenarios_selec = st.multiselect(
            "Scénarios à afficher",
            options=list(SCENARIOS.keys()),
            default=list(SCENARIOS.keys()),
            format_func=lambda x: f"{x.title()} ({SCENARIOS[x]['label']})"
        )

        st.divider()
        st.subheader("📊 Indicateurs")
        indicateurs_affichage = st.multiselect(
            "Variables à visualiser",
            options=["temp_moy_c", "co2_ppm", "jours_chauds_30", "anomalie_temp_c"],
            default=["temp_moy_c", "co2_ppm"],
        )

        return {
            "periode": periode,
            "scenarios": scenarios_selec,
            "indicateurs": indicateurs_affichage,
        }


# ─────────────────────────────────────────────
# ONGLET 1 : ANALYSE HISTORIQUE
# ─────────────────────────────────────────────
def render_historique(data: dict, params: dict):
    st.header(f"📈 Analyse historique — {TERRITORY.name}")

    df = data["features"]
    df_filter = df[df["annee"].between(*params["periode"])]

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    last_row = df.iloc[-1]
    first_row = df[df["annee"] == params["periode"][0]].iloc[0] if len(df[df["annee"] == params["periode"][0]]) else df.iloc[0]

    with col1:
        delta_temp = last_row["temp_moy_c"] - first_row["temp_moy_c"]
        st.metric("🌡️ Température actuelle",
                  f"{last_row['temp_moy_c']:.1f}°C",
                  delta=f"+{delta_temp:.2f}°C depuis {params['periode'][0]}")
    with col2:
        if "co2_ppm" in df.columns:
            st.metric("🏭 CO₂ atmosphérique",
                      f"{last_row['co2_ppm']:.0f} ppm",
                      delta=f"+{last_row['co2_ppm'] - first_row['co2_ppm']:.0f} ppm")
    with col3:
        if "jours_chauds_30" in df.columns:
            st.metric("☀️ Jours > 30°C",
                      f"{last_row['jours_chauds_30']:.0f} j/an",
                      delta=f"+{last_row['jours_chauds_30'] - first_row['jours_chauds_30']:.0f} j")
    with col4:
        if "score_risque_climatique" in df.columns:
            score = last_row["score_risque_climatique"]
            couleur = "🔴" if score > 70 else "🟠" if score > 50 else "🟡"
            st.metric(f"{couleur} Score risque",
                      f"{score:.0f}/100")

    # Graphique principal : évolution de la température
    col_left, col_right = st.columns([2, 1])

    with col_left:
        if "temp_moy_c" in params["indicateurs"] or len(params["indicateurs"]) == 0:
            fig = go.Figure()

            # Courbe historique
            fig.add_trace(go.Scatter(
                x=df_filter["annee"], y=df_filter["temp_moy_c"],
                mode="lines", name="Température annuelle",
                line=dict(color="#a29bfe", width=1.5),
            ))

            # Moyenne mobile 10 ans
            df_filter = df_filter.copy()
            df_filter["rolling_10"] = df_filter["temp_moy_c"].rolling(10, center=True).mean()
            fig.add_trace(go.Scatter(
                x=df_filter["annee"], y=df_filter["rolling_10"],
                mode="lines", name="Moyenne mobile 10 ans",
                line=dict(color="#fd79a8", width=3),
            ))

            # Ligne de référence 1961-1990
            ref_temp = df[df["annee"].between(1961, 1990)]["temp_moy_c"].mean()
            fig.add_hline(y=ref_temp, line_dash="dash",
                          annotation_text=f"Normale 1961-1990 ({ref_temp:.1f}°C)",
                          line_color="#00b894")

            fig.update_layout(
                title="🌡️ Évolution de la température moyenne en France",
                template="plotly_dark", height=400,
                xaxis_title="Année", yaxis_title="Température (°C)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Heatmap des anomalies par décennie
        if "anomalie_temp_c" in df.columns:
            df_filter["decennie"] = (df_filter["annee"] // 10 * 10).astype(str)
            anom_moy = df_filter.groupby("decennie")["anomalie_temp_c"].mean().reset_index()

            fig_bar = go.Figure(go.Bar(
                x=anom_moy["decennie"],
                y=anom_moy["anomalie_temp_c"].round(2),
                marker_color=[
                    "#e74c3c" if v > 0.5 else "#f39c12" if v > 0 else "#3498db"
                    for v in anom_moy["anomalie_temp_c"]
                ],
                text=[f"+{v:.2f}°C" if v > 0 else f"{v:.2f}°C"
                      for v in anom_moy["anomalie_temp_c"].round(2)],
                textposition="outside",
            ))
            fig_bar.update_layout(
                title="📊 Anomalie par décennie",
                template="plotly_dark", height=400,
                xaxis_title="Décennie", yaxis_title="Anomalie (°C)",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # CO₂ + Température superposés
    if "co2_ppm" in df.columns and len(df_filter) > 0:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_filter["annee"], y=df_filter["temp_moy_c"],
            mode="lines", name="Température (°C)",
            line=dict(color="#fd79a8"), yaxis="y"
        ))
        fig2.add_trace(go.Scatter(
            x=df_filter["annee"], y=df_filter["co2_ppm"],
            mode="lines", name="CO₂ (ppm)",
            line=dict(color="#fdcb6e", dash="dash"), yaxis="y2"
        ))
        fig2.update_layout(
            title="🔗 Corrélation Température / CO₂",
            template="plotly_dark", height=350,
            yaxis=dict(title="Température (°C)", titlefont_color="#fd79a8"),
            yaxis2=dict(title="CO₂ (ppm)", overlaying="y", side="right",
                        titlefont_color="#fdcb6e"),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 2 : PROJECTIONS
# ─────────────────────────────────────────────
def render_projections(data: dict, params: dict):
    st.header("🔮 Projections climatiques 2030 / 2050 / 2100")

    df_hist = data["features"]
    df_proj = data["projections"]

    # Slider temporel
    annee_slider = st.select_slider(
        "📅 Horizon de projection",
        options=[2026, 2030, 2040, 2050, 2075, 2100],
        value=2050
    )

    # Filtrer les projections <= annee_slider
    df_proj_filter = df_proj[
        (df_proj["annee"] <= annee_slider) &
        (df_proj["scenario"].isin(params["scenarios"]))
    ]

    col1, col2 = st.columns([3, 1])

    with col1:
        fig = go.Figure()

        # Historique
        hist_recent = df_hist[df_hist["annee"] >= 1950]
        fig.add_trace(go.Scatter(
            x=hist_recent["annee"], y=hist_recent["temp_moy_c"],
            mode="lines", name="Historique",
            line=dict(color="#636e72", width=2),
        ))

        # Projections par scénario
        for scenario_name in params["scenarios"]:
            sc_info = SCENARIOS[scenario_name]
            sub = df_proj_filter[df_proj_filter["scenario"] == scenario_name]
            if len(sub) == 0:
                continue

            # Bande d'incertitude
            fig.add_trace(go.Scatter(
                x=pd.concat([sub["annee"], sub["annee"].iloc[::-1]]),
                y=pd.concat([sub["upper_ci"], sub["lower_ci"].iloc[::-1]]),
                fill="toself",
                fillcolor=sc_info["color"] + "33",
                line=dict(color="rgba(255,255,255,0)"),
                showlegend=False, hoverinfo="skip",
            ))

            fig.add_trace(go.Scatter(
                x=sub["annee"], y=sub["prediction"],
                mode="lines+markers",
                name=f"{scenario_name.title()} ({sc_info['label']})",
                line=dict(color=sc_info["color"], width=2.5),
                marker=dict(size=8),
            ))

        fig.add_vline(x=2024, line_dash="dot", line_color="white",
                      annotation_text="Aujourd'hui")
        fig.update_layout(
            title=f"📈 Projections de température jusqu'en {annee_slider}",
            template="plotly_dark", height=500,
            xaxis_title="Année", yaxis_title="Température (°C)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🎯 Résumé des projections")
        for yr in [y for y in PROJECTION_YEARS if y <= annee_slider]:
            st.markdown(f"**📅 {yr}**")
            for sc_name, sc in SCENARIOS.items():
                if sc_name not in params["scenarios"]:
                    continue
                sub = df_proj[(df_proj["annee"] == yr) & (df_proj["scenario"] == sc_name)]
                if len(sub) > 0:
                    pred = sub["prediction"].mean()
                    st.markdown(
                        f"<span style='color:{sc['color']}'>{sc_name.title()}: **{pred:.1f}°C**</span>",
                        unsafe_allow_html=True
                    )
            st.divider()


# ─────────────────────────────────────────────
# ONGLET 3 : ÉMISSIONS GES
# ─────────────────────────────────────────────
def render_emissions(data: dict):
    st.header("🏭 Émissions de GES par secteur (France)")

    df = data["ges"]
    if df.empty:
        st.warning("Données GES non disponibles.")
        return

    # Filtrer total
    df_secteurs = df[df["secteur"] != "TOTAL"]

    fig = px.area(
        df_secteurs, x="annee", y="emissions_mtco2eq", color="secteur",
        title="Émissions GES par secteur (MtCO₂eq)",
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )
    fig.update_layout(height=450, xaxis_title="Année", yaxis_title="MtCO₂eq")
    st.plotly_chart(fig, use_container_width=True)

    # Objectif 2030
    st.info("🎯 **Objectif France 2030 :** -55% d'émissions vs 1990 (PNACC 3 / Loi Énergie Climat)")


# ─────────────────────────────────────────────
# ONGLET 4 : PRÉCONISATIONS CITOYENNES
# ─────────────────────────────────────────────
def render_recommandations(data: dict):
    st.header("🌱 Préconisations citoyennes")
    st.caption("Basées sur vos données territoriales et alignées avec le PNACC 3 & Earth Action Report 2025")

    # Profil de risque
    df = data["features"]
    last = df.iloc[-1]

    risk_score = last.get("score_risque_climatique", 50)
    jours_chauds = last.get("jours_chauds_30", 15)
    deficit_precip = last.get("deficit_precip_pct", -5)

    engine = RecommendationEngine()
    recs = engine.get_recommendations(
        risk_score=risk_score,
        jours_chauds=jours_chauds,
        deficit_precip=deficit_precip,
        territoire=TERRITORY.name,
    )

    for category, actions in recs.items():
        with st.expander(f"**{category}**", expanded=True):
            for action in actions:
                priority_color = "🔴" if action["priority"] == "haute" else "🟠" if action["priority"] == "moyenne" else "🟢"
                st.markdown(
                    f"{priority_color} **{action['titre']}** — {action['description']}\n"
                    f"*Impact estimé : {action['impact']}*"
                )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    # Header principal
    st.title("🌍 ClimaDash — Changement Climatique France")
    st.caption(f"Hackathon #26 · Sup²Vinci · 16-17 Mars 2026 · Territoire : {TERRITORY.name}")

    # Chargement
    with st.spinner("⏳ Chargement des données climatiques..."):
        data = load_data()

    # Sidebar
    params = render_sidebar(data)

    # Onglets
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Analyse historique",
        "🔮 Projections",
        "🏭 Émissions GES",
        "🌱 Préconisations",
    ])

    with tab1:
        render_historique(data, params)
    with tab2:
        render_projections(data, params)
    with tab3:
        render_emissions(data)
    with tab4:
        render_recommandations(data)

    # Footer
    st.divider()
    st.caption(
        "Sources : Météo France · NOAA · CITEPA Secten · DRIAS · GIEC 2023 | "
        "Dashboard Hackathon #26 — Big Data & IA"
    )


if __name__ == "__main__":
    main()
