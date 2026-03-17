import streamlit as st

_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">

<style>
/* 
   Variables — dark (défaut)
    */
:root {
    --cd-green:        #0e7c61;
    --cd-green-light:  #13a37f;
    --cd-accent:       #4ecdc4;

    --cd-bg:           #080c0e;
    --cd-bg-card:      #0d1417;
    --cd-bg-hover:     #111c1a;
    --cd-border:       #1a2e28;
    --cd-border-hover: #2a5248;
    --cd-text:         #d8e4e2;
    --cd-text-muted:   #5a8a80;
    --cd-text-faint:   #3d6b60;

    --cd-alert-bg:     #160d0d;
    --cd-alert-border: #7b2d2d;
    --cd-alert-text:   #c09090;

    --cd-hero-grad:    linear-gradient(135deg, #080c0e 0%, #0a1f18 50%, #080c0e 100%);
    --cd-hero-glow:    rgba(14,124,97,0.15);
    --cd-slider-bg:    #0e7c61;

    --cd-radius:       12px;
    --cd-shadow:       0 4px 24px rgba(0,0,0,0.4);
    --cd-transition:   0.18s ease;
}

/* 
   Variables — light
    */
@media (prefers-color-scheme: light) {
    :root {
        --cd-bg:           #f4faf8;
        --cd-bg-card:      #ffffff;
        --cd-bg-hover:     #eaf5f0;
        --cd-border:       #b8d8cf;
        --cd-border-hover: #7ab8a8;
        --cd-text:         #0d2820;
        --cd-text-muted:   #2d7a65;
        --cd-text-faint:   #5a9e8a;

        --cd-alert-bg:     #fff4f4;
        --cd-alert-border: #e8a0a0;
        --cd-alert-text:   #8a3a3a;

        --cd-hero-grad:    linear-gradient(135deg, #eaf7f3 0%, #d0ece6 50%, #eaf7f3 100%);
        --cd-hero-glow:    rgba(14,124,97,0.12);
        --cd-slider-bg:    #0e7c61;
        --cd-shadow:       0 4px 24px rgba(0,0,0,0.08);
    }
}

/* 
   Masquer éléments Streamlit parasites
    */
#MainMenu, footer[class*="css"], header[class*="css"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.viewerBadge_container__1QSob { display: none !important; }
button[title="View fullscreen"] { display: none !important; }

/* 
   Scrollbar personnalisée
    */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--cd-bg); }
::-webkit-scrollbar-thumb { background: var(--cd-border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--cd-green); }

/* 
   Base
    */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--cd-bg);
    color: var(--cd-text);
}
.stApp {
    background: var(--cd-bg);
    animation: fadeIn 0.35s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

/* 
   Sidebar
    */
[data-testid="stSidebar"] {
    background: var(--cd-bg-card);
    border-right: 1px solid var(--cd-border);
}
[data-testid="stSidebar"] * { color: var(--cd-text-muted) !important; }
[data-testid="stSidebar"] .stSlider > div > div > div {
    background: var(--cd-slider-bg) !important;
}
[data-testid="stSidebar"] hr {
    border-color: var(--cd-border) !important;
    margin: 12px 0 !important;
}
/* Section labels dans la sidebar */
[data-testid="stSidebar"] .sidebar-section-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--cd-text-faint) !important;
    margin: 14px 0 6px 0;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* 
   Bouton primaire — override Streamlit
    */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #4d6b63 0%, #5c7d74 100%) !important;
    border: none !important;
    color: #e8eeec !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.5px !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    transition: all var(--cd-transition) !important;
    box-shadow: 0 2px 8px rgba(30,60,50,0.25) !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(30,60,50,0.38) !important;
}
.stButton > button[kind="primary"]:active,
.stButton > button[data-testid="baseButton-primary"]:active {
    transform: translateY(0) !important;
}

/* Bouton secondaire */
.stButton > button:not([kind="primary"]) {
    background: transparent !important;
    border: 1px solid var(--cd-border) !important;
    color: var(--cd-text-muted) !important;
    border-radius: 8px !important;
    transition: all var(--cd-transition) !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--cd-green) !important;
    color: var(--cd-green) !important;
}

/* 
   Hero
    */
