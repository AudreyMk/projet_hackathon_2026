from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from web.data import apply_theme


def tab_vigicrues(df_vigi: pd.DataFrame):
    """
    Onglet Vigicrues — niveaux d'eau par station hydrologique.
    `df_vigi` : DataFrame retourné par src.data_loader.load_vigigrues()
    """
    if df_vigi.empty:
        st.warning(
            "Fichier `vigigrues.csv` introuvable dans `data/raw/`.\n\n"
            "Colonnes attendues : `CdStation`, `DateObs`, `Valeur` — séparateur `;` ou tabulation."
        )
        return

    # ── KPIs globaux ──────────────────────────────────────────────────
    stations_vigi: list[str] = []
    if "station" in df_vigi.columns:
        stations_vigi = sorted(
            df_vigi["station"].dropna()
            .astype(str).str.strip()
            .replace("", float("nan")).dropna()
            .unique().tolist()
        )

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Stations suivies", len(stations_vigi))
    with k2:
        st.metric("Mesures totales", f"{len(df_vigi):,}")
    with k3:
        if "hauteur_mm" in df_vigi.columns:
            st.metric("Hauteur max observée", f"{df_vigi['hauteur_mm'].max():,.0f} mm")

    if not stations_vigi:
        st.warning("Colonne `station` vide ou absente dans les données Vigigrues.")
        st.dataframe(df_vigi.head(10))
        return

    # ── Sélecteur de station ──────────────────────────────────────────
    station_sel = st.selectbox("Station Vigicrues", stations_vigi, key="vigi_station_sel")

    if station_sel is None:
        return

    # ── Filtrage par station ──────────────────────────────────────────
    df_v = df_vigi[df_vigi["station"] == station_sel].copy() if "station" in df_vigi.columns else df_vigi.copy()
    if "datetime_utc" in df_v.columns:
        df_v = df_v.sort_values("datetime_utc")

    st.markdown(f"### Station **{station_sel}**")

    if "hauteur_mm" in df_v.columns:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Min", f"{df_v['hauteur_mm'].min():,.0f} mm")
        c2.metric("Max", f"{df_v['hauteur_mm'].max():,.0f} mm")
        c3.metric("Moy.", f"{df_v['hauteur_mm'].mean():,.0f} mm")
        c4.metric("Dernière mesure",
                  f"{df_v['hauteur_mm'].iloc[-1]:,.0f} mm" if len(df_v) else "—")

    # ── Graphique niveau d'eau ────────────────────────────────────────
    if "hauteur_mm" in df_v.columns and "datetime_utc" in df_v.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_v["datetime_utc"], y=df_v["hauteur_mm"],
            mode="lines", name="Hauteur d'eau (mm)",
            line=dict(color="#74b9ff", width=1.5),
            fill="tozeroy", fillcolor="rgba(116,185,255,0.12)",
        ))
        moy = df_v["hauteur_mm"].mean()
        fig.add_hline(y=moy, line_dash="dash", line_color="#fdcb6e",
                      annotation_text=f"Moy. {moy:,.0f} mm")
        apply_theme(fig, f"Niveau d'eau — Station {station_sel}", 450)
        fig.update_xaxes(title_text="Date / Heure (UTC)")
        fig.update_yaxes(title_text="Hauteur (mm)")
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    # ── Distribution des hauteurs ─────────────────────────────────────
    if "hauteur_mm" in df_v.columns:
        with st.expander("Distribution des hauteurs"):
            fig_h = px.histogram(df_v, x="hauteur_mm", nbins=40,
                color_discrete_sequence=["#74b9ff"],
                labels={"hauteur_mm": "Hauteur (mm)"},
                title=f"Distribution des hauteurs — {station_sel}")
            apply_theme(fig_h, height=300)
            st.plotly_chart(fig_h, use_container_width=True)

    # ── Tableau des dernières mesures ─────────────────────────────────
    st.subheader("Dernières 50 mesures")
    display_cols = [c for c in ["datetime_utc", "hauteur_mm", "qualif", "continuite"]
                    if c in df_v.columns]
    st.dataframe(df_v[display_cols].tail(50).iloc[::-1], use_container_width=True)
