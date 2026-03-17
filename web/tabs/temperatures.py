from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from web.data import apply_theme


# ── Helpers ────────────────────────────────────────────────────────────────

def _filter_annual(df: pd.DataFrame, periode: tuple) -> pd.DataFrame:
    return df[df["annee"].between(*periode)].copy()


def _filter_monthly_station(df: pd.DataFrame, station: str) -> pd.DataFrame:
    if df.empty or station == "Toutes (moyenne nationale)" or "nom_station" not in df.columns:
        return df
    return df[df["nom_station"] == station].copy()


def _annual_for_station(df_monthly: pd.DataFrame, station: str, periode: tuple) -> pd.DataFrame:
    df = _filter_monthly_station(df_monthly, station)
    if df.empty:
        return df
    agg = {}
    for col, fn in [("tmoy", "mean"), ("tmax", "mean"), ("tmin", "mean")]:
        if col in df.columns:
            agg[col] = (col, fn)
    for col in ["nb_jours_tx30", "precip_mm"]:
        if col in df.columns:
            agg[col] = (col, "sum")
    if not agg:
        return pd.DataFrame()
    out = df.dropna(subset=["annee"]).groupby("annee", as_index=False).agg(**agg)
    out = out.rename(columns={"tmoy": "temp_moy_c", "tmax": "tmax_moy_c", "tmin": "tmin_moy_c"})
    if "temp_moy_c" in out.columns:
        ref_mask = out["annee"].between(1961, 1990)
        ref = out.loc[ref_mask, "temp_moy_c"].mean()
        out["anomalie_temp_c"] = (out["temp_moy_c"] - ref).round(3) if pd.notna(ref) else np.nan
    return out[out["annee"].between(*periode)].sort_values("annee")


# ── Sous-onglets ────────────────────────────────────────────────────────────

