import streamlit as st

from web.templates import render


def render_hero(df_hist):
    last = df_hist.iloc[-1]
    first = df_hist[df_hist["annee"] == 1900].iloc[0]
    st.markdown(render(
        "hero.html",
        delta_temp=f"{last['temp_moy'] - first['temp_moy']:.1f}",
        co2=f"{last['co2_ppm']:.0f}",
        risk=f"{last['risk_score']:.0f}",
    ), unsafe_allow_html=True)


def render_kpis(df_hist, periode):
    df_f = df_hist[df_hist["annee"].between(*periode)]
    if df_f.empty:
        return
    last = df_f.iloc[-1]
    first_yr = df_f.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🌡️ Température actuelle", f"{last['temp_moy']:.1f}°C",
                  delta=f"+{last['temp_moy'] - first_yr['temp_moy']:.2f}°C depuis {periode[0]}")
    with col2:
        st.metric("🏭 CO₂ atmosphérique", f"{last['co2_ppm']:.0f} ppm",
                  delta=f"+{last['co2_ppm'] - first_yr['co2_ppm']:.0f} ppm")
    with col3:
        st.metric("☀️ Jours > 30°C / an", f"{last['jours_chauds']} j",
                  delta=f"+{last['jours_chauds'] - first_yr['jours_chauds']} j")
    with col4:
        st.metric("⚠️ Score risque", f"{last['risk_score']:.0f} / 100",
                  delta="Niveau critique" if last["risk_score"] > 70 else "Niveau modéré")
