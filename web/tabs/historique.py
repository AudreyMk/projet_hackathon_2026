import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from web.data import GREEN, ACCENT, apply_theme


def tab_historique(df_hist, periode):
    df = df_hist[df_hist["annee"].between(*periode)].copy()
    df["roll10"] = df["temp_moy"].rolling(10, center=True, min_periods=3).mean()

    #  Graphique 1 : Température + moyenne mobile
    fig1 = go.Figure()

    # Zone de référence 1961-1990
    ref_temp = df_hist[df_hist["annee"].between(1961, 1990)]["temp_moy"].mean()
    fig1.add_hline(y=ref_temp, line_dash="dash", line_color="#3d6b60", line_width=1,
                   annotation_text=f"Normale 1961–90 ({ref_temp:.1f}°C)", annotation_font_color="#3d6b60")

    fig1.add_trace(go.Scatter(
        x=df["annee"], y=df["temp_moy"], mode="lines",
        line=dict(color="#2a4a40", width=1), name="Annuel", showlegend=True,
    ))
    fig1.add_trace(go.Scatter(
        x=df["annee"], y=df["roll10"], mode="lines",
        line=dict(color=GREEN, width=3), name="Moy. mobile 10 ans",
    ))

    # Canicule 2003
    if 2003 in df["annee"].values:
        v = df[df["annee"] == 2003]["temp_moy"].values[0]
        fig1.add_annotation(x=2003, y=v, text=" 2003", showarrow=True, arrowhead=2,
                             arrowcolor="#e74c3c", font=dict(color="#e74c3c", size=11), ax=30, ay=-40)

    apply_theme(fig1, "Évolution de la température moyenne en France", 380)
    fig1.update_yaxes(title_text="°C")
    st.plotly_chart(fig1, width="stretch")

    #  Graphique 2 : Barres anomalies + CO₂
    col_a, col_b = st.columns([3, 2])

    with col_a:
        colors_anom = [
            "#e74c3c" if v > 0.8 else "#e67e22" if v > 0.4 else
            "#f39c12" if v > 0 else "#3498db" if v > -0.4 else "#2980b9"
            for v in df["anomalie"]
        ]
        fig_anom = go.Figure(go.Bar(
            x=df["annee"], y=df["anomalie"].round(2),
            marker_color=colors_anom, name="Anomalie",
        ))
        apply_theme(fig_anom, "Anomalie thermique vs 1961–1990 (°C)", 300)
        fig_anom.update_yaxes(title_text="°C")
        st.plotly_chart(fig_anom, width="stretch")

    with col_b:
        fig_co2 = go.Figure()
        fig_co2.add_hline(y=350, line_dash="dot", line_color="#f39c12",
                          annotation_text="Limite sécurité 350 ppm", annotation_font_color="#f39c12")
        fig_co2.add_hline(y=420, line_dash="dot", line_color="#e74c3c",
                          annotation_text="Seuil alerte 420 ppm", annotation_font_color="#e74c3c")
        fig_co2.add_trace(go.Scatter(
            x=df["annee"], y=df["co2_ppm"], mode="lines",
            line=dict(color=ACCENT, width=2.5), fill="tozeroy",
            fillcolor="rgba(78,205,196,0.07)",
        ))
        apply_theme(fig_co2, "CO₂ atmosphérique (ppm)", 300)
        fig_co2.update_yaxes(title_text="ppm")
        st.plotly_chart(fig_co2, width="stretch")

    #  Graphique 3 : Double axe Temp / CO₂
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(go.Scatter(
        x=df["annee"], y=df["temp_moy"], name="Température (°C)",
        line=dict(color=GREEN, width=2),
    ), secondary_y=False)
    fig_dual.add_trace(go.Scatter(
        x=df["annee"], y=df["co2_ppm"], name="CO₂ (ppm)",
        line=dict(color=ACCENT, width=2, dash="dot"),
    ), secondary_y=True)
    apply_theme(fig_dual, "Corrélation Température / CO₂", 320)
    fig_dual.update_yaxes(title_text="°C", secondary_y=False)
    fig_dual.update_yaxes(title_text="CO₂ (ppm)", secondary_y=True, gridcolor="#1a2e28")
    st.plotly_chart(fig_dual, width="stretch")

    #  Stats décennales
    st.markdown('<p class="section-title">Synthèse par décennie</p>', unsafe_allow_html=True)
    df["dec"] = (df["annee"] // 10 * 10).astype(str) + "s"
    dec_stats = df.groupby("dec").agg(
        temp=("temp_moy", "mean"),
        anomalie=("anomalie", "mean"),
        co2=("co2_ppm", "mean"),
        jours_chauds=("jours_chauds", "mean"),
    ).round(2).reset_index()
    dec_stats.columns = ["Décennie", "Temp. moy (°C)", "Anomalie (°C)", "CO₂ (ppm)", "Jours > 30°C"]
    st.dataframe(
        dec_stats.style
        .background_gradient(subset=["Anomalie (°C)"], cmap="RdBu_r")
        .background_gradient(subset=["CO₂ (ppm)"], cmap="YlOrRd")
        .format(precision=2),
        width="stretch", hide_index=True,
    )