def _tab_historique(data: dict, station: str, periode: tuple):
    df_ann = _filter_annual(data["meteo_annual"], periode)

    if station != "Toutes (moyenne nationale)":
        df_st = _annual_for_station(data["meteo_monthly"], station, periode)
        if not df_st.empty:
            df_ann = df_st

    if not df_ann.empty:
        last, first = df_ann.iloc[-1], df_ann.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if "temp_moy_c" in df_ann.columns:
                st.metric("Temp. moy. (dernière année)",
                          f"{last['temp_moy_c']:.1f} °C",
                          delta=f"{last['temp_moy_c'] - first['temp_moy_c']:+.2f} °C sur la période")
        with c2:
            if "tmax_moy_c" in df_ann.columns:
                st.metric("Tmax moy.",
                          f"{last['tmax_moy_c']:.1f} °C",
                          delta=f"{last['tmax_moy_c'] - first['tmax_moy_c']:+.2f} °C")
        with c3:
            if "nb_jours_tx30" in df_ann.columns:
                st.metric("Jours > 30 °C",
                          f"{int(last['nb_jours_tx30'])} j/an",
                          delta=f"{int(last['nb_jours_tx30']) - int(first['nb_jours_tx30']):+d} j")
        with c4:
            if "precip_mm" in df_ann.columns:
                st.metric("Précipitations",
                          f"{last['precip_mm']:,.0f} mm",
                          delta=f"{last['precip_mm'] - first['precip_mm']:+.0f} mm")

    col_l, col_r = st.columns([3, 2])

    with col_l:
        if not df_ann.empty and "temp_moy_c" in df_ann.columns:
            df_plot = df_ann.copy()
            df_plot["roll10"] = df_plot["temp_moy_c"].rolling(10, center=True, min_periods=5).mean()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_plot["annee"], y=df_plot["temp_moy_c"],
                mode="lines", name="Température annuelle",
                line=dict(color="#a29bfe", width=1.2), opacity=0.7))
            fig.add_trace(go.Scatter(x=df_plot["annee"], y=df_plot["roll10"],
                mode="lines", name="Moy. mobile 10 ans",
                line=dict(color="#fd79a8", width=2.8)))
            ref_mask = df_ann["annee"].between(1961, 1990)
            if ref_mask.any():
                ref = df_ann.loc[ref_mask, "temp_moy_c"].mean()
                fig.add_hline(y=ref, line_dash="dash", line_color="#00b894",
                              annotation_text=f"Normale 1961–90 ({ref:.1f} °C)")
            apply_theme(fig, "Évolution de la température moyenne", 380)
            fig.update_yaxes(title_text="°C")
            fig.update_layout(legend=dict(orientation="h", y=1.08))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de données de température pour la période sélectionnée.")

    with col_r:
        if not df_ann.empty and "anomalie_temp_c" in df_ann.columns:
            df_plot = df_ann.dropna(subset=["anomalie_temp_c"]).copy()
            df_plot["decennie"] = (df_plot["annee"] // 10 * 10).astype(str) + "s"
            anom_dec = (df_plot.groupby("decennie")["anomalie_temp_c"]
                        .agg(val="mean", n="count").reset_index())
            anom_dec = anom_dec[anom_dec["n"] > 2].copy()
            anom_dec["anomalie_temp_c"] = anom_dec["val"].round(2)
            fig2 = go.Figure(go.Bar(
                x=anom_dec["decennie"], y=anom_dec["anomalie_temp_c"],
                marker_color=["#e74c3c" if v > 0.5 else "#f39c12" if v > 0 else "#74b9ff"
                               for v in anom_dec["anomalie_temp_c"]],
                text=[f"{v:+.2f}°C" for v in anom_dec["anomalie_temp_c"]],
                textposition="outside"))
            apply_theme(fig2, "Anomalie par décennie", 380)
            fig2.update_yaxes(title_text="Anomalie (°C)")
            st.plotly_chart(fig2, use_container_width=True)

    if not df_ann.empty and "precip_mm" in df_ann.columns:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df_ann["annee"], y=df_ann["precip_mm"],
            name="Précipitations (mm)", marker_color="#74b9ff", opacity=0.7))
        roll_p = df_ann["precip_mm"].rolling(10, center=True, min_periods=5).mean()
        fig3.add_trace(go.Scatter(x=df_ann["annee"], y=roll_p, mode="lines",
            name="Moy. mobile 10 ans", line=dict(color="#fdcb6e", width=2.5)))
        apply_theme(fig3, "Précipitations annuelles", 320)
        fig3.update_yaxes(title_text="mm/an")
        fig3.update_layout(legend=dict(orientation="h"))
        st.plotly_chart(fig3, use_container_width=True)

    if not df_ann.empty and all(c in df_ann.columns for c in ["tmin_moy_c", "tmax_moy_c"]):
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=df_ann["annee"], y=df_ann["tmax_moy_c"],
            mode="lines", name="Tmax moy.", line=dict(color="#e17055")))
        fig4.add_trace(go.Scatter(x=df_ann["annee"], y=df_ann["tmin_moy_c"],
            mode="lines", name="Tmin moy.", line=dict(color="#74b9ff"),
            fill="tonexty", fillcolor="rgba(116,185,255,0.08)"))
        apply_theme(fig4, "Enveloppe Tmin / Tmax", 320)
        fig4.update_yaxes(title_text="°C")
        fig4.update_layout(legend=dict(orientation="h"))
        st.plotly_chart(fig4, use_container_width=True)


