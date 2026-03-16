import streamlit as st

from web.templates import render


def sidebar(df_hist, scenarios):
    # Initialisation session_state
    if "applied" not in st.session_state:
        st.session_state["applied"] = {
            "periode": (1950, 2024),
            "horizon": 2100,
            "sc_sel": list(scenarios.keys()),
            "territoire": "France entière",
        }

    with st.sidebar:
        st.markdown(render("sidebar_header.html"), unsafe_allow_html=True)

        st.markdown("**PÉRIODE HISTORIQUE**")
        periode_input = st.slider("Période historique", 1900, 2024, st.session_state["applied"]["periode"], label_visibility="collapsed", key="_periode")

        st.markdown("**HORIZON DE PROJECTION**")
        horizon_input = st.select_slider("Horizon de projection", options=[2030, 2040, 2050, 2060, 2075, 2100],
            value=st.session_state["applied"]["horizon"], label_visibility="collapsed", key="_horizon")

        st.markdown("**SCÉNARIOS**")
        sc_sel_input = st.multiselect("Scénarios", list(scenarios.keys()),
            default=st.session_state["applied"]["sc_sel"], label_visibility="collapsed", key="_sc_sel")

        st.markdown("**TERRITOIRE**")
        territoire_opts = ["France entière", "Île-de-France", "Provence-Alpes-Côte d'Azur", "Bretagne", "Occitanie", "Auvergne-Rhône-Alpes", "Nouvelle-Aquitaine"]
        territoire_input = st.selectbox("Territoire", territoire_opts,
            index=territoire_opts.index(st.session_state["applied"]["territoire"]),
            label_visibility="collapsed", key="_territoire")

        st.divider()

        if st.button("Appliquer les filtres", width="stretch", type="primary"):
            st.session_state["applied"] = {
                "periode": periode_input,
                "horizon": horizon_input,
                "sc_sel": sc_sel_input,
                "territoire": territoire_input,
            }

        st.markdown(render("sidebar_sources.html"), unsafe_allow_html=True)

    a = st.session_state["applied"]
    return a["periode"], a["horizon"], a["sc_sel"], a["territoire"]
