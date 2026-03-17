import plotly.graph_objects as go
import streamlit as st

from web.data import GREEN, ACCENT, apply_theme, hex_alpha
from web.templates import render


def tab_emissions(df_ges, df_ec):
    col_l, col_r = st.columns([3, 2])

    with col_l:
        #  Stacked area GES
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
        #  Donut part actuelle
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

    #  Empreinte carbone individuelle
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