def _tab_carte_france(data: dict, periode: tuple):
    df_st  = data["stations"]
    df_mon = data["meteo_monthly"]

    if df_st.empty or "lat" not in df_st.columns:
        st.info("Aucune donnée GPS de stations disponible.")
        return

    col_var, col_per = st.columns(2)
    with col_var:
        variable_map = {
            "Température moyenne (°C)": "temp_moy_c",
            "Température max (°C)":     "tmax_moy_c",
            "Température min (°C)":     "tmin_moy_c",
            "Précipitations moy. (mm)": "precip_moy_mm",
        }
        var_label = st.selectbox("Variable", list(variable_map.keys()), key="carte_var")
        var_col   = variable_map[var_label]
    with col_per:
        st.info(f"Période : **{periode[0]}–{periode[1]}** (modifiable dans la barre latérale)")

    if not df_mon.empty and "nom_station" in df_mon.columns:
        mask = df_mon["annee"].between(*periode)
        df_p = df_mon[mask].copy()
        agg: dict[str, tuple] = {}
        col_src_map = {"temp_moy_c": "tmoy", "tmax_moy_c": "tmax",
                       "tmin_moy_c": "tmin", "precip_moy_mm": "precip_mm"}
        for dst, src in col_src_map.items():
            if src in df_p.columns:
                agg[dst] = (src, "mean")
        if agg:
            df_stats = (df_p.dropna(subset=["nom_station"])
                        .groupby("nom_station", as_index=False).agg(**agg))
            gps_cols = [c for c in ["nom_station", "lat", "lon", "altitude"] if c in df_st.columns]
            df_map = df_st[gps_cols].merge(df_stats, on="nom_station", how="inner")
        else:
            df_map = df_st.copy()
    else:
        df_map = df_st.copy()

    for c in ["temp_moy_c", "tmax_moy_c", "tmin_moy_c", "precip_moy_mm"]:
        if c in df_map.columns:
            df_map[c] = df_map[c].round(2)
    df_map = df_map.dropna(subset=["lat", "lon"])

    if df_map.empty or var_col not in df_map.columns:
        st.warning(f"Pas de données '{var_label}' pour cette sélection.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Stations", len(df_map))
    k2.metric("Min", f"{df_map[var_col].min():.1f}")
    k3.metric("Max", f"{df_map[var_col].max():.1f}")
    k4.metric("Moy. nationale", f"{df_map[var_col].mean():.1f}")

    colorscale = "Blues" if "précip" in var_label.lower() else "RdYlBu_r"
    hover_cols = {c: True for c in ["temp_moy_c", "tmax_moy_c", "tmin_moy_c", "precip_moy_mm", "altitude"]
                  if c in df_map.columns}

    v = df_map[var_col].fillna(0)
    v_min, v_max = v.min(), v.max()
    df_map["_size"] = (4 + 14 * (v - v_min) / (v_max - v_min)) if v_max > v_min else 10.0

    fig = px.scatter_mapbox(
        df_map, lat="lat", lon="lon", color=var_col,
        hover_name="nom_station", hover_data=hover_cols,
        color_continuous_scale=colorscale,
        size="_size", size_max=18,
        zoom=4.8, center={"lat": 46.6, "lon": 2.3},
        mapbox_style="carto-darkmatter",
        title=f"{var_label} par station ({periode[0]}–{periode[1]})",
        labels={var_col: var_label},
    )
    fig.update_traces(marker=dict(opacity=0.85))
    fig.update_layout(height=580, margin=dict(t=50, b=0),
        coloraxis_colorbar=dict(title=var_label, thickness=14, len=0.7))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Distribution des valeurs par station"):
        fig_hist = px.histogram(df_map, x=var_col, nbins=30,
            color_discrete_sequence=["#a29bfe"], labels={var_col: var_label},
            title=f"Distribution — {var_label}")
        fig_hist.update_layout(height=300)
        apply_theme(fig_hist)
        st.plotly_chart(fig_hist, use_container_width=True)

    col_top, col_bot = st.columns(2)
    with col_top:
        st.subheader(f"Top 10 — {var_label}")
        st.dataframe(df_map[["nom_station", var_col]].nlargest(10, var_col).reset_index(drop=True),
                     use_container_width=True)
    with col_bot:
        st.subheader(f"Bottom 10 — {var_label}")
        st.dataframe(df_map[["nom_station", var_col]].nsmallest(10, var_col).reset_index(drop=True),
                     use_container_width=True)


def _tab_stations(data: dict):
    df_st = data["stations"]
    if df_st.empty:
        st.info("Aucune donnée GPS de stations disponible.")
        return

    if "lat" in df_st.columns and "lon" in df_st.columns:
        color_col  = "temp_moy_c" if "temp_moy_c" in df_st.columns else None
        hover_data = {c: True for c in ["precip_moy_mm", "n_obs", "annee_min", "annee_max"]
                      if c in df_st.columns}
        fig = px.scatter_mapbox(df_st.dropna(subset=["lat", "lon"]),
            lat="lat", lon="lon", color=color_col,
            hover_name="nom_station" if "nom_station" in df_st.columns else None,
            hover_data=hover_data, color_continuous_scale="RdYlBu_r",
            size_max=12, zoom=4.5, center={"lat": 46.6, "lon": 2.3},
            mapbox_style="carto-darkmatter",
            title=f"{len(df_st)} stations — température moyenne")
        fig.update_traces(marker=dict(size=8))
        fig.update_layout(height=500, margin=dict(t=50))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tableau des stations")
    display_cols = [c for c in ["nom_station", "lat", "lon", "altitude",
                                 "temp_moy_c", "precip_moy_mm", "n_obs",
                                 "annee_min", "annee_max"] if c in df_st.columns]
    st.dataframe(
        df_st[display_cols].round(2).sort_values("nom_station")
        if "nom_station" in df_st.columns else df_st[display_cols].round(2),
        use_container_width=True, height=400)


