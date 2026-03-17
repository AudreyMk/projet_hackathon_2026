import json
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from web.data import GREEN, THEME, apply_theme, is_dark_mode


_GEOJSON_PATH = Path("data/processed/france_regions.geojson")


def tab_carte(df_reg, territoire="France entière"):
    st.markdown('<p class="section-sub">Anomalies de température et score de risque par région</p>', unsafe_allow_html=True)

    selected = territoire if territoire != "France entière" else None

    with open(_GEOJSON_PATH) as f:
        geojson = json.load(f)

    dark = is_dark_mode()
    map_style = "carto-darkmatter" if dark else "carto-positron"

    # Choroplèthe régions
    fig_map = px.choropleth_mapbox(
        df_reg,
        geojson=geojson,
        locations="region",
        featureidkey="properties.nom",
        color="risque",
        color_continuous_scale=["#0e7c61", "#f39c12", "#e74c3c"],
        range_color=[50, 95],
        hover_name="region",
        hover_data={"anomalie": True, "risque": True},
        zoom=4.5,
        center={"lat": 46.5, "lon": 2.5},
        mapbox_style=map_style,
        height=520,
        opacity=0.75,
    )

    # Surbrillance de la région sélectionnée
    if selected:
        df_sel = df_reg[df_reg["region"] == selected]
        if not df_sel.empty:
            fig_map.add_trace(go.Choroplethmapbox(
                geojson=geojson,
                locations=[selected],
                featureidkey="properties.nom",
                z=[1],
                colorscale=[[0, "rgba(255,255,255,0.35)"], [1, "rgba(255,255,255,0.35)"]],
                showscale=False, hoverinfo="skip",
                marker_line_color="#ffffff", marker_line_width=2.5,
            ))
            fig_map.update_layout(
                mapbox_center={"lat": float(df_sel["lat"].iloc[0]), "lon": float(df_sel["lon"].iloc[0])},
                mapbox_zoom=6,
            )

    fig_map.update_layout(
        **{k: v for k, v in THEME.items() if k in ["paper_bgcolor", "font", "margin"]},
        coloraxis_colorbar=dict(
            title="Risque", tickfont=dict(color="#a8c5be"), titlefont=dict(color="#a8c5be"),
        ),
    )
    st.plotly_chart(fig_map, width="stretch")

    # Classement des régions par risque
    st.markdown('<p class="section-title" style="margin-top:4px">Classement des régions par risque climatique</p>', unsafe_allow_html=True)
    df_rank = df_reg.sort_values("risque", ascending=False).reset_index(drop=True)
    df_rank.index += 1

    bar_colors = [
        "#ffffff" if (selected and row["region"] == selected) else
        ("#e74c3c" if row["risque"] >= 80 else "#f39c12" if row["risque"] >= 65 else GREEN)
        for _, row in df_rank.iterrows()
    ]

    fig_rank = go.Figure(go.Bar(
        x=df_rank["risque"],
        y=df_rank["region"],
        orientation="h",
        marker=dict(color=bar_colors),
        text=[f'{r} — {a}' for r, a in zip(df_rank["risque"], df_rank["anomalie"])],
        textposition="inside",
        textfont=dict(color="#fff", size=11),
    ))
    apply_theme(fig_rank, "", 400)
    fig_rank.update_xaxes(title_text="Score de risque (0-100)")
    st.plotly_chart(fig_rank, width="stretch")
