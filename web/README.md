# 🌍 ClimaDash — Application Streamlit

## Lancement en 3 commandes

```bash
# 1. Installer les dépendances (30 secondes)
pip install -r requirements.txt

# 2. Lancer l'application
streamlit run app.py

# 3. Ouvrir dans le navigateur
# → http://localhost:8501
```

## Contenu de l'application

| Onglet | Contenu |
|--------|---------|
| 📈 Historique | Températures 1900-2024, anomalies, CO₂, corrélations |
| 🔮 Projections | Scénarios GIEC 2030/2050/2100 avec intervalles de confiance |
| 🏭 Émissions | GES par secteur, empreinte carbone individuelle |
| 🗺️ Carte | Choroplèthe des anomalies et risques par région française (GeoJSON officiel) |
| 🌱 Préconisations | Actions citoyennes + calculette carbone interactive |
| 🌊 Marégraphie | Carte temps réel des 175 marégraphes SHOM (RONIM/REFMAR) |

## Déploiement sur Streamlit Cloud (gratuit)

1. Créer un dépôt GitHub avec `app.py` + `requirements.txt`
2. Aller sur [share.streamlit.io](https://share.streamlit.io)
3. Connecter le dépôt → **Deploy**

URL publique générée automatiquement — parfait pour le pitch !

## Structure du module web/

```
web/
├── __init__.py
├── data.py          # Génération des données synthétiques + fetch_tidegauges()
├── styles.py        # CSS injecté (dark/light via CSS variables)
├── templates.py     # Moteur de rendu HTML ({{variable}})
├── sidebar.py       # Filtres + session_state + bouton Appliquer
├── components.py    # Hero banner + KPIs
├── tabs.py          # 6 onglets (tab_historique … tab_maregraphie)
└── templates/
    ├── hero.html
    ├── alert_card.html
    ├── rec_card.html
    ├── progress_bar.html
    ├── risk_profile.html
    ├── sidebar_header.html
    ├── sidebar_sources.html
    └── footer.html
```

## Sources des données

| Source | Données | Type |
|--------|---------|------|
| Météo France | Températures historiques France (1900-2024) | Simulé |
| NOAA | CO₂ atmosphérique (Mauna Loa) | Simulé |
| CITEPA Secten | Émissions GES France par secteur | Simulé |
| GIEC AR6 2023 | Scénarios SSP1-2.6 / SSP2-4.5 / SSP5-8.5 | Simulé |
| INSEE/SDES | Empreinte carbone individuelle | Simulé |
| **SHOM** | **Marégraphes RONIM/REFMAR (175 stations)** | **Temps réel via API** |
| gregoiredavid/france-geojson | Contours des 13 régions métropolitaines | GeoJSON statique |