.hero-wrap {
    background: var(--cd-hero-grad);
    border: 1px solid var(--cd-border);
    border-radius: 20px;
    padding: 40px 48px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    box-shadow: var(--cd-shadow);
}
.hero-wrap::before {
    content: '';
    position: absolute; top: -80px; right: -80px;
    width: 360px; height: 360px;
    background: radial-gradient(circle, var(--cd-hero-glow) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
}
.hero-wrap::after {
    content: '';
    position: absolute; bottom: -40px; left: 20%;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(78,205,196,0.06) 0%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem; font-weight: 800;
    color: var(--cd-text); line-height: 1.1;
    margin: 0 0 8px 0;
    letter-spacing: -1px;
}
.hero-title span { color: var(--cd-green); }
.hero-sub {
    color: var(--cd-text-muted); font-size: 1rem; font-weight: 300;
    margin: 0 0 20px 0; letter-spacing: 0.5px;
}
.hero-stats {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 20px;
}
.hero-stat {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(14,124,97,0.08);
    border: 1px solid rgba(14,124,97,0.22);
    border-radius: 10px;
    padding: 10px 16px;
    min-width: 140px;
    transition: all var(--cd-transition);
}
.hero-stat:hover {
    background: rgba(14,124,97,0.15);
    border-color: var(--cd-green);
    transform: translateY(-1px);
}
.hero-stat-icon { font-size: 1.3rem; line-height: 1; }
.hero-stat-body {}
.hero-stat-val {
    font-family: 'Syne', sans-serif;
    font-size: 1.25rem; font-weight: 800;
    color: var(--cd-text); line-height: 1;
}
.hero-stat-label {
    font-size: 0.68rem; color: var(--cd-text-faint);
    text-transform: uppercase; letter-spacing: 1px;
    margin-top: 2px;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(231,76,60,0.1);
    border: 1px solid rgba(231,76,60,0.35);
    color: #e74c3c; font-size: 0.73rem; font-weight: 600;
    padding: 5px 12px; border-radius: 20px;
    margin-top: 18px; letter-spacing: 0.5px;
    animation: pulse 3s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(231,76,60,0.3); }
    50% { box-shadow: 0 0 0 5px rgba(231,76,60,0); }
}
.hero-badge-dot {
    width: 6px; height: 6px;
    background: #e74c3c;
    border-radius: 50%;
    animation: blink 1.2s ease-in-out infinite;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }

/* 
   KPI Cards
    */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
