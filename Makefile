# =============================================
# Hackathon #26 — Changement Climatique
# Makefile — Gestion de projet complète
# =============================================

.PHONY: help install all ingest process train compare dashboard mlflow clean test lint format

PYTHON = python
SRC = src
TERRITORY ?= france   # france | region | commune

# ─────────────────────────────────────────────
# 🆘 AIDE
# ─────────────────────────────────────────────
help:
	@echo ""
	@echo "╔══════════════════════════════════════════════╗"
	@echo "║   Hackathon #26 — Changement Climatique     ║"
	@echo "╚══════════════════════════════════════════════╝"
	@echo ""
	@echo "  make install      → Installe les dépendances"
	@echo "  make all          → Pipeline complet (ingest+process+train)"
	@echo "  make ingest       → Télécharge toutes les données"
	@echo "  make process      → Nettoie & transforme les données"
	@echo "  make train        → Entraîne tous les modèles"
	@echo "  make compare      → Benchmark des modèles (RMSE/MAE/MAPE)"
	@echo "  make dashboard    → Lance le dashboard Streamlit"
	@echo "  make mlflow       → Lance l'UI MLflow"
	@echo "  make test         → Lance les tests unitaires"
	@echo "  make lint         → Vérifie la qualité du code"
	@echo "  make format       → Formate le code (black)"
	@echo "  make clean        → Supprime les artefacts temporaires"
	@echo ""
	@echo "  Territoire : make ingest TERRITORY=ile_de_france"
	@echo ""

# ─────────────────────────────────────────────
# 📦 INSTALLATION
# ─────────────────────────────────────────────
install:
	@echo "📦 Installation des dépendances..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✅ Installation terminée"

# ─────────────────────────────────────────────
# 🔄 PIPELINE COMPLET
# ─────────────────────────────────────────────
all: ingest process train compare
	@echo ""
	@echo "✅ Pipeline complet terminé !"
	@echo "👉 Lance le dashboard : make dashboard"

# ─────────────────────────────────────────────
# 📥 INGESTION DES DONNÉES
# ─────────────────────────────────────────────
ingest:
	@echo "📥 Ingestion des données (territoire: $(TERRITORY))..."
	$(PYTHON) -m src.ingestion.pipeline --territory $(TERRITORY)
	@echo "✅ Données ingérées → data/raw/"

ingest-meteo:
	@echo "🌦️  Météo France..."
	$(PYTHON) -m src.ingestion.meteo_france --territory $(TERRITORY)

ingest-co2:
	@echo "🏭 NOAA CO₂/CH₄..."
	$(PYTHON) -m src.ingestion.noaa_co2

ingest-ges:
	@echo "⚗️  CITEPA Secten GES..."
	$(PYTHON) -m src.ingestion.citepa_secten

# ─────────────────────────────────────────────
# 🧹 TRAITEMENT DES DONNÉES
# ─────────────────────────────────────────────
process:
	@echo "🧹 Nettoyage & transformation..."
	$(PYTHON) -m src.processing.cleaner
	$(PYTHON) -m src.processing.transformer
	$(PYTHON) -m src.processing.features
	@echo "✅ Données traitées → data/processed/"

# ─────────────────────────────────────────────
# 🤖 ENTRAÎNEMENT DES MODÈLES
# ─────────────────────────────────────────────
train: train-arima train-prophet train-lstm train-gbm
	@echo "✅ Tous les modèles entraînés"

train-arima:
	@echo "📈 ARIMA/SARIMA..."
	$(PYTHON) -m src.models.arima_model

train-prophet:
	@echo "🔮 Prophet..."
	$(PYTHON) -m src.models.prophet_model

train-lstm:
	@echo "🧠 LSTM/GRU..."
	$(PYTHON) -m src.models.lstm_model

train-gbm:
	@echo "🌲 Gradient Boosting..."
	$(PYTHON) -m src.models.gradient_boosting

# ─────────────────────────────────────────────
# 📊 COMPARAISON DES MODÈLES
# ─────────────────────────────────────────────
compare:
	@echo "📊 Benchmark des modèles..."
	$(PYTHON) -m src.models.model_comparison
	@echo "✅ Rapport de comparaison → reports/model_comparison.html"

# ─────────────────────────────────────────────
# 🖥️  DASHBOARD & MLFLOW
# ─────────────────────────────────────────────
dashboard:
	@echo "🖥️  Lancement du dashboard Streamlit..."
	streamlit run src/visualization/dashboard.py --server.port 8501

mlflow:
	@echo "📈 Lancement MLflow UI..."
	mlflow ui --backend-store-uri ./mlflow_runs --port 5000

# ─────────────────────────────────────────────
# 🧪 TESTS & QUALITÉ
# ─────────────────────────────────────────────
test:
	@echo "🧪 Tests unitaires..."
	pytest tests/ -v --tb=short

lint:
	@echo "🔍 Vérification qualité..."
	flake8 src/ --max-line-length=100 --ignore=E203,W503

format:
	@echo "✨ Formatage du code..."
	black src/ notebooks/ --line-length 100

# ─────────────────────────────────────────────
# 🗑️  NETTOYAGE
# ─────────────────────────────────────────────
clean:
	@echo "🗑️  Nettoyage des artefacts..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Nettoyage terminé"

clean-data:
	@echo "⚠️  Suppression des données traitées..."
	rm -rf data/processed/*
	@echo "✅ data/processed/ vidé"