def _tab_mensuel(data: dict):
    df_m = data["meteo_monthly"]
    if df_m.empty:
        st.info("Aucune donnée mensuelle disponible.")
        return

    stations: list[str] = []
    if "nom_station" in df_m.columns:
        stations = sorted(df_m["nom_station"].dropna().unique().tolist())

    st.info(f"**{len(df_m):,}** observations mensuelles · "
            f"**{len(stations)}** stations · "
            f"**{int(df_m['annee'].min())}–{int(df_m['annee'].max())}**")

    col1, col2 = st.columns(2)
    with col1:
        station_m = st.selectbox("Station", stations, key="mensuel_station")
    with col2:
        variable = st.selectbox("Variable",
            [c for c in ["tmoy", "tmax", "tmin", "precip_mm", "nb_jours_tx30", "etp"]
             if c in df_m.columns], key="mensuel_var")

    labels = {"tmoy": "Température moyenne (°C)", "tmax": "Température maximale (°C)",
              "tmin": "Température minimale (°C)", "precip_mm": "Précipitations (mm)",
              "nb_jours_tx30": "Jours Tmax > 30 °C", "etp": "ETP (mm)"}

    df_s = (df_m[df_m["nom_station"] == station_m].copy()
            if station_m and "nom_station" in df_m.columns else df_m.copy())
    df_s = df_s.dropna(subset=[variable]) if variable in df_s.columns else df_s

    if df_s.empty or variable not in df_s.columns:
        st.warning("Pas de données pour cette sélection.")
        return

    df_s["date_plot"] = pd.to_datetime(
        df_s["annee"].astype(str) + "-" + df_s["mois"].astype(str).str.zfill(2),
        format="%Y-%m", errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_s["date_plot"], y=df_s[variable], mode="lines",
        line=dict(color="#a29bfe", width=1), name=labels.get(variable, variable)))
    roll = df_s[variable].rolling(12, center=True, min_periods=6).mean()
    fig.add_trace(go.Scatter(x=df_s["date_plot"], y=roll, mode="lines",
        line=dict(color="#fd79a8", width=2.5), name="Moy. mobile 12 mois"))
    apply_theme(fig, f"{labels.get(variable, variable)} — {station_m}", 400)
    fig.update_yaxes(title_text=labels.get(variable, variable))
    fig.update_layout(legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    if "mois" in df_s.columns:
        mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                       "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        saison = df_s.groupby("mois")[variable].mean().reset_index()
        saison["mois_label"] = saison["mois"].apply(
            lambda m: mois_labels[int(m) - 1] if pd.notna(m) and 1 <= int(m) <= 12 else "?")
        fig_s = go.Figure(go.Bar(x=saison["mois_label"], y=saison[variable].round(2),
            marker_color="#81ecec", text=saison[variable].round(1), textposition="outside"))
        apply_theme(fig_s, f"Saisonnalité moyenne — {station_m}", 300)
        fig_s.update_yaxes(title_text=labels.get(variable, variable))
        st.plotly_chart(fig_s, use_container_width=True)


# ── Point d'entrée ──────────────────────────────────────────────────────────

def tab_temperatures(data: dict, periode: tuple):
    """
    Onglet Températures réelles Météo France.
    `data`   : dict retourné par src.data_loader.load_all()
    `periode`: tuple (annee_min, annee_max) depuis la sidebar
    """
    df_m = data.get("meteo_monthly", pd.DataFrame())
    df_ann = data.get("meteo_annual", pd.DataFrame())

    if df_ann.empty and df_m.empty:
        st.warning("Données Météo France introuvables. Vérifiez `data/raw/avant_1960.csv` et `apres_1960.csv`.")
        return

    # Sélecteur de station (en haut de l'onglet)
    all_stations: list[str] = []
    if not df_m.empty and "nom_station" in df_m.columns:
        all_stations = sorted(df_m["nom_station"].dropna().unique().tolist())

    station_sel = st.selectbox(
        "Station météo",
        options=["Toutes (moyenne nationale)"] + all_stations,
        index=0,
        key="temp_station_sel",
    )

    sub1, sub2, sub3, sub4 = st.tabs([
        "Historique",
        "Carte France",
        "Stations",
        "Mensuel / Station",
    ])

    with sub1:
        _tab_historique(data, station_sel, periode)
    with sub2:
        _tab_carte_france(data, periode)
    with sub3:
        _tab_stations(data)
    with sub4:
        _tab_mensuel(data)
