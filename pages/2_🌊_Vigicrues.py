"""
pages/2_🌊_Vigicrues.py
========================
Page Vigigrues — niveaux d'eau temps réel par station hydrologique.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import load_all

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    section[data-testid="stSidebar"] { background-color: #12151c; }
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #74b9ff;
        border-radius: 12px;
        padding: 12px 16px;
    }
    h1 { color: #74b9ff !important; letter-spacing: -0.5px; }
    h2 { color: #81ecec !important; }
    h3 { color: #dfe6e9 !important; }
</style>
""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  CHARGEMENT                                                 ║
# ╚══════════════════════════════════════════════════════════════╝
@st.cache_data(ttl=300, show_spinner=False)  # TTL court : données temps réel
def _load() -> dict[str, pd.DataFrame]:
    return load_all()


# ╔══════════════════════════════════════════════════════════════╗
# ║  SIDEBAR                                                    ║
# ╚══════════════════════════════════════════════════════════════╝
def render_sidebar(df: pd.DataFrame) -> dict:
    with st.sidebar:
        st.markdown("## 🌊 Vigicrues")
        st.divider()

        if "station" in df.columns:
            stations_vigi = sorted(
                df["station"].dropna()
                .astype(str).str.strip()
                .replace("", float("nan")).dropna()
                .unique().tolist()
            )
        else:
            stations_vigi = []

        st.subheader("📍 Station")
        if stations_vigi:
            station_sel = st.selectbox("Station Vigicrues", stations_vigi, key="vigi_station")
        else:
            station_sel = None
            st.warning("Aucune station disponible.")

        st.divider()

        st.subheader("ℹ️ Données chargées")
        if not df.empty:
            st.info(
                f"**{len(df):,}** mesures\n\n"
                f"**{len(stations_vigi)}** station(s)\n\n"
                + (f"Depuis : **{df['datetime_utc'].min().strftime('%d/%m/%Y %H:%M')}**\n\n"
                   f"Jusqu'à : **{df['datetime_utc'].max().strftime('%d/%m/%Y %H:%M')}**"
                   if "datetime_utc" in df.columns and not df["datetime_utc"].isna().all()
                   else "")
            )

    return {"station": station_sel, "stations_vigi": stations_vigi}


# ╔══════════════════════════════════════════════════════════════╗
# ║  PAGE PRINCIPALE                                            ║
# ╚══════════════════════════════════════════════════════════════╝
def render_page(df: pd.DataFrame, params: dict):
    stations_vigi = params["stations_vigi"]
    station_v     = params["station"]

    # ── KPIs globaux ──────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("📍 Stations suivies", len(stations_vigi))
    with k2:
        st.metric("📊 Mesures totales", f"{len(df):,}")
    with k3:
        if "hauteur_mm" in df.columns:
            st.metric("🔆 Hauteur max observée", f"{df['hauteur_mm'].max():,.0f} mm")

    if not stations_vigi:
        st.warning("Colonne `station` vide ou absente dans les données Vigigrues.")
        st.markdown("**Aperçu des données chargées :**")
        st.dataframe(df.head(10))
        return

    if station_v is None:
        return

    # ── Filtrage par station ───────────────────────────────────────
    df_v = df[df["station"] == station_v].copy() if "station" in df.columns else df.copy()
    if "datetime_utc" in df_v.columns:
        df_v = df_v.sort_values("datetime_utc")

    st.markdown(f"### 🌊 Station **{station_v}**")

    # ── Stats de la station ────────────────────────────────────────
    if "hauteur_mm" in df_v.columns:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📉 Min", f"{df_v['hauteur_mm'].min():,.0f} mm")
        c2.metric("📈 Max", f"{df_v['hauteur_mm'].max():,.0f} mm")
        c3.metric("📊 Moy.", f"{df_v['hauteur_mm'].mean():,.0f} mm")
        c4.metric("🕐 Dernière mesure",
                  f"{df_v['hauteur_mm'].iloc[-1]:,.0f} mm" if len(df_v) else "—")

    # ── Graphique niveau d'eau ─────────────────────────────────────
    if "hauteur_mm" in df_v.columns and "datetime_utc" in df_v.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_v["datetime_utc"], y=df_v["hauteur_mm"],
            mode="lines", name="Hauteur d'eau (mm)",
            line=dict(color="#74b9ff", width=1.5),
            fill="tozeroy", fillcolor="rgba(116,185,255,0.12)",
        ))

        # Ligne de moyenne
        moy = df_v["hauteur_mm"].mean()
        fig.add_hline(y=moy, line_dash="dash", line_color="#fdcb6e",
                      annotation_text=f"Moy. {moy:,.0f} mm")

        fig.update_layout(
            title=f"🌊 Niveau d'eau — Station {station_v}",
            template="plotly_dark", height=450,
            xaxis_title="Date / Heure (UTC)", yaxis_title="Hauteur (mm)",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Distribution des hauteurs ──────────────────────────────────
    if "hauteur_mm" in df_v.columns:
        with st.expander("📊 Distribution des hauteurs"):
            import plotly.express as px
            fig_h = px.histogram(df_v, x="hauteur_mm", nbins=40,
                color_discrete_sequence=["#74b9ff"],
                labels={"hauteur_mm": "Hauteur (mm)"},
                title=f"Distribution des hauteurs — {station_v}")
            fig_h.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_h, use_container_width=True)

    # ── Tableau des dernières mesures ──────────────────────────────
    st.subheader("📋 Dernières 50 mesures")
    display_cols = [c for c in ["datetime_utc", "hauteur_mm", "qualif", "continuite"]
                    if c in df_v.columns]
    st.dataframe(df_v[display_cols].tail(50).iloc[::-1], use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  MAIN                                                       ║
# ╚══════════════════════════════════════════════════════════════╝
st.title("🌊 Vigicrues — Niveaux d'eau")
st.caption("Données temps réel SCHAPI · Hackathon #26 · Sup²Vinci · Mars 2026")

with st.spinner("⏳ Chargement des données Vigigrues…"):
    data = _load()

df_vigi = data["vigigrues"]

if df_vigi.empty:
    st.warning(
        "Fichier `vigigrues.csv` introuvable dans `data/raw/`.\n\n"
        "Colonnes attendues : `CdStation`, `DateObs`, `Valeur` — séparateur `;` ou tabulation."
    )
else:
    params = render_sidebar(df_vigi)
    render_page(df_vigi, params)

st.divider()
st.caption("Source : Vigicrues (SCHAPI) | Hackathon #26 — Sup²Vinci")
