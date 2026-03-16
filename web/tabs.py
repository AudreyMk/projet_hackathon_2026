import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

from web.data import GREEN, ACCENT, THEME, apply_theme, hex_alpha, is_dark_mode, fetch_tidegauges
from web.templates import render


# ══════════════════════════════════════════════
# ONGLET 1 — ANALYSE HISTORIQUE
# ══════════════════════════════════════════════
def tab_historique(df_hist, periode):
    df = df_hist[df_hist["annee"].between(*periode)].copy()
    df["roll10"] = df["temp_moy"].rolling(10, center=True, min_periods=3).mean()

    # ── Graphique 1 : Température + moyenne mobile ──
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
        fig1.add_annotation(x=2003, y=v, text="🔥 2003", showarrow=True, arrowhead=2,
                             arrowcolor="#e74c3c", font=dict(color="#e74c3c", size=11), ax=30, ay=-40)

    apply_theme(fig1, "Évolution de la température moyenne en France", 380)
    fig1.update_yaxes(title_text="°C")
    st.plotly_chart(fig1, width="stretch")

    # ── Graphique 2 : Barres anomalies + CO₂ ──
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

    # ── Graphique 3 : Double axe Temp / CO₂ ───
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

    # ── Stats décennales ───────────────────────
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


# ══════════════════════════════════════════════
# ONGLET 2 — PROJECTIONS 2100
# ══════════════════════════════════════════════
def tab_projections(df_hist, df_proj, scenarios, sc_sel, horizon=2100):
    st.markdown("""
    <p class="section-sub">Projections basées sur les scénarios GIEC AR6 (2023) ·
    Incertitude représentée à 95% · Méthode : consensus 4 modèles (ARIMA, Prophet, LSTM, XGBoost)</p>
    """, unsafe_allow_html=True)

    fig = go.Figure()

    # Historique depuis 1950
    hist_r = df_hist[df_hist["annee"] >= 1950]
    fig.add_trace(go.Scatter(
        x=hist_r["annee"], y=hist_r["temp_moy"],
        mode="lines", name="Historique",
        line=dict(color="#3d6b60", width=2),
    ))

    # Projections
    for sc_name, sc in scenarios.items():
        if sc_name not in sc_sel:
            continue
        sub = df_proj[(df_proj["scenario"] == sc_name) & (df_proj["annee"] <= horizon)]
        if sub.empty:
            continue

        # Bande d'incertitude
        fig.add_trace(go.Scatter(
            x=pd.concat([sub["annee"], sub["annee"].iloc[::-1]]),
            y=pd.concat([sub["upper"], sub["lower"].iloc[::-1]]),
            fill="toself", fillcolor=hex_alpha(sc["color"], 0.13),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
        ))
        # Ligne centrale
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

    # ── Tableau de synthèse ────────────────────
    st.markdown('<p class="section-title" style="margin-top:8px">Valeurs projetées</p>', unsafe_allow_html=True)
    rows = []
    for yr in [2030, 2050, 2075, 2100]:
        if yr > horizon:
            continue
        row = {"Année": yr}
        for sc_name in sc_sel:
            sub = df_proj[(df_proj["scenario"] == sc_name) & (df_proj["annee"] == yr)]
            if not sub.empty:
                t = sub["temp"].values[0]
                lo = sub["lower"].values[0]
                hi = sub["upper"].values[0]
                row[sc_name.split("(")[0].strip()] = f"{t:.2f}°C [{lo:.2f}–{hi:.2f}]"
        rows.append(row)

    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    # ── Alertes scénario pessimiste ────────────
    st.markdown('<p class="section-title" style="margin-top:16px">⚠️ Conséquences projetées (scénario pessimiste)</p>', unsafe_allow_html=True)

    alertes = [
        ("🌡️ +4.4°C en 2100", "La France connaîtrait des températures estivales comparables au Maghreb actuel. Les vagues de chaleur > 50°C possibles dans le Sud."),
        ("💧 Sécheresses chroniques", "Le débit des rivières françaises chuterait de 10 à 40%. Tensions sévères sur les ressources agricoles et l'eau potable."),
        ("🔥 Feux de forêt ×5", "Les surfaces brûlées pourraient être multipliées par 5 d'ici 2100, atteignant des régions non concernées aujourd'hui."),
        ("🌊 Niveau des mers +60cm", "20 à 30% des zones côtières françaises exposées aux inondations régulières. Impact sur 3M d'habitants."),
    ]
    cols = st.columns(2)
    for i, (titre, desc) in enumerate(alertes):
        with cols[i % 2]:
            st.markdown(render("alert_card.html", titre=titre, desc=desc), unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ONGLET 3 — ÉMISSIONS & EMPREINTE
# ══════════════════════════════════════════════
def tab_emissions(df_ges, df_ec):
    col_l, col_r = st.columns([3, 2])

    with col_l:
        # ── Stacked area GES ──────────────────
        pivot = df_ges.pivot_table(index="annee", columns="secteur", values="val", aggfunc="sum").fillna(0)
        sect_colors = df_ges[["secteur", "color"]].drop_duplicates().set_index("secteur")["color"].to_dict()

        fig_ges = go.Figure()
        for sect in pivot.columns:
            color = sect_colors.get(sect, GREEN)
            fig_ges.add_trace(go.Scatter(
                x=pivot.index, y=pivot[sect],
                mode="lines", name=sect,
                stackgroup="one", line=dict(color=color, width=0.5),
                fillcolor=hex_alpha(color, 0.8),
            ))

        # Objectif 2030 (-55% vs 1990)
        total_1990 = df_ges[df_ges["annee"] == 1990]["val"].sum()
        fig_ges.add_hline(
            y=total_1990 * 0.45, line_dash="dash", line_color="#f39c12",
            annotation_text=f"Objectif 2030 : −55% ({total_1990*0.45:.0f} MtCO₂eq)",
            annotation_font_color="#f39c12",
        )
        apply_theme(fig_ges, "Émissions GES France par secteur (MtCO₂eq)", 400)
        fig_ges.update_yaxes(title_text="MtCO₂eq")
        st.plotly_chart(fig_ges, width="stretch")

    with col_r:
        # ── Donut part actuelle ────────────────
        last_year = df_ges["annee"].max()
        df_last = df_ges[df_ges["annee"] == last_year]
        fig_donut = go.Figure(go.Pie(
            labels=df_last["secteur"],
            values=df_last["val"],
            hole=0.6,
            marker=dict(colors=[sect_colors.get(s, GREEN) for s in df_last["secteur"]]),
            textfont=dict(color="#d8e4e2", size=11),
        ))
        apply_theme(fig_donut, f"Répartition GES {last_year}", 400)
        fig_donut.update_traces(textposition="outside")
        st.plotly_chart(fig_donut, width="stretch")

    # ── Empreinte carbone individuelle ─────────
    st.markdown('<p class="section-title">Empreinte carbone par habitant</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Incluant les émissions importées (consommation) · Source : INSEE/SDES</p>', unsafe_allow_html=True)

    fig_ec = go.Figure()
    fig_ec.add_trace(go.Scatter(
        x=df_ec["annee"], y=df_ec["nationale"],
        name="Émissions nationales", stackgroup="one",
        line=dict(color=GREEN, width=0), fillcolor=hex_alpha(GREEN, 0.6),
    ))
    fig_ec.add_trace(go.Scatter(
        x=df_ec["annee"], y=df_ec["importee"],
        name="Émissions importées", stackgroup="one",
        line=dict(color=ACCENT, width=0), fillcolor=hex_alpha(ACCENT, 0.53),
    ))
    fig_ec.add_hline(y=2.0, line_dash="dash", line_color="#f39c12",
                     annotation_text="Cible 2050 : 2 tCO₂eq", annotation_font_color="#f39c12")
    apply_theme(fig_ec, "Empreinte carbone par habitant (tCO₂eq/an)", 350)
    fig_ec.update_yaxes(title_text="tCO₂eq/habitant")
    st.plotly_chart(fig_ec, width="stretch")

    # Indicateur de progrès
    current = df_ec["totale"].iloc[-1]
    target = 2.0
    progress_pct = min(100, (12.6 - current) / (12.6 - target) * 100)
    st.markdown(render(
        "progress_bar.html",
        progress_pct=f"{progress_pct:.0f}",
        green=GREEN, accent=ACCENT,
        current=f"{current:.1f}",
        target=target,
    ), unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ONGLET 4 — CARTE RÉGIONALE
# ══════════════════════════════════════════════
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


# ══════════════════════════════════════════════
# ONGLET 5 — PRÉCONISATIONS CITOYENNES
# ══════════════════════════════════════════════
def tab_preconisations(df_hist):
    last = df_hist.iloc[-1]
    risk = last["risk_score"]
    jours = last["jours_chauds"]

    # Profil de risque dynamique
    risk_label = "🔴 CRITIQUE" if risk > 70 else "🟠 ÉLEVÉ" if risk > 50 else "🟡 MODÉRÉ"
    bar_color = "#e74c3c" if risk > 70 else "#f39c12" if risk > 50 else GREEN
    st.markdown(render(
        "risk_profile.html",
        risk=f"{risk:.0f}",
        risk_label=risk_label,
        bar_color=bar_color,
        jours=jours,
    ), unsafe_allow_html=True)

    # Préconisations structurées
    categories = {
        "☀️ Faire face aux canicules": [
            ("Végétalisation urbaine", "Planter des arbres et créer des corridors verts. Objectif +30% de canopée d'ici 2030.", "−2 à −4°C en ville", "haute"),
            ("Toits et façades végétalisés", "Toitures végétalisées ou bardages isolants sur les bâtiments exposés. Éligible MaPrimeRénov'.", "−30% de chaleur intérieure", "haute"),
            ("Îlots de fraîcheur", "Cartographier les espaces frais (parcs, fontaines, bâtiments publics) et les rendre accessibles.", "Protection des populations vulnérables", "haute"),
            ("Comportements individuels", "Volets fermés le jour, hydratation fréquente, éviter les sorties 12h-16h en période de canicule.", "Réduction du risque de coup de chaleur", "moyenne"),
        ],
        "💧 Sobriété hydrique": [
            ("Récupération d'eau de pluie", "Cuves de 500 à 10 000L. Utilisables pour l'arrosage et les sanitaires. Subventionné par certaines communes.", "−30 à −50% d'eau extérieure", "haute"),
            ("Jardinage résistant à la sécheresse", "Espèces méditerranéennes (lavande, romarin), paillage épais, arrosage en soirée.", "−70% d'arrosage nécessaire", "moyenne"),
            ("Audit de consommation d'eau", "Identifier les postes de surconsommation : robinetterie, chasse d'eau, irrigation. Économies de 20-40%.", "Réduction de la facture eau", "basse"),
        ],
        "♻️ Réduire son empreinte carbone": [
            ("Mobilité douce", "Vélo, transports en commun, covoiturage. Le transport = ~30% de l'empreinte individuelle.", "−1.5 tCO₂eq/an", "haute"),
            ("Alimentation bas carbone", "Réduire la viande rouge, favoriser local et saisonnier. L'alimentation = ~25% de l'empreinte.", "−1 tCO₂eq/an", "haute"),
            ("Rénovation énergétique", "Isolation, pompe à chaleur. MaPrimeRénov' jusqu'à 90% pour ménages modestes.", "−2 à −3 tCO₂eq/an + économies facture", "haute"),
            ("Consommation responsable", "Réparer, acheter d'occasion, allonger la durée de vie des équipements.", "−0.5 à −1 tCO₂eq/an", "moyenne"),
        ],
        "🏙️ Adapter son territoire": [
            ("Plan Climat local (PCAET)", "Participer à l'élaboration du Plan Climat Air Énergie Territorial de votre commune.", "Mobilisation collective", "moyenne"),
            ("Aménagement anti-incendie", "Débroussaillage à 50-200m des habitations selon arrêté préfectoral. Obligatoire légalement.", "−60% de risque de propagation", "haute"),
            ("Infrastructure résiliente", "Anticiper la mise en conformité des réseaux eau et énergie aux événements extrêmes.", "Réduction des coûts catastrophes", "haute"),
        ],
    }

    prio_cols = {"haute": "rec-prio-haute", "moyenne": "rec-prio-moyenne", "basse": "rec-prio-basse"}
    prio_icons = {"haute": "🔴", "moyenne": "🟠", "basse": "🟢"}

    for cat_name, actions in categories.items():
        with st.expander(f"**{cat_name}**", expanded=(cat_name == "☀️ Faire face aux canicules")):
            cols = st.columns(2)
            for i, (titre, desc, impact, prio) in enumerate(actions):
                with cols[i % 2]:
                    st.markdown(render(
                        "rec_card.html",
                        prio_class=prio_cols[prio],
                        icon=prio_icons[prio],
                        titre=titre, desc=desc, impact=impact,
                    ), unsafe_allow_html=True)

    # Calculette carbone interactive
    st.markdown('<p class="section-title" style="margin-top:20px">🧮 Ma calculette carbone</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Estimez votre empreinte personnelle</p>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        km_voiture = st.number_input("🚗 km en voiture/an", 0, 80000, 12000, step=1000)
        viande = st.selectbox("🥩 Consommation viande", ["Grande (quotidienne)", "Modérée (3×/sem)", "Faible (flexitarien)", "Végétarien"])
    with c2:
        km_avion = st.number_input("✈️ km en avion/an", 0, 100000, 3000, step=500)
        logement = st.selectbox("🏠 Chauffage", ["Gaz naturel", "Fioul", "Pompe à chaleur", "Électrique"])
    with c3:
        isolé = st.checkbox("🏗️ Logement bien isolé")
        rénové = st.checkbox("🔧 Rénovation énergétique récente")

    # Calcul simplifié
    em_voiture = km_voiture * 0.21 / 1000
    em_avion = km_avion * 0.255 / 1000
    em_viande = {"Grande (quotidienne)": 2.5, "Modérée (3×/sem)": 1.8, "Faible (flexitarien)": 1.2, "Végétarien": 0.7}[viande]
    em_logement = {"Gaz naturel": 2.0, "Fioul": 2.8, "Pompe à chaleur": 0.6, "Électrique": 0.9}[logement]
    if isolé: em_logement *= 0.75
    if rénové: em_logement *= 0.80
    total_em = em_voiture + em_avion + em_viande + em_logement + 2.5  # reste (achats, services...)

    target_2050 = 2.0
    france_moy = 9.9

    fig_calc = go.Figure()
    fig_calc.add_trace(go.Bar(
        x=["Voiture", "Avion", "Alimentation", "Logement", "Autres"],
        y=[em_voiture, em_avion, em_viande, em_logement, 2.5],
        marker_color=[GREEN, "#e74c3c", "#f39c12", ACCENT, "#9b59b6"],
        text=[f"{v:.1f}" for v in [em_voiture, em_avion, em_viande, em_logement, 2.5]],
        textposition="outside", textfont=dict(color="#d8e4e2"),
    ))
    fig_calc.add_hline(y=france_moy, line_dash="dot", line_color="#f39c12",
                       annotation_text=f"Moyenne France ({france_moy} t)", annotation_font_color="#f39c12")
    fig_calc.add_hline(y=target_2050, line_dash="dash", line_color=GREEN,
                       annotation_text=f"Cible 2050 ({target_2050} t)", annotation_font_color=GREEN)
    apply_theme(fig_calc, f"Votre empreinte estimée : {total_em:.1f} tCO₂eq/an", 350)
    fig_calc.update_yaxes(title_text="tCO₂eq/an")
    st.plotly_chart(fig_calc, width="stretch")

    if total_em < target_2050:
        st.success(f"🌟 Votre empreinte ({total_em:.1f} t) est **sous la cible 2050** ({target_2050} t). Excellent !")
    elif total_em < france_moy:
        st.info(f"🟡 Votre empreinte ({total_em:.1f} t) est **inférieure à la moyenne française** ({france_moy} t). Des progrès restent possibles.")
    else:
        st.warning(f"🔴 Votre empreinte ({total_em:.1f} t) est **au-dessus de la moyenne** ({france_moy} t). Les actions ci-dessus peuvent vous aider.")


# ══════════════════════════════════════════════
# ONGLET 6 — MARÉGRAPHIE (SHOM)
# ══════════════════════════════════════════════
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

    # ── Filtres ────────────────────────────────
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

    # ── KPIs ───────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total stations", len(df_f))
    k2.metric("En service (OK)", int((df_f["state"] == "OK").sum()))
    k3.metric("Hors service / PB", int(df_f["state"].isin(["KO", "PB"]).sum()))
    k4.metric("Réseau RONIM", int((df_f["reseau"] == "RONIM").sum()))

    # ── Carte ──────────────────────────────────
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

    # ── Répartition par état (barres) ──────────
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