.kpi-card {
    background: var(--cd-bg-card);
    border: 1px solid var(--cd-border);
    border-radius: var(--cd-radius);
    padding: 20px 24px;
    position: relative; overflow: hidden;
    transition: all var(--cd-transition);
    box-shadow: var(--cd-shadow);
}
.kpi-card:hover {
    border-color: var(--cd-border-hover);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.kpi-card::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
    background: var(--accent, var(--cd-green));
    border-radius: 0 0 2px 2px;
}
.kpi-label { font-size: 0.7rem; color: var(--cd-text-faint); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
.kpi-value { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; color: var(--cd-text); line-height: 1; }
.kpi-delta { font-size: 0.8rem; margin-top: 6px; }
.kpi-up { color: #e74c3c; } .kpi-down { color: var(--cd-green); } .kpi-neutral { color: #f39c12; }

/* 
   Section titles
    */
.section-title {
    font-family: 'Syne', sans-serif; font-size: 1.35rem; font-weight: 700;
    color: var(--cd-text); margin: 0 0 4px 0;
}
.section-sub { font-size: 0.85rem; color: var(--cd-text-muted); margin-bottom: 18px; line-height: 1.5; }

/* 
   Alert card
    */
.alert-card {
    background: var(--cd-alert-bg);
    border: 1px solid var(--cd-alert-border);
    border-left: 4px solid #e74c3c;
    border-radius: 10px; padding: 16px 20px;
    margin-bottom: 14px;
    transition: all var(--cd-transition);
}
.alert-card:hover { border-left-width: 5px; transform: translateX(2px); }
.alert-card h4 { color: #e74c3c; margin: 0 0 6px 0; font-size: 0.9rem; font-weight: 600; }
.alert-card p  { color: var(--cd-alert-text); margin: 0; font-size: 0.82rem; line-height: 1.5; }

/* 
   Rec cards
    */
.rec-card {
    background: var(--cd-bg-card);
    border: 1px solid var(--cd-border);
    border-radius: 10px; padding: 16px 18px;
    margin-bottom: 12px;
    transition: all var(--cd-transition);
}
.rec-card:hover {
    border-color: var(--cd-border-hover);
    background: var(--cd-bg-hover);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}
.rec-card h4 { color: var(--cd-text); font-size: 0.92rem; margin: 0 0 5px 0; font-weight: 600; }
.rec-card p  { color: var(--cd-text-muted); font-size: 0.82rem; margin: 0 0 8px 0; line-height: 1.5; }
.rec-impact  { font-size: 0.75rem; color: var(--cd-green); font-weight: 600;
               background: rgba(14,124,97,0.1); border-radius: 4px; padding: 2px 8px;
               display: inline-block; }
.rec-prio-haute   { border-left: 3px solid #e74c3c; }
.rec-prio-moyenne { border-left: 3px solid #f39c12; }
.rec-prio-basse   { border-left: 3px solid var(--cd-green); }

/* 
   Streamlit overrides — Tabs
    */
.stTabs [data-baseweb="tab-list"] {
    background: var(--cd-bg-card);
    border: 1px solid var(--cd-border);
    border-radius: 12px; padding: 5px; gap: 3px;
    margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    color: var(--cd-text-muted) !important;
    border-radius: 8px !important; padding: 9px 18px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.87rem !important; font-weight: 500 !important;
    transition: all var(--cd-transition) !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
    background: var(--cd-bg-hover) !important;
    color: var(--cd-text) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--cd-green) !important;
    color: #fff !important;
    box-shadow: 0 2px 10px rgba(14,124,97,0.35) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 4px !important;
}

/* 
   Streamlit overrides — Metrics
    */
div[data-testid="stMetric"] {
    background: var(--cd-bg-card);
    border-radius: var(--cd-radius);
    padding: 16px 20px;
    border: 1px solid var(--cd-border);
    transition: all var(--cd-transition);
}
div[data-testid="stMetric"]:hover {
    border-color: var(--cd-border-hover);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}
div[data-testid="stMetric"] label {
    color: var(--cd-text-muted) !important; font-size: 0.75rem !important;
    text-transform: uppercase; letter-spacing: 1px; font-weight: 500 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--cd-text) !important;
    font-family: 'Syne', sans-serif !important; font-size: 1.65rem !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
}

/* 
   Streamlit overrides — Inputs
    */
.stSelectbox label, .stSlider label, .stMultiSelect label,
.stNumberInput label, .stCheckbox label {
    color: var(--cd-text-muted) !important; font-size: 0.8rem !important;
    text-transform: uppercase; letter-spacing: 1px; font-weight: 500 !important;
}
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: var(--cd-bg-card) !important;
    border-color: var(--cd-border) !important;
    border-radius: 8px !important;
    transition: border-color var(--cd-transition) !important;
}
.stSelectbox > div > div:hover,
.stMultiSelect > div > div:hover {
    border-color: var(--cd-green) !important;
}
.stNumberInput > div > div {
    background: var(--cd-bg-card) !important;
    border-radius: 8px !important;
}

/* 
   Streamlit overrides — Expanders
    */
[data-testid="stExpander"] {
    border: 1px solid var(--cd-border) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    margin-bottom: 10px !important;
    transition: border-color var(--cd-transition) !important;
}
[data-testid="stExpander"]:hover {
    border-color: var(--cd-border-hover) !important;
}
[data-testid="stExpander"] summary {
    background: var(--cd-bg-card) !important;
    padding: 14px 18px !important;
    font-weight: 600 !important;
}
[data-testid="stExpander"] summary:hover {
    background: var(--cd-bg-hover) !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: var(--cd-bg) !important;
    padding: 16px !important;
}

/* 
   Streamlit overrides — Dataframes
    */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid var(--cd-border) !important;
}

/* 
   Streamlit overrides — Divider
    */
hr[data-testid="stDivider"] {
    border-color: var(--cd-border) !important;
    margin: 10px 0 !important;
}

/* 
   Streamlit overrides — Alerts (success/info/warning)
    */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-width: 1px !important;
}

/*  Plotly  */
.js-plotly-plot { border-radius: 12px; overflow: hidden; }
.modebar { opacity: 0.4 !important; transition: opacity 0.2s !important; }
.modebar:hover { opacity: 1 !important; }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)
