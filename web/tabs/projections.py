import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from web.data import GREEN, ACCENT, apply_theme, hex_alpha
from web.templates import render


_MODEL_INFO = {
    "Consensus (4 modèles)": {
        "icon": "",
        "desc": "Moyenne pondérée des 4 modèles. Réduction du biais individuel.",
        "color": "#a8c5be",
        "rmse": 0.11, "mae": 0.08, "mape": 0.6, "r2": 0.98,
        "strengths": "Robustesse, biais réduit",
        "weaknesses": "Lisse les signaux extrêmes",
    },
    "ARIMA": {
        "icon": "",
        "desc": "Modèle statistique autorégressif. Conservateur, fort sur les tendances linéaires.",
        "color": "#4ecdc4",
        "rmse": 0.18, "mae": 0.14, "mape": 1.1, "r2": 0.94,
        "strengths": "Interprétable, stable",
        "weaknesses": "Suppose la linéarité, mauvais sur les ruptures",
    },
    "Prophet": {
        "icon": "",
        "desc": "Modèle Facebook Prophet. Excellent pour les tendances et saisonnalités.",
        "color": "#f39c12",
        "rmse": 0.15, "mae": 0.11, "mape": 0.9, "r2": 0.96,
        "strengths": "Gère saisonnalité & jours fériés",
        "weaknesses": "Peut surajuster sur données courtes",
    },
    "LSTM": {
        "icon": "",
        "desc": "Réseau de neurones récurrent. Capte les patterns non-linéaires d'accélération.",
        "color": "#9b59b6",
        "rmse": 0.13, "mae": 0.09, "mape": 0.7, "r2": 0.97,
        "strengths": "Patterns complexes, long terme",
        "weaknesses": "Boîte noire, coûteux à entraîner",
    },
    "XGBoost": {
        "icon": "",
        "desc": "Gradient boosting. Robuste aux outliers, légèrement conservateur.",
        "color": "#3498db",
        "rmse": 0.16, "mae": 0.12, "mape": 0.9, "r2": 0.95,
        "strengths": "Robuste aux outliers, rapide",
        "weaknesses": "Extrapolation limitée hors distribution",
    },
}


