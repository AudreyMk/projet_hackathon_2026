import plotly.graph_objects as go
import streamlit as st

from web.data import GREEN, ACCENT, apply_theme
from web.templates import render


def tab_preconisations(df_hist):
    last = df_hist.iloc[-1]
    risk = last["risk_score"]
    jours = last["jours_chauds"]

    # Profil de risque dynamique
    risk_label = " CRITIQUE" if risk > 70 else " ÉLEVÉ" if risk > 50 else " MODÉRÉ"
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
        " Faire face aux canicules": [
            ("Végétalisation urbaine", "Planter des arbres et créer des corridors verts. Objectif +30% de canopée d'ici 2030.", "−2 à −4°C en ville", "haute"),
            ("Toits et façades végétalisés", "Toitures végétalisées ou bardages isolants sur les bâtiments exposés. Éligible MaPrimeRénov'.", "−30% de chaleur intérieure", "haute"),
            ("Îlots de fraîcheur", "Cartographier les espaces frais (parcs, fontaines, bâtiments publics) et les rendre accessibles.", "Protection des populations vulnérables", "haute"),
            ("Comportements individuels", "Volets fermés le jour, hydratation fréquente, éviter les sorties 12h-16h en période de canicule.", "Réduction du risque de coup de chaleur", "moyenne"),
        ],
        " Sobriété hydrique": [
            ("Récupération d'eau de pluie", "Cuves de 500 à 10 000L. Utilisables pour l'arrosage et les sanitaires. Subventionné par certaines communes.", "−30 à −50% d'eau extérieure", "haute"),
            ("Jardinage résistant à la sécheresse", "Espèces méditerranéennes (lavande, romarin), paillage épais, arrosage en soirée.", "−70% d'arrosage nécessaire", "moyenne"),
            ("Audit de consommation d'eau", "Identifier les postes de surconsommation : robinetterie, chasse d'eau, irrigation. Économies de 20-40%.", "Réduction de la facture eau", "basse"),
        ],
        " Réduire son empreinte carbone": [
            ("Mobilité douce", "Vélo, transports en commun, covoiturage. Le transport = ~30% de l'empreinte individuelle.", "−1.5 tCO₂eq/an", "haute"),
            ("Alimentation bas carbone", "Réduire la viande rouge, favoriser local et saisonnier. L'alimentation = ~25% de l'empreinte.", "−1 tCO₂eq/an", "haute"),
            ("Rénovation énergétique", "Isolation, pompe à chaleur. MaPrimeRénov' jusqu'à 90% pour ménages modestes.", "−2 à −3 tCO₂eq/an + économies facture", "haute"),
            ("Consommation responsable", "Réparer, acheter d'occasion, allonger la durée de vie des équipements.", "−0.5 à −1 tCO₂eq/an", "moyenne"),
        ],
        " Adapter son territoire": [
            ("Plan Climat local (PCAET)", "Participer à l'élaboration du Plan Climat Air Énergie Territorial de votre commune.", "Mobilisation collective", "moyenne"),
            ("Aménagement anti-incendie", "Débroussaillage à 50-200m des habitations selon arrêté préfectoral. Obligatoire légalement.", "−60% de risque de propagation", "haute"),
            ("Infrastructure résiliente", "Anticiper la mise en conformité des réseaux eau et énergie aux événements extrêmes.", "Réduction des coûts catastrophes", "haute"),
        ],
    }

    prio_cols = {"haute": "rec-prio-haute", "moyenne": "rec-prio-moyenne", "basse": "rec-prio-basse"}
    prio_icons = {"haute": "", "moyenne": "", "basse": ""}

    for cat_name, actions in categories.items():
        with st.expander(f"**{cat_name.strip()}**", expanded=(cat_name == " Faire face aux canicules")):
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
    st.markdown('<p class="section-title" style="margin-top:20px"> Ma calculette carbone</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Estimez votre empreinte personnelle</p>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        km_voiture = st.number_input(" km en voiture/an", 0, 80000, 12000, step=1000)
        viande = st.selectbox(" Consommation viande", ["Grande (quotidienne)", "Modérée (3×/sem)", "Faible (flexitarien)", "Végétarien"])
    with c2:
        km_avion = st.number_input(" km en avion/an", 0, 100000, 3000, step=500)
        logement = st.selectbox(" Chauffage", ["Gaz naturel", "Fioul", "Pompe à chaleur", "Électrique"])
    with c3:
        isolé = st.checkbox(" Logement bien isolé")
        rénové = st.checkbox(" Rénovation énergétique récente")

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
        st.success(f" Votre empreinte ({total_em:.1f} t) est **sous la cible 2050** ({target_2050} t). Excellent !")
    elif total_em < france_moy:
        st.info(f" Votre empreinte ({total_em:.1f} t) est **inférieure à la moyenne française** ({france_moy} t). Des progrès restent possibles.")
    else:
        st.warning(f" Votre empreinte ({total_em:.1f} t) est **au-dessus de la moyenne** ({france_moy} t). Les actions ci-dessus peuvent vous aider.")
