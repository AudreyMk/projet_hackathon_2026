"""
tests/test_pipeline.py
========================
Tests unitaires pour valider le pipeline complet.
Lance avec : pytest tests/ -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────
# TESTS INGESTION
# ─────────────────────────────────────────────
class TestMeteoFranceIngester:
    def test_generate_temperature_data(self):
        from src.ingestion.meteo_france import MeteoFranceIngester
        ingester = MeteoFranceIngester()
        files = ingester._generate_realistic_temperature_data()
        assert len(files) == 1, "Doit produire 1 fichier"
        assert files[0].exists(), "Le fichier doit exister"

        df = pd.read_parquet(files[0])
        assert len(df) == 125, "125 années (1900-2024)"
        assert "temp_moy_c" in df.columns
        assert "jours_chauds_30" in df.columns
        assert df["temp_moy_c"].between(9, 16).all(), "Températures France plausibles"

    def test_temperature_trend_positive(self):
        from src.ingestion.meteo_france import MeteoFranceIngester
        ingester = MeteoFranceIngester()
        ingester._generate_realistic_temperature_data()
        df = pd.read_parquet(ingester.output_dir / "temperatures_annuelles.parquet")

        temp_1900_1920 = df[df["annee"] <= 1920]["temp_moy_c"].mean()
        temp_2000_2024 = df[df["annee"] >= 2000]["temp_moy_c"].mean()
        assert temp_2000_2024 > temp_1900_1920, "Réchauffement attendu sur la période"


class TestNOAACo2Ingester:
    def test_generate_co2_data(self):
        from src.ingestion.noaa_co2 import NOAACo2Ingester
        ingester = NOAACo2Ingester()
        files = ingester._generate_synthetic_co2()
        assert len(files) == 1
        df = pd.read_parquet(files[0])
        assert df["co2_ppm"].min() >= 290
        assert df["co2_ppm"].max() <= 430
        # CO₂ doit être croissant globalement
        assert df["co2_ppm"].iloc[-1] > df["co2_ppm"].iloc[0]


class TestCitepaIngester:
    def test_generate_ges_data(self):
        from src.ingestion.citepa_secten import CitepaIngester
        ingester = CitepaIngester()
        df = ingester._generate_realistic_ges()
        assert "annee" in df.columns
        assert "secteur" in df.columns
        assert "emissions_mtco2eq" in df.columns
        assert df["emissions_mtco2eq"].ge(0).all(), "Pas d'émissions négatives"

        # Total 2024 < total 1990 (baisse des émissions)
        total_1990 = df[(df["annee"] == 1990) & (df["secteur"] == "TOTAL")]["emissions_mtco2eq"].sum()
        total_2024 = df[(df["annee"] == 2024) & (df["secteur"] == "TOTAL")]["emissions_mtco2eq"].sum()
        assert total_2024 < total_1990, "Émissions doivent baisser sur la période"


# ─────────────────────────────────────────────
# TESTS PROCESSING
# ─────────────────────────────────────────────
class TestDataCleaner:
    def test_interpolation_missing_values(self):
        from src.processing.cleaner import DataCleaner

        # Créer un DataFrame avec des manquants
        df = pd.DataFrame({
            "annee": range(2000, 2020),
            "temp_moy_c": [12.0, np.nan, 12.5, np.nan, np.nan, 13.0] + [13.0] * 14,
        })
        cleaner = DataCleaner()
        df_clean, report = cleaner.clean_dataset(df, "test")

        assert df_clean["temp_moy_c"].isna().sum() == 0, "Plus de NaN après nettoyage"
        assert "interpolé" in str(report["actions"])

    def test_outlier_detection(self):
        from src.processing.cleaner import DataCleaner

        df = pd.DataFrame({
            "annee": range(2000, 2050),
            "temp_moy_c": [12.0] * 48 + [999.0, -999.0],  # 2 outliers extrêmes
        })
        cleaner = DataCleaner()
        df_clean, report = cleaner.clean_dataset(df, "test_outliers")
        assert df_clean["temp_moy_c"].max() < 50, "Outlier extrême supprimé"


# ─────────────────────────────────────────────
# TESTS MODÈLES
# ─────────────────────────────────────────────
class TestBaseModel:
    @pytest.fixture
    def sample_df(self):
        """DataFrame de test avec données climatiques synthétiques."""
        np.random.seed(42)
        years = list(range(1950, 2025))
        n = len(years)
        return pd.DataFrame({
            "annee": years,
            "temp_moy_c": (12.0 + np.linspace(0, 1.5, n) + np.random.normal(0, 0.2, n)).round(2),
            "co2_ppm": (310 + np.linspace(0, 110, n)).round(1),
        })

    def test_metrics_computation(self, sample_df):
        from src.models.base_model import BaseClimateModel

        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 2.1, 2.9, 4.2, 4.8])
        metrics = BaseClimateModel._compute_metrics(y_true, y_pred)

        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics
        assert "mape" in metrics
        assert metrics["rmse"] > 0
        assert 0 <= metrics["r2"] <= 1


# ─────────────────────────────────────────────
# TESTS RECOMMANDATIONS
# ─────────────────────────────────────────────
class TestRecommendationEngine:
    def test_high_risk_generates_fire_recs(self):
        from src.recommendations.citizen_actions import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.get_recommendations(risk_score=80, jours_chauds=35,
                                          deficit_precip=-20, territoire="France")
        assert any("incendie" in k.lower() or "feux" in k.lower() for k in recs.keys())

    def test_low_risk_no_fire_recs(self):
        from src.recommendations.citizen_actions import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.get_recommendations(risk_score=20, jours_chauds=5,
                                          deficit_precip=0, territoire="France")
        assert not any("incendie" in k.lower() or "feux" in k.lower() for k in recs.keys())

    def test_carbone_always_included(self):
        from src.recommendations.citizen_actions import RecommendationEngine
        engine = RecommendationEngine()
        for score in [10, 50, 90]:
            recs = engine.get_recommendations(risk_score=score, jours_chauds=10,
                                              deficit_precip=0, territoire="Test")
            assert any("carbone" in k.lower() for k in recs.keys()), \
                "Réduction carbone doit toujours être incluse"

    def test_all_actions_have_required_fields(self):
        from src.recommendations.citizen_actions import RecommendationEngine
        engine = RecommendationEngine()
        recs = engine.get_recommendations(risk_score=70, jours_chauds=30,
                                          deficit_precip=-15, territoire="Paris")
        for category, actions in recs.items():
            for action in actions:
                assert "titre" in action, f"Champ 'titre' manquant dans {category}"
                assert "description" in action
                assert "impact" in action
                assert "priority" in action
                assert action["priority"] in ["haute", "moyenne", "basse"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
