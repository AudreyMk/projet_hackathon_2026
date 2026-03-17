"""
ClimaDash — Application Streamlit Hackathon #26
================================================
Lancement : streamlit run app.py

Dépendances minimales :
    pip install streamlit plotly pandas numpy scipy

100% autonome : génère les données réalistes en interne.
Compatible Streamlit Cloud pour déploiement public.
"""

import streamlit as st

from web.styles import inject_css
from web.templates import render
from web.data import build_data
from web.sidebar import sidebar
from web.components import render_hero, render_kpis
from web.tabs import (
    tab_historique,
    tab_projections,
    tab_emissions,
    tab_carte,
    tab_preconisations,
    tab_maregraphie,
)

st.set_page_config(
    page_title="ClimaDash · France 2100",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Hackathon #26 · Sup²Vinci · 16-17 Mars 2026"},
)

inject_css()


def main():
    df_hist, df_ges, df_ec, df_proj, df_reg, scenarios = build_data()

    periode, horizon, sc_sel, territoire = sidebar(df_hist, scenarios)

    render_hero(df_hist)
    render_kpis(df_hist, periode)

    tabs = st.tabs([
        "📈 Historique",
        "🔮 Projections 2100",
        "🏭 Émissions GES",
        "🗺️ Carte régionale",
        "🌱 Préconisations",
        "🌊 Marégraphie",
    ])

    with tabs[0]:
        tab_historique(df_hist, periode)
    with tabs[1]:
        tab_projections(df_hist, df_proj, scenarios, sc_sel, horizon)
    with tabs[2]:
        tab_emissions(df_ges, df_ec)
    with tabs[3]:
        tab_carte(df_reg, territoire)
    with tabs[4]:
        tab_preconisations(df_hist)
    with tabs[5]:
        tab_maregraphie()

    st.markdown(render("footer.html"), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
