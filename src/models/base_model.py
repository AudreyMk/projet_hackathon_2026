"""
src/models/base_model.py
=========================
Classe abstraite commune à tous les modèles de prédiction climatique.
Standardise l'interface : train / predict / evaluate / save / load.
Intégration MLflow pour le tracking des expériences.
"""

import abc
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import mlflow
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import MLFLOW_DIR, PROCESSED_DIR, SCENARIOS, PROJECTION_YEARS, MODEL_CONFIG


class BaseClimateModel(abc.ABC):
    """
    Classe de base pour tous les modèles climatiques.

    Toutes les sous-classes doivent implémenter :
    - _fit(X_train, y_train)
    - _predict(X)
    - get_model_params()
    """

    def __init__(self, target: str = "temp_moy_c", model_name: str = "base"):
        self.target = target
        self.model_name = model_name
        self.model = None
        self.is_fitted = False
        self.metrics: Dict = {}
        self.feature_names: List[str] = []

        # MLflow setup
        mlflow.set_tracking_uri(str(MLFLOW_DIR))
        mlflow.set_experiment(f"hackathon26_{target}")

    # 
    # INTERFACE PUBLIQUE
    # 
    def train(self, df: pd.DataFrame, test_size: float = 0.2) -> Dict:
        """
        Entraîne le modèle avec tracking MLflow.

        Args:
            df: DataFrame avec les features (index chronologique)
            test_size: Proportion du jeu de test (time-based split)

        Returns:
            dict: Métriques d'évaluation {rmse, mae, mape, r2}
        """
        logger.info(f" [{self.model_name}] Entraînement sur '{self.target}'...")

        # Préparation des données
        X, y = self._prepare_data(df)
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Entraînement + MLflow
        with mlflow.start_run(run_name=f"{self.model_name}_{datetime.now():%Y%m%d_%H%M}"):
            mlflow.set_tags({
                "model": self.model_name,
                "target": self.target,
                "framework": self.__class__.__module__,
            })

            self._fit(X_train, y_train)
            y_pred = self._predict(X_test)

            self.metrics = self._compute_metrics(y_test, y_pred)
            mlflow.log_metrics(self.metrics)
            mlflow.log_params(self.get_model_params())

            logger.success(
                f" [{self.model_name}] RMSE={self.metrics['rmse']:.4f} | "
                f"MAE={self.metrics['mae']:.4f} | R²={self.metrics['r2']:.4f}"
            )

        self.is_fitted = True
        return self.metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Prédit sur de nouvelles données."""
        if not self.is_fitted:
            raise RuntimeError(f"Le modèle {self.model_name} n'est pas encore entraîné.")
        return self._predict(X)

    def generate_projections(
        self,
        df_history: pd.DataFrame,
        horizon_years: List[int] = None,
    ) -> pd.DataFrame:
        """
        Génère des projections climatiques selon 3 scénarios GIEC.

        Args:
            df_history: Historique des données
            horizon_years: Années cibles (défaut: [2030, 2050, 2100])

        Returns:
            DataFrame avec colonnes [annee, scenario, prediction, lower_ci, upper_ci]
        """
        if horizon_years is None:
            horizon_years = PROJECTION_YEARS

        results = []
        last_year = int(df_history["annee"].max())

        for scenario_name, scenario_info in SCENARIOS.items():
            # Projection de base (tendance historique)
            base_trend = self._estimate_base_trend(df_history)

            for target_year in horizon_years:
                years_ahead = target_year - last_year
                if years_ahead <= 0:
                    continue

                # Projection avec ajustement scénario
                base_pred = self._project_forward(df_history, years_ahead)
                scenario_adjustment = self._scenario_adjustment(
                    base_pred, scenario_info["delta_temp"], years_ahead
                )

                pred_value = base_pred + scenario_adjustment
                # Intervalle de confiance qui s'élargit avec l'horizon
                uncertainty = base_pred * 0.05 * np.sqrt(years_ahead / 10)

                results.append({
                    "annee": target_year,
                    "scenario": scenario_name,
                    "scenario_label": scenario_info["label"],
                    "prediction": round(float(pred_value), 3),
                    "lower_ci": round(float(pred_value - 1.96 * uncertainty), 3),
                    "upper_ci": round(float(pred_value + 1.96 * uncertainty), 3),
                    "delta_temp": scenario_info["delta_temp"],
                    "color": scenario_info["color"],
                    "target_variable": self.target,
                    "model": self.model_name,
                })

        df_proj = pd.DataFrame(results)
        logger.info(f" [{self.model_name}] {len(df_proj)} projections générées")
        return df_proj

    # 
    # MÉTHODES ABSTRAITES
    # 
    @abc.abstractmethod
    def _fit(self, X_train: np.ndarray, y_train: np.ndarray):
        """Entraîne le modèle interne."""
        pass

    @abc.abstractmethod
    def _predict(self, X: np.ndarray) -> np.ndarray:
        """Retourne les prédictions."""
        pass

    @abc.abstractmethod
    def get_model_params(self) -> Dict:
        """Retourne les hyperparamètres loggués dans MLflow."""
        pass

    # 
    # HELPERS COMMUNS
    # 
    def _prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prépare X et y depuis le DataFrame."""
        df_clean = df.dropna(subset=[self.target]).copy()
        exclude = [self.target, "annee", "source"] + [
            c for c in df.columns if c.endswith("_quality")
        ]
        feature_cols = [c for c in df_clean.columns if c not in exclude
                        and df_clean[c].dtype in [np.float64, np.int64, np.float32]]
        self.feature_names = feature_cols

        X = df_clean[feature_cols].ffill().fillna(0).values
        y = df_clean[self.target].values
        return X, y

    @staticmethod
    def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Calcule RMSE, MAE, MAPE, R²."""
        y_true = np.array(y_true, dtype=float)
        y_pred = np.array(y_pred, dtype=float)

        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)

        # MAPE (évite division par zéro)
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else np.nan

        return {"rmse": round(rmse, 5), "mae": round(mae, 5),
                "mape": round(mape, 3), "r2": round(r2, 5)}

    def _estimate_base_trend(self, df: pd.DataFrame) -> float:
        """Estime la valeur actuelle et la tendance."""
        if self.target in df.columns:
            recent = df[df["annee"] >= df["annee"].max() - 10][self.target].dropna()
            return float(recent.mean()) if len(recent) > 0 else 12.0
        return 12.0

    def _project_forward(self, df: pd.DataFrame, years_ahead: int) -> float:
        """Projection forward simplifiée (tendance linéaire)."""
        if self.target not in df.columns:
            return 12.0
        s = df[self.target].dropna().values
        if len(s) < 2:
            return float(s[-1]) if len(s) > 0 else 12.0
        # Tendance sur les 30 dernières années
        n = min(30, len(s))
        x = np.arange(n)
        slope, intercept = np.polyfit(x, s[-n:], 1)
        return float(intercept + slope * (n + years_ahead))

    def _scenario_adjustment(self, base: float, delta_temp: float, years_ahead: int) -> float:
        """Ajustement scénarisé par rapport à la tendance de base."""
        if self.target == "temp_moy_c":
            # Proportion du réchauffement scénario sur la période
            return delta_temp * (years_ahead / 74)  # 74 = 2100 - 2026
        elif self.target == "co2_ppm":
            scenario_factor = delta_temp / 4.4  # Normalisation
            return 80 * scenario_factor * (years_ahead / 74)
        return 0.0
