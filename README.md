# 🌍 Hackathon #26 — Changement Climatique
## Analyse, Visualisation et Prédiction Climatique Multi-Échelle & Sensibilisation Citoyenne

> **Sup²Vinci · 16 & 17 Mars 2026** · Mastère Big Data & IA

---

## 🗂️ Structure du projet

```
hackathon26_climat/
├── app.py                    # Point d'entrée Streamlit
├── config/
│   └── settings.py           # Paramètres globaux (territoire, années, sources)
├── data/
│   ├── raw/                  # Données brutes téléchargées
│   ├── processed/
│   │   └── france_regions.geojson  # Contours 13 régions (gregoiredavid)
│   └── external/             # Shapefiles, référentiels géographiques
├── web/                      # Module dashboard Streamlit
│   ├── __init__.py
│   ├── data.py               # Données synthétiques + fetch_tidegauges() SHOM
│   ├── styles.py             # CSS dark/light (CSS custom properties)
│   ├── templates.py          # Moteur de rendu HTML {{variable}}
│   ├── sidebar.py            # Filtres + session_state
│   ├── components.py         # Hero banner + KPIs
│   ├── tabs.py               # 6 onglets
│   └── templates/            # Fragments HTML (hero, cartes, footer…)
├── src/
│   ├── ingestion/
│   │   ├── pipeline.py       # Orchestrateur principal du pipeline
│   │   ├── meteo_france.py   # API Météo France / meteo.data.gouv.fr
│   │   ├── citepa_secten.py  # Émissions GES (Secten – CITEPA)
│   │   └── noaa_co2.py       # Concentrations CO₂/CH₄ (NOAA)
│   ├── processing/
│   │   ├── cleaner.py        # Nettoyage & valeurs manquantes
│   │   ├── transformer.py    # Agrégations & feature engineering
│   │   └── features.py       # Indicateurs climatiques calculés
│   ├── models/
│   │   ├── base_model.py     # Classe abstraite commune
│   │   ├── arima_model.py    # ARIMA / SARIMA
│   │   ├── prophet_model.py  # Facebook Prophet
│   │   ├── lstm_model.py     # LSTM / GRU (TensorFlow/Keras)
│   │   ├── gradient_boosting.py  # XGBoost / LightGBM
│   │   └── model_comparison.py   # Benchmark RMSE / MAE / MAPE
│   └── recommendations/
│       └── citizen_actions.py  # Moteur de préconisations citoyennes
├── notebooks/
│   ├── 01_exploration_EDA.ipynb
│   └── 02_modelisation_predictions.ipynb
├── tests/
│   └── test_pipeline.py
├── requirements.txt
├── Makefile
├── .env.example
└── README.md
```

---

## ⚡ Lancement rapide

### 🍎 macOS / Linux

```bash
# 1. Cloner le dépôt
git clone <repo>
cd hackathon26_climat

# 2. Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le dashboard (100% autonome, aucune clé API requise)
streamlit run app.py
# → http://localhost:8501

# 5. (Optionnel) Pipeline complet ingestion → processing → modèles
cp .env.example .env   # Ajouter les clés API si nécessaire
make all

# 6. (Optionnel) MLflow UI
make mlflow
```

### 🪟 Windows (PowerShell)

```powershell
# 1. Cloner le dépôt
git clone <repo>
cd hackathon26_climat

# 2. Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\Activate.ps1

# Si l'activation est bloquée par la politique d'exécution :
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le dashboard (100% autonome, aucune clé API requise)
streamlit run app.py
# → http://localhost:8501

# 5. (Optionnel) Variables d'environnement
copy .env.example .env   # Puis éditer .env avec vos clés API

# 6. (Optionnel) MLflow UI (nécessite make — installer via choco ou scoop)
make mlflow
# Ou sans make :
mlflow ui --backend-store-uri ./mlflow_runs
```

### 🪟 Windows (Invite de commandes — CMD)

```cmd
:: 1. Cloner le dépôt
git clone <repo>
cd hackathon26_climat

:: 2. Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\activate.bat

:: 3. Installer les dépendances
pip install -r requirements.txt

:: 4. Lancer le dashboard
streamlit run app.py
```

---

## 📋 Prérequis

| Outil | Version minimale | Vérification |
|-------|-----------------|--------------|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Git | 2.x | `git --version` |
| (Optionnel) make | — | macOS : `xcode-select --install` · Windows : [chocolatey](https://chocolatey.org/) `choco install make` |

> **Note Windows** : si `python` n'est pas reconnu, essayer `py` à la place. Vérifier que Python est bien ajouté au PATH lors de l'installation.

---

## 🎯 Territoire d'étude
Configurable dans `config/settings.py` : France entière / Région / Commune.

## 🖥️ Dashboard — Onglets

| Onglet | Contenu |
|--------|---------|
| 📈 Historique | Températures 1900-2024, anomalies, CO₂, corrélations décennales |
| 🔮 Projections 2100 | Scénarios GIEC SSP1/2/5 avec bandes d'incertitude à 95% + choix du modèle |
| 🏭 Émissions GES | Émissions par secteur, empreinte carbone individuelle |
| 🗺️ Carte régionale | Choroplèthe risque/anomalie par région (GeoJSON officiel) |
| 🌱 Préconisations | Actions citoyennes classées + calculette carbone interactive |
| 🌊 Marégraphie | 175 marégraphes SHOM temps réel (API RONIM/REFMAR) |

## 📊 Indicateurs couverts (≥ 8 requis)
| # | Indicateur | Source | Catégorie |
|---|-----------|--------|-----------|
| 1 | Température moyenne annuelle | Météo France | Évolution |
| 2 | Jours > 30°C / jours de gel | Météo France | Évolution |
| 3 | Précipitations annuelles | Météo France | Évolution |
| 4 | Concentrations CO₂ (ppm) | NOAA | Pression humaine |
| 5 | Émissions GES par secteur | CITEPA Secten | Pression humaine |
| 6 | Empreinte carbone individuelle | INSEE/SDES | Pression humaine |
| 7 | Réseau de marégraphes côtiers | **SHOM (API temps réel)** | Évolution |
| 8 | Coût économique des catastrophes | CCR | Impact visible |
| 9 | Niveau des mers | PSMSL | Évolution |
| 10| Risque climatique régional | Composite (anomalie + CO₂ + chaleur) | Impact visible |

## 🤖 Modèles IA
- **ARIMA/SARIMA** — Baseline statistique, conservateur, fort sur les tendances linéaires
- **Prophet** — Tendances + saisonnalité (Facebook Research)
- **LSTM/GRU** — Deep learning, capte les patterns non-linéaires d'accélération
- **XGBoost/LightGBM** — Gradient Boosting multivarié, robuste aux outliers
- **Consensus** — Moyenne pondérée des 4 modèles (réduction du biais individuel)

## 🗓️ Projections
Scénarios GIEC pour 2030 / 2050 / 2100 :
- 🟢 Optimiste : +1,4°C (SSP1-2.6)
- 🟡 Intermédiaire : +2,7°C (SSP2-4.5)
- 🔴 Pessimiste : +4,4°C (SSP5-8.5)
