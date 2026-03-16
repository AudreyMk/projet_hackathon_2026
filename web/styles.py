import streamlit as st

_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">

<style>
/* ══════════════════════════════════════════════
   Variables — dark (défaut)
   ══════════════════════════════════════════════ */
:root {
    --cd-green:        #0e7c61;
    --cd-accent:       #4ecdc4;

    --cd-bg:           #080c0e;
    --cd-bg-card:      #0d1417;
    --cd-border:       #1a2e28;
    --cd-text:         #d8e4e2;
    --cd-text-muted:   #5a8a80;
    --cd-text-faint:   #3d6b60;

    --cd-alert-bg:     #160d0d;
    --cd-alert-border: #7b2d2d;
    --cd-alert-text:   #c09090;

    --cd-hero-grad:    linear-gradient(135deg, #080c0e 0%, #0a1f18 50%, #080c0e 100%);
    --cd-hero-glow:    rgba(14,124,97,0.15);
    --cd-slider-bg:    #0e7c61;
}

/* ══════════════════════════════════════════════
   Variables — light
   ══════════════════════════════════════════════ */
@media (prefers-color-scheme: light) {
    :root {
        --cd-bg:           #f4faf8;
        --cd-bg-card:      #ffffff;
        --cd-border:       #b8d8cf;
        --cd-text:         #0d2820;
        --cd-text-muted:   #2d7a65;
        --cd-text-faint:   #5a9e8a;

        --cd-alert-bg:     #fff4f4;
        --cd-alert-border: #e8a0a0;
        --cd-alert-text:   #8a3a3a;

        --cd-hero-grad:    linear-gradient(135deg, #eaf7f3 0%, #d0ece6 50%, #eaf7f3 100%);
        --cd-hero-glow:    rgba(14,124,97,0.12);
        --cd-slider-bg:    #0e7c61;
    }
}

/* ══════════════════════════════════════════════
   Base
   ══════════════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--cd-bg);
    color: var(--cd-text);
}
.stApp { background: var(--cd-bg); }

/* ══════════════════════════════════════════════
   Sidebar
   ══════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: var(--cd-bg-card);
    border-right: 1px solid var(--cd-border);
}
[data-testid="stSidebar"] * { color: var(--cd-text-muted) !important; }
[data-testid="stSidebar"] .stSlider > div > div > div {
    background: var(--cd-slider-bg) !important;
}

/* ══════════════════════════════════════════════
   Hero
   ══════════════════════════════════════════════ */
.hero-wrap {
    background: var(--cd-hero-grad);
    border: 1px solid var(--cd-border);
    border-radius: 16px;
    padding: 36px 44px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.hero-wrap::before {
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, var(--cd-hero-glow) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3rem; font-weight: 800;
    color: var(--cd-text); line-height: 1.1;
    margin: 0 0 8px 0;
    letter-spacing: -1px;
}
.hero-title span { color: var(--cd-green); }
.hero-sub {
    color: var(--cd-text-muted); font-size: 1rem; font-weight: 300;
    margin: 0; letter-spacing: 0.5px;
}
.hero-badge {
    display: inline-block;
    background: rgba(14,124,97,0.12);
    border: 1px solid var(--cd-green);
    color: var(--cd-green); font-size: 0.75rem; font-weight: 500;
    padding: 4px 12px; border-radius: 20px;
    margin-top: 16px; letter-spacing: 1px; text-transform: uppercase;
}

/* ══════════════════════════════════════════════
   KPI Cards
   ══════════════════════════════════════════════ */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
.kpi-card {
    background: var(--cd-bg-card);
    border: 1px solid var(--cd-border);
    border-radius: 12px;
    padding: 20px 24px;
    position: relative; overflow: hidden;
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: var(--cd-green); }
.kpi-card::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
    background: var(--accent, var(--cd-green));
}
.kpi-label { font-size: 0.72rem; color: var(--cd-text-faint); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
.kpi-value { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; color: var(--cd-text); line-height: 1; }
.kpi-delta { font-size: 0.8rem; margin-top: 6px; }
.kpi-up { color: #e74c3c; } .kpi-down { color: var(--cd-green); } .kpi-neutral { color: #f39c12; }

/* ══════════════════════════════════════════════
   Section titles
   ══════════════════════════════════════════════ */
.section-title {
    font-family: 'Syne', sans-serif; font-size: 1.4rem; font-weight: 700;
    color: var(--cd-text); margin: 0 0 4px 0;
}
.section-sub { font-size: 0.85rem; color: var(--cd-text-muted); margin-bottom: 20px; }

/* ══════════════════════════════════════════════
   Alert card
   ══════════════════════════════════════════════ */
.alert-card {
    background: var(--cd-alert-bg);
    border: 1px solid var(--cd-alert-border);
    border-left: 4px solid #e74c3c;
    border-radius: 8px; padding: 14px 18px;
    margin-bottom: 16px;
}
.alert-card h4 { color: #e74c3c; margin: 0 0 4px 0; font-size: 0.9rem; }
.alert-card p  { color: var(--cd-alert-text); margin: 0; font-size: 0.82rem; }

/* ══════════════════════════════════════════════
   Rec cards
   ══════════════════════════════════════════════ */
.rec-card {
    background: var(--cd-bg-card);
    border: 1px solid var(--cd-border);
    border-radius: 10px; padding: 16px 18px;
    margin-bottom: 12px;
}
.rec-card h4 { color: var(--cd-text); font-size: 0.92rem; margin: 0 0 4px 0; }
.rec-card p  { color: var(--cd-text-muted); font-size: 0.82rem; margin: 0 0 6px 0; }
.rec-impact  { font-size: 0.75rem; color: var(--cd-green); font-weight: 500; }
.rec-prio-haute   { border-left: 3px solid #e74c3c; }
.rec-prio-moyenne { border-left: 3px solid #f39c12; }
.rec-prio-basse   { border-left: 3px solid var(--cd-green); }

/* ══════════════════════════════════════════════
   Streamlit overrides
   ══════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: var(--cd-bg-card); border-radius: 10px; padding: 4px; gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: var(--cd-text-muted) !important; border-radius: 7px; padding: 8px 20px;
    font-family: 'DM Sans', sans-serif;
}
.stTabs [aria-selected="true"] {
    background: var(--cd-green) !important; color: #fff !important;
}
div[data-testid="stMetric"] {
    background: var(--cd-bg-card); border-radius: 10px;
    padding: 14px 18px; border: 1px solid var(--cd-border);
}
div[data-testid="stMetric"] label {
    color: var(--cd-text-muted) !important; font-size: 0.78rem !important;
    text-transform: uppercase; letter-spacing: 1px;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--cd-text) !important;
    font-family: 'Syne', sans-serif !important; font-size: 1.7rem !important;
}
.stSelectbox label, .stSlider label, .stMultiSelect label {
    color: var(--cd-text-muted) !important; font-size: 0.8rem !important;
    text-transform: uppercase; letter-spacing: 1px;
}

/* ── Plotly ── */
.js-plotly-plot { border-radius: 10px; overflow: hidden; }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)
