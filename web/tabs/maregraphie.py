import plotly.graph_objects as go
import streamlit as st

from web.data import THEME, apply_theme, is_dark_mode, fetch_tidegauges


_STATE_COLOR = {
    "OK":     "#2ecc71",
    "ASYNC":  "#f39c12",
    "KO":     "#e74c3c",
    "PB":     "#e74c3c",
    "OLD":    "#9b59b6",
    "HIDDEN": "#7f8c8d",
}
_STATE_LABEL = {
    "OK":     "En service",
    "ASYNC":  "Décalée",
    "KO":     "Hors service",
    "PB":     "Problème",
    "OLD":    "Obsolète",
    "HIDDEN": "Masquée",
}


def tab_maregraphie():
    st.markdown(
        '<p class="section-sub">Réseau national de marégraphes SHOM · RONIM / REFMAR · Données temps réel</p>',
        unsafe_allow_html=True,
    )

    df = fetch_tidegauges()

    if df.empty:
        st.error("Impossible de récupérer les données SHOM. Vérifiez votre connexion.")
        return

    #  Filtres
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        reseaux_opts = ["Tous"] + sorted(df["reseau"].dropna().unique().tolist())
        reseau_sel = st.selectbox("Réseau", reseaux_opts, label_visibility="visible")
    with col_f2:
        etats_opts = ["Tous"] + sorted(df["state"].unique().tolist())
        etat_sel = st.selectbox("État", etats_opts, label_visibility="visible")
    with col_f3:
        only_ok = st.checkbox("En service uniquement", value=False)

    df_f = df.copy()
    if reseau_sel != "Tous":
        df_f = df_f[df_f["reseau"] == reseau_sel]
    if etat_sel != "Tous":
        df_f = df_f[df_f["state"] == etat_sel]
    if only_ok:
        df_f = df_f[df_f["state"] == "OK"]

    #  KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total stations", len(df_f))
    k2.metric("En service (OK)", int((df_f["state"] == "OK").sum()))
    k3.metric("Hors service / PB", int(df_f["state"].isin(["KO", "PB"]).sum()))
    k4.metric("Réseau RONIM", int((df_f["reseau"] == "RONIM").sum()))

    #  Carte
    dark = is_dark_mode()
    map_style = "carto-darkmatter" if dark else "carto-positron"

    df_f = df_f.copy()
    df_f["color"] = df_f["state"].map(_STATE_COLOR).fillna("#7f8c8d")
    df_f["label"] = df_f["state"].map(_STATE_LABEL).fillna(df_f["state"])

    fig_map = go.Figure()
    for state, grp in df_f.groupby("state"):
        color = _STATE_COLOR.get(state, "#7f8c8d")
        label = _STATE_LABEL.get(state, state)
        fig_map.add_trace(go.Scattermapbox(
            lat=grp["latitude"],
            lon=grp["longitude"],
            mode="markers",
            marker=dict(size=10, color=color, opacity=0.9),
            name=label,
            text=grp["name_clean"] + "<br>Réseau : " + grp["reseau"].fillna("–") + "<br>État : " + label,
            hovertemplate="%{text}<extra></extra>",
        ))

    fig_map.update_layout(
        mapbox_style=map_style,
        mapbox_zoom=4.2,
        mapbox_center={"lat": 46.8, "lon": 2.3},
        height=520,
        legend=dict(orientation="h", y=1.02, x=0),
        **{k: v for k, v in THEME.items() if k in ["paper_bgcolor", "font", "margin"]},
    )
    st.plotly_chart(fig_map, width="stretch")

    #  Répartition par état (barres)
    col_bar, col_tbl = st.columns([2, 3])

    with col_bar:
        state_counts = df_f["state"].value_counts().reset_index()
        state_counts.columns = ["state", "count"]
        state_counts["label"] = state_counts["state"].map(_STATE_LABEL).fillna(state_counts["state"])
        state_counts["color"] = state_counts["state"].map(_STATE_COLOR).fillna("#7f8c8d")

        fig_bar = go.Figure(go.Bar(
            x=state_counts["label"],
            y=state_counts["count"],
            marker_color=state_counts["color"],
            text=state_counts["count"],
            textposition="outside",
            textfont=dict(color="#d8e4e2"),
        ))
        apply_theme(fig_bar, "Stations par état", 300)
        fig_bar.update_yaxes(title_text="Nombre de stations")
        st.plotly_chart(fig_bar, width="stretch")

    with col_tbl:
        st.markdown('<p class="section-title" style="margin-top:4px">Liste des stations</p>', unsafe_allow_html=True)
        df_display = df_f[["name_clean", "reseau", "state", "latitude", "longitude"]].copy()
        df_display.columns = ["Station", "Réseau", "État", "Lat.", "Lon."]
        df_display["État"] = df_display["État"].map(_STATE_LABEL).fillna(df_display["État"])
        df_display = df_display.sort_values("Station").reset_index(drop=True)
        st.dataframe(df_display, height=280, width="stretch", hide_index=True)
