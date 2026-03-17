"""
pages/1_🌡️_Temperatures.py
============================
Page Températures — historique, anomalies, carte France, mensuel par station.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_all

# ── CSS partagé ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    section[data-testid="stSidebar"] { background-color: #12151c; }
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #6c5ce7;
        border-radius: 12px;
        padding: 12px 16px;
    }
    h1 { color: #a29bfe !important; letter-spacing: -0.5px; }
    h2 { color: #81ecec !important; }
    h3 { color: #dfe6e9 !important; }
    .stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 0.9rem; color: #b2bec3; }
    .stTabs [aria-selected="true"] { color: #a29bfe !important; border-bottom: 2px solid #a29bfe; }
</style>
""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  CHARGEMENT (cache partagé entre pages via st.cache_data)   ║
# ╚══════════════════════════════════════════════════════════════╝
@st.cache_data(ttl=1800, show_spinner=False)
def _load() -> dict[str, pd.DataFrame]:
    return load_all()


# ╔══════════════════════════════════════════════════════════════╗
# ║  SIDEBAR                                                    ║
# ╚══════════════════════════════════════════════════════════════╝
def render_sidebar(data: dict) -> dict:
    df_ann = data["meteo_annual"]
    df_m   = data["meteo_monthly"]

    with st.sidebar:
        st.markdown("## 🌡️ Températures")
        st.divider()

        # Période
        st.subheader("📅 Période")
        y_min = int(df_ann["annee"].min()) if not df_ann.empty else 1900
        y_max = int(df_ann["annee"].max()) if not df_ann.empty else 2025
        periode = st.slider("Période historique", y_min, y_max, (max(y_min, 1950), y_max))

        st.divider()

        # Station
        st.subheader("📡 Station")
        all_stations: list[str] = []
        if not df_m.empty and "nom_station" in df_m.columns:
            all_stations = sorted(df_m["nom_station"].dropna().unique().tolist())
        station_sel = st.selectbox(
            "Station météo",
            options=["Toutes (moyenne nationale)"] + all_stations,
            index=0,
        )

        st.divider()

        # Infos
        st.subheader("ℹ️ Données chargées")
        if not df_m.empty:
            st.info(
                f"**{len(df_m):,}** obs. mensuelles\n\n"
                f"**{df_m['nom_station'].nunique() if 'nom_station' in df_m.columns else '?'}** stations\n\n"
                f"Période : **{y_min}–{y_max}**"
            )

    return {"periode": periode, "station": station_sel}


# ╔══════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                    ║
# ╚══════════════════════════════════════════════════════════════╝
def _filter_annual(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    return df[df["annee"].between(*params["periode"])].copy()


def _filter_monthly_station(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    if df.empty:
        return df
    station = params["station"]
    if station == "Toutes (moyenne nationale)" or "nom_station" not in df.columns:
        return df
    return df[df["nom_station"] == station].copy()


def _annual_for_station(df_monthly: pd.DataFrame, params: dict) -> pd.DataFrame:
    df = _filter_monthly_station(df_monthly, params)
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
    out = out[out["annee"].between(*params["periode"])].sort_values("annee")
    return out


# ╔══════════════════════════════════════════════════════════════╗
# ║  ONGLET 1 — HISTORIQUE                                      ║
# ╚══════════════════════════════════════════════════════════════╝
def tab_historique(data: dict, params: dict):
    df_ann = _filter_annual(data["meteo_annual"], params)

    if params["station"] != "Toutes (moyenne nationale)":
        df_station = _annual_for_station(data["meteo_monthly"], params)
        if not df_station.empty:
            df_ann = df_station

    st.markdown("### 📈 Température & Précipitations historiques")

    # KPIs
    if not df_ann.empty:
        last, first = df_ann.iloc[-1], df_ann.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if "temp_moy_c" in df_ann.columns:
                st.metric("🌡️ Temp. moy. (dernière année)",
                          f"{last['temp_moy_c']:.1f} °C",
                          delta=f"{last['temp_moy_c']-first['temp_moy_c']:+.2f} °C sur la période")
        with c2:
            if "tmax_moy_c" in df_ann.columns:
                st.metric("🔆 Tmax moy.",
                          f"{last['tmax_moy_c']:.1f} °C",
                          delta=f"{last['tmax_moy_c']-first['tmax_moy_c']:+.2f} °C")
        with c3:
            if "nb_jours_tx30" in df_ann.columns:
                st.metric("☀️ Jours > 30 °C",
                          f"{int(last['nb_jours_tx30'])} j/an",
                          delta=f"{int(last['nb_jours_tx30'])-int(first['nb_jours_tx30']):+d} j")
        with c4:
            if "precip_mm" in df_ann.columns:
                st.metric("🌧️ Précipitations",
                          f"{last['precip_mm']:,.0f} mm",
                          delta=f"{last['precip_mm']-first['precip_mm']:+.0f} mm")

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
                              annotation_text=f"Normale 1961-90 ({ref:.1f} °C)")
            fig.update_layout(title="🌡️ Évolution de la température moyenne",
                template="plotly_dark", height=380,
                xaxis_title="Année", yaxis_title="°C",
                legend=dict(orientation="h", y=1.08), margin=dict(t=80))
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
            fig2.update_layout(title="📊 Anomalie par décennie",
                template="plotly_dark", height=380,
                xaxis_title="Décennie", yaxis_title="Anomalie (°C)")
            st.plotly_chart(fig2, use_container_width=True)

    # Précipitations
    if not df_ann.empty and "precip_mm" in df_ann.columns:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(x=df_ann["annee"], y=df_ann["precip_mm"],
            name="Précipitations (mm)", marker_color="#74b9ff", opacity=0.7))
        roll_p = df_ann["precip_mm"].rolling(10, center=True, min_periods=5).mean()
        fig3.add_trace(go.Scatter(x=df_ann["annee"], y=roll_p, mode="lines",
            name="Moy. mobile 10 ans", line=dict(color="#fdcb6e", width=2.5)))
        fig3.update_layout(title="🌧️ Précipitations annuelles",
            template="plotly_dark", height=320,
            xaxis_title="Année", yaxis_title="mm/an",
            legend=dict(orientation="h"))
        st.plotly_chart(fig3, use_container_width=True)

    # Enveloppe Tmin / Tmax
    if not df_ann.empty and all(c in df_ann.columns for c in ["tmin_moy_c", "tmax_moy_c"]):
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=df_ann["annee"], y=df_ann["tmax_moy_c"],
            mode="lines", name="Tmax moy.", line=dict(color="#e17055")))
        fig4.add_trace(go.Scatter(x=df_ann["annee"], y=df_ann["tmin_moy_c"],
            mode="lines", name="Tmin moy.", line=dict(color="#74b9ff"),
            fill="tonexty", fillcolor="rgba(116,185,255,0.08)"))
        fig4.update_layout(title="🌡️ Enveloppe Tmin / Tmax",
            template="plotly_dark", height=320,
            xaxis_title="Année", yaxis_title="°C",
            legend=dict(orientation="h"))
        st.plotly_chart(fig4, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  ONGLET 2 — CARTE FRANCE                                    ║
# ╚══════════════════════════════════════════════════════════════╝
def tab_carte_france(data: dict, params: dict):
    st.markdown("### 🗺️ Carte des températures par station — France")

    df_st  = data["stations"]
    df_mon = data["meteo_monthly"]

    if df_st.empty or "lat" not in df_st.columns:
        st.info("Aucune donnée GPS de stations disponible.")
        return

    col_var, col_per = st.columns(2)
    with col_var:
        variable_map = {
            "Température moyenne (°C)":  "temp_moy_c",
            "Température max (°C)":      "tmax_moy_c",
            "Température min (°C)":      "tmin_moy_c",
            "Précipitations moy. (mm)":  "precip_moy_mm",
        }
        var_label = st.selectbox("Variable", list(variable_map.keys()), key="carte_var")
        var_col   = variable_map[var_label]
    with col_per:
        periode = params["periode"]
        st.info(f"Période sélectionnée : **{periode[0]}–{periode[1]}**\n\n"
                f"(modifiable dans la barre latérale)")

    # Calcul stats par station sur la période
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
    k1.metric("📍 Stations", len(df_map))
    k2.metric(f"Min", f"{df_map[var_col].min():.1f}")
    k3.metric(f"Max", f"{df_map[var_col].max():.1f}")
    k4.metric(f"Moy. nationale", f"{df_map[var_col].mean():.1f}")

    colorscale = "Blues" if "précip" in var_label.lower() else "RdYlBu_r"

    hover_cols = {c: True for c in ["temp_moy_c", "tmax_moy_c", "tmin_moy_c",
                                     "precip_moy_mm", "altitude"] if c in df_map.columns}

    # Taille normalisée sans NaN
    size_col = f"_size_{var_col}"
    v = df_map[var_col].fillna(0)
    v_min, v_max = v.min(), v.max()
    df_map[size_col] = (4 + 14 * (v - v_min) / (v_max - v_min)) if v_max > v_min else 10.0

    fig = px.scatter_mapbox(
        df_map, lat="lat", lon="lon", color=var_col,
        hover_name="nom_station", hover_data=hover_cols,
        color_continuous_scale=colorscale,
        size=size_col, size_max=18,
        zoom=4.8, center={"lat": 46.6, "lon": 2.3},
        mapbox_style="carto-darkmatter",
        title=f"🗺️ {var_label} par station ({periode[0]}–{periode[1]})",
        labels={var_col: var_label},
    )
    fig.update_traces(marker=dict(opacity=0.85))
    fig.update_layout(template="plotly_dark", height=580, margin=dict(t=50, b=0),
        coloraxis_colorbar=dict(title=var_label, thickness=14, len=0.7))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📊 Distribution des valeurs par station"):
        fig_hist = px.histogram(df_map, x=var_col, nbins=30,
            color_discrete_sequence=["#a29bfe"], labels={var_col: var_label},
            title=f"Distribution — {var_label}")
        fig_hist.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig_hist, use_container_width=True)

    col_top, col_bot = st.columns(2)
    with col_top:
        st.subheader(f"🔆 Top 10 — {var_label}")
        st.dataframe(df_map[["nom_station", var_col]].nlargest(10, var_col).reset_index(drop=True),
                     use_container_width=True)
    with col_bot:
        st.subheader(f"❄️ Bottom 10 — {var_label}")
        st.dataframe(df_map[["nom_station", var_col]].nsmallest(10, var_col).reset_index(drop=True),
                     use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  ONGLET 3 — STATIONS                                        ║
# ╚══════════════════════════════════════════════════════════════╝
def tab_stations(data: dict):
    st.markdown("### 📡 Réseau de stations météo")

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
            title=f"📍 {len(df_st)} stations — température moyenne")
        fig.update_traces(marker=dict(size=8))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(t=50))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Tableau des stations")
    display_cols = [c for c in ["nom_station", "lat", "lon", "altitude",
                                 "temp_moy_c", "precip_moy_mm", "n_obs",
                                 "annee_min", "annee_max"] if c in df_st.columns]
    st.dataframe(
        df_st[display_cols].round(2).sort_values("nom_station")
        if "nom_station" in df_st.columns else df_st[display_cols].round(2),
        use_container_width=True, height=400)


# ╔══════════════════════════════════════════════════════════════╗
# ║  ONGLET 4 — MENSUEL PAR STATION                             ║
# ╚══════════════════════════════════════════════════════════════╝
def tab_mensuel(data: dict, params: dict):
    st.markdown("### 📆 Données mensuelles par station")

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
    fig.update_layout(title=f"{labels.get(variable, variable)} — {station_m}",
        template="plotly_dark", height=400,
        xaxis_title="Date", yaxis_title=labels.get(variable, variable),
        legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

    if "mois" in df_s.columns:
        mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                       "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        saison = df_s.groupby("mois")[variable].mean().reset_index()
        saison["mois_label"] = saison["mois"].apply(
            lambda m: mois_labels[int(m)-1] if pd.notna(m) and 1 <= int(m) <= 12 else "?")
        fig_s = go.Figure(go.Bar(x=saison["mois_label"], y=saison[variable].round(2),
            marker_color="#81ecec", text=saison[variable].round(1), textposition="outside"))
        fig_s.update_layout(title=f"Saisonnalité moyenne — {station_m}",
            template="plotly_dark", height=300,
            xaxis_title="Mois", yaxis_title=labels.get(variable, variable))
        st.plotly_chart(fig_s, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  MAIN                                                       ║
# ╚══════════════════════════════════════════════════════════════╝
st.title("🌡️ Températures — Météo France")
st.caption("Données historiques · Hackathon #26 · Sup²Vinci · Mars 2026")

with st.spinner("⏳ Chargement des données météo…"):
    data = _load()

params = render_sidebar(data)

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Historique",
    "🗺️ Carte France",
    "📡 Stations",
    "📆 Mensuel / Station",
])

with tab1:
    tab_historique(data, params)
with tab2:
    tab_carte_france(data, params)
with tab3:
    tab_stations(data)
with tab4:
    tab_mensuel(data, params)

st.divider()
st.caption("Source : Météo France (avant_1960.csv / apres_1960.csv) | Hackathon #26 — Sup²Vinci")