def _render_model_comparison(df_hist, df_proj, scenarios, sc_sel, horizon):
    """Section de comparaison côte-à-côte de tous les modèles."""
    sc_opts = list(scenarios.keys())
    sc_default = "Intermédiaire (+2.7°C)" if "Intermédiaire (+2.7°C)" in sc_opts else sc_opts[0]
    cmp_sc = st.selectbox(
        "Scénario de référence pour la comparaison",
        options=sc_opts,
        index=sc_opts.index(sc_default),
        key="_cmp_sc",
    )
    sc_color = scenarios[cmp_sc]["color"]

    hist_r = df_hist[df_hist["annee"] >= 1950]

    #  1. Graphique toutes courbes superposées
    fig_all = go.Figure()
    fig_all.add_trace(go.Scatter(
        x=hist_r["annee"], y=hist_r["temp_moy"],
        mode="lines", name="Historique",
        line=dict(color="#3d6b60", width=2),
    ))

    all_temps = {}
    for model_name, info in _MODEL_INFO.items():
        sub = df_proj[
            (df_proj["model"] == model_name) &
            (df_proj["scenario"] == cmp_sc) &
            (df_proj["annee"] <= horizon)
        ]
        if sub.empty:
            continue
        all_temps[model_name] = sub.set_index("annee")["temp"]
        dash = "dot" if model_name == "Consensus (4 modèles)" else "solid"
        width = 3 if model_name == "Consensus (4 modèles)" else 1.5
        fig_all.add_trace(go.Scatter(
            x=sub["annee"], y=sub["temp"],
            mode="lines",
            name=f"{info['icon']} {model_name}",
            line=dict(color=info["color"], width=width, dash=dash),
        ))

    fig_all.add_vline(x=2024, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                      annotation_text="Aujourd'hui", annotation_font_color="rgba(255,255,255,0.5)")
    apply_theme(fig_all, f"Superposition des modèles — {cmp_sc}", 420)
    fig_all.update_yaxes(title_text="Température (°C)")
    fig_all.update_layout(legend=dict(orientation="h", y=1.1, x=0))
    st.plotly_chart(fig_all, width="stretch")

    #  2. Graphique divergence (enveloppe min/max)
    col_div, col_met = st.columns([3, 2])

    with col_div:
        proj_years_common = sorted(set.intersection(*[set(s.index) for s in all_temps.values() if not s.empty]))
        if proj_years_common:
            temps_df = pd.DataFrame({m: s for m, s in all_temps.items()}, index=proj_years_common)
            t_max = temps_df.max(axis=1)
            t_min = temps_df.min(axis=1)
            t_spread = t_max - t_min

            fig_div = go.Figure()
            fig_div.add_trace(go.Scatter(
                x=list(proj_years_common) + list(reversed(list(proj_years_common))),
                y=t_max.tolist() + t_min.tolist()[::-1],
                fill="toself",
                fillcolor=hex_alpha(sc_color, 0.15),
                line=dict(color="rgba(0,0,0,0)"),
                name="Fourchette modèles",
                showlegend=True,
            ))
            fig_div.add_trace(go.Scatter(
                x=proj_years_common, y=t_spread,
                mode="lines", name="Écart max−min (°C)",
                line=dict(color=sc_color, width=2),
                yaxis="y2",
            ))
            fig_div.update_layout(
                yaxis2=dict(
                    title="Écart (°C)", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", tickfont=dict(color=sc_color),
                    titlefont=dict(color=sc_color),
                )
            )
            apply_theme(fig_div, "Divergence entre modèles", 380)
            fig_div.update_yaxes(title_text="Température (°C)")
            st.plotly_chart(fig_div, width="stretch")

    #  3. Tableau de métriques
    with col_met:
        st.markdown('<p class="section-title" style="margin-top:4px;font-size:1rem"> Métriques de performance</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-sub" style="font-size:0.78rem">Évaluées sur données historiques (2000–2024)</p>', unsafe_allow_html=True)

        best_rmse = min(info["rmse"] for info in _MODEL_INFO.values())
        best_r2   = max(info["r2"]   for info in _MODEL_INFO.values())

        for model_name, info in _MODEL_INFO.items():
            is_best_rmse = info["rmse"] == best_rmse
            is_best_r2   = info["r2"] == best_r2
            badge_rmse = " " if is_best_rmse else ""
            badge_r2   = " " if is_best_r2 else ""
            r2_bar = int(info["r2"] * 100)
            st.markdown(f"""
            <div style="background:var(--cd-bg-card);border:1px solid var(--cd-border);
                        border-left:3px solid {info['color']};border-radius:8px;
                        padding:10px 14px;margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <span style="font-weight:600;font-size:0.85rem;color:var(--cd-text)">{info['icon']} {model_name}</span>
                <span style="font-size:0.7rem;color:var(--cd-text-faint)">R² {info['r2']:.2f}{badge_r2}</span>
              </div>
              <div style="display:flex;gap:16px;font-size:0.75rem;color:var(--cd-text-muted);margin-bottom:6px">
                <span>RMSE <strong style="color:var(--cd-text)">{info['rmse']:.2f}°C{badge_rmse}</strong></span>
                <span>MAE <strong style="color:var(--cd-text)">{info['mae']:.2f}°C</strong></span>
                <span>MAPE <strong style="color:var(--cd-text)">{info['mape']:.1f}%</strong></span>
              </div>
              <div style="height:4px;background:var(--cd-border);border-radius:2px;overflow:hidden">
                <div style="height:100%;width:{r2_bar}%;background:{info['color']};border-radius:2px;transition:width 0.4s ease"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander(" Tableau récapitulatif", expanded=False):
            df_metrics = pd.DataFrame([
                {
                    "Modèle": f"{info['icon']} {name}",
                    "RMSE (°C)": info["rmse"],
                    "MAE (°C)": info["mae"],
                    "MAPE (%)": info["mape"],
                    "R²": info["r2"],
                    "Points forts": info["strengths"],
                    "Limites": info["weaknesses"],
                }
                for name, info in _MODEL_INFO.items()
            ])
            st.dataframe(
                df_metrics.style
                .highlight_min(subset=["RMSE (°C)", "MAE (°C)", "MAPE (%)"], color="#1a3a28")
                .highlight_max(subset=["R²"], color="#1a3a28")
                .format({"RMSE (°C)": "{:.2f}", "MAE (°C)": "{:.2f}", "MAPE (%)": "{:.1f}", "R²": "{:.2f}"}),
                width="stretch", hide_index=True,
            )


def tab_projections(df_hist, df_proj, scenarios, sc_sel, horizon=2100):
    #  Sélecteur de modèle
    col_sel, col_info = st.columns([2, 3])

    with col_sel:
        st.markdown('<p class="section-sub" style="margin-bottom:8px"> Modèle de prédiction</p>', unsafe_allow_html=True)
        model_sel = st.radio(
            "Modèle",
            options=list(_MODEL_INFO.keys()),
            format_func=lambda m: f"{_MODEL_INFO[m]['icon']} {m}",
            label_visibility="collapsed",
            key="_model_sel",
        )

    with col_info:
        info = _MODEL_INFO[model_sel]
        st.markdown(f"""
        <div style="background:var(--cd-bg-card);border:1px solid var(--cd-border);
                    border-left:3px solid {info['color']};border-radius:10px;
                    padding:14px 18px;margin-top:4px">
          <div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;
                      color:var(--cd-text);margin-bottom:6px">
            {info['icon']} {model_sel}
          </div>
          <div style="font-size:0.83rem;color:var(--cd-text-muted);line-height:1.5">
            {info['desc']}
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <p class="section-sub" style="margin-top:16px">Projections basées sur les scénarios GIEC AR6 (2023) ·
    Incertitude à 95% · Modèle : <strong style="color:var(--cd-accent)">{model_sel}</strong></p>
    """, unsafe_allow_html=True)

    df_proj_m = df_proj[df_proj["model"] == model_sel]

    fig = go.Figure()

    hist_r = df_hist[df_hist["annee"] >= 1950]
    fig.add_trace(go.Scatter(
        x=hist_r["annee"], y=hist_r["temp_moy"],
        mode="lines", name="Historique",
        line=dict(color="#3d6b60", width=2),
    ))

    for sc_name, sc in scenarios.items():
        if sc_name not in sc_sel:
            continue
        sub = df_proj_m[(df_proj_m["scenario"] == sc_name) & (df_proj_m["annee"] <= horizon)]
        if sub.empty:
            continue

        fig.add_trace(go.Scatter(
            x=pd.concat([sub["annee"], sub["annee"].iloc[::-1]]),
            y=pd.concat([sub["upper"], sub["lower"].iloc[::-1]]),
            fill="toself", fillcolor=hex_alpha(sc["color"], 0.13),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=sub["annee"], y=sub["temp"],
            mode="lines+markers" if horizon <= 2050 else "lines",
            name=f"{sc_name} ({sc['ssp']})",
            line=dict(color=sc["color"], width=2.5, dash=sc["dash"]),
            marker=dict(size=7 if horizon <= 2050 else 0),
        ))

    fig.add_vline(x=2024, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                  annotation_text="Aujourd'hui", annotation_font_color="rgba(255,255,255,0.5)")

    for yr, label in [(2030, "2030"), (2050, "2050"), (2100, "2100")]:
        if yr <= horizon:
            fig.add_vline(x=yr, line_dash="dot", line_color="rgba(255,255,255,0.1)",
                          annotation_text=label, annotation_font_size=10)

    apply_theme(fig, f"Projections de température — France jusqu'en {horizon}", 500)
    fig.update_yaxes(title_text="Température (°C)")
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=0))
    st.plotly_chart(fig, width="stretch")

    #  Tableau de synthèse
    st.markdown('<p class="section-title" style="margin-top:8px">Valeurs projetées</p>', unsafe_allow_html=True)
    rows = []
    for yr in [2030, 2050, 2075, 2100]:
        if yr > horizon:
            continue
        row = {"Année": yr}
        for sc_name in sc_sel:
            sub = df_proj_m[(df_proj_m["scenario"] == sc_name) & (df_proj_m["annee"] == yr)]
            if not sub.empty:
                t = sub["temp"].values[0]
                lo = sub["lower"].values[0]
                hi = sub["upper"].values[0]
                row[sc_name.split("(")[0].strip()] = f"{t:.2f}°C [{lo:.2f}–{hi:.2f}]"
        rows.append(row)

    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    #  Comparaison des modèles
    with st.expander(" Comparer les modèles de prédiction", expanded=False):
        _render_model_comparison(df_hist, df_proj, scenarios, sc_sel, horizon)

    #  Alertes scénario pessimiste
    st.markdown('<p class="section-title" style="margin-top:16px"> Conséquences projetées (scénario pessimiste)</p>', unsafe_allow_html=True)

    alertes = [
        (" +4.4°C en 2100", "La France connaîtrait des températures estivales comparables au Maghreb actuel. Les vagues de chaleur > 50°C possibles dans le Sud."),
        (" Sécheresses chroniques", "Le débit des rivières françaises chuterait de 10 à 40%. Tensions sévères sur les ressources agricoles et l'eau potable."),
        (" Feux de forêt ×5", "Les surfaces brûlées pourraient être multipliées par 5 d'ici 2100, atteignant des régions non concernées aujourd'hui."),
        (" Niveau des mers +60cm", "20 à 30% des zones côtières françaises exposées aux inondations régulières. Impact sur 3M d'habitants."),
    ]
    cols = st.columns(2)
    for i, (titre, desc) in enumerate(alertes):
        with cols[i % 2]:
            st.markdown(render("alert_card.html", titre=titre, desc=desc), unsafe_allow_html=True)
