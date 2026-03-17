"""
src/models/arima_model.py  +  prophet_model.py  +  lstm_model.py
==================================================================
Implémentations des 4 modèles de prédiction climatique.
Chaque modèle hérite de BaseClimateModel.
"""

# 
# ARIMA / SARIMA
# 
import warnings
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.base_model import BaseClimateModel
from config.settings import MODEL_CONFIG


class ARIMAModel(BaseClimateModel):
    """
    Modèle ARIMA / SARIMA pour séries temporelles climatiques.

    Utilise pmdarima.auto_arima pour sélectionner automatiquement
    les ordres (p, d, q) et (P, D, Q, m) optimaux.
    """

    def __init__(self, target: str = "temp_moy_c"):
        super().__init__(target=target, model_name="SARIMA")
        self.cfg = MODEL_CONFIG["arima"]
        self._arima_model = None
        self._last_train_series = None

    def _fit(self, X_train: np.ndarray, y_train: np.ndarray):
        """Auto-ARIMA avec saisonnalité."""
        import pmdarima as pm
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._arima_model = pm.auto_arima(
                y_train,
                start_p=1, start_q=1,
                max_p=self.cfg["max_p"],
                max_d=self.cfg["max_d"],
                max_q=self.cfg["max_q"],
                seasonal=self.cfg["seasonal"],
                m=self.cfg["m"],
                information_criterion="aic",
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
            )
        self._last_train_series = y_train
        logger.info(f"  SARIMA ordre : {self._arima_model.order} × {self._arima_model.seasonal_order}")

    def _predict(self, X: np.ndarray) -> np.ndarray:
        n = len(X)
        preds, _ = self._arima_model.predict(n_periods=n, return_conf_int=True)
        return preds

    def get_model_params(self) -> Dict:
        return {
            "order": str(self._arima_model.order),
            "seasonal_order": str(self._arima_model.seasonal_order),
            "aic": round(self._arima_model.aic(), 4),
        }

    def _project_forward(self, df: pd.DataFrame, years_ahead: int) -> float:
        """Utilise le modèle ARIMA directement pour projeter."""
        if self._arima_model is not None:
            preds = self._arima_model.predict(n_periods=years_ahead)
            return float(preds[-1])
        return super()._project_forward(df, years_ahead)


# 
# PROPHET
# 

class ProphetModel(BaseClimateModel):
    """
    Modèle Facebook Prophet pour séries temporelles climatiques.

    Gère automatiquement tendance + saisonnalité + points de rupture.
    """

    def __init__(self, target: str = "temp_moy_c"):
        super().__init__(target=target, model_name="Prophet")
        self.cfg = MODEL_CONFIG["prophet"]
        self._prophet = None
        self._df_train = None

    def _fit(self, X_train: np.ndarray, y_train: np.ndarray):
        from prophet import Prophet

        # Prophet attend un DataFrame avec colonnes 'ds' et 'y'
        # On reconstruit la série temporelle annuelle
        n = len(y_train)
        start_year = 1900
        dates = pd.date_range(start=f"{start_year}-01-01", periods=n, freq="YS")

        self._df_train = pd.DataFrame({"ds": dates, "y": y_train})

        self._prophet = Prophet(
            changepoint_prior_scale=self.cfg["changepoint_prior_scale"],
            seasonality_mode=self.cfg["seasonality_mode"],
            yearly_seasonality=self.cfg["yearly_seasonality"],
            interval_width=0.95,
        )
        self._prophet.fit(self._df_train)
        logger.info(f"  Prophet entraîné sur {n} années")

    def _predict(self, X: np.ndarray) -> np.ndarray:
        n = len(X)
        last_date = self._df_train["ds"].max()
        future = pd.date_range(start=last_date, periods=n + 1, freq="YS")[1:]
        future_df = pd.DataFrame({"ds": future})
        forecast = self._prophet.predict(future_df)
        return forecast["yhat"].values

    def get_model_params(self) -> Dict:
        return {
            "changepoint_prior_scale": self.cfg["changepoint_prior_scale"],
            "seasonality_mode": self.cfg["seasonality_mode"],
        }

    def _project_forward(self, df: pd.DataFrame, years_ahead: int) -> float:
        """Projection Prophet sur N années."""
        if self._prophet is not None and self._df_train is not None:
            last_date = self._df_train["ds"].max()
            future = pd.date_range(start=last_date, periods=years_ahead + 1, freq="YS")[1:]
            forecast = self._prophet.predict(pd.DataFrame({"ds": future}))
            return float(forecast["yhat"].iloc[-1])
        return super()._project_forward(df, years_ahead)


# 
# LSTM / GRU
# 

class LSTMModel(BaseClimateModel):
    """
    Réseau LSTM (Long Short-Term Memory) pour séries temporelles.

    Architecture : LSTM → Dropout → LSTM → Dense
    """

    def __init__(self, target: str = "temp_moy_c"):
        super().__init__(target=target, model_name="LSTM")
        self.cfg = MODEL_CONFIG["lstm"]
        self._scaler = None
        self._seq_len = self.cfg["sequence_length"]
        self._last_sequence = None

    def _fit(self, X_train: np.ndarray, y_train: np.ndarray):
        try:
            import tensorflow as tf
            from sklearn.preprocessing import MinMaxScaler
            tf.get_logger().setLevel("ERROR")

            # Normalisation
            self._scaler = MinMaxScaler()
            y_scaled = self._scaler.fit_transform(y_train.reshape(-1, 1)).flatten()

            # Création des séquences
            Xs, ys = self._create_sequences(y_scaled, self._seq_len)
            if len(Xs) == 0:
                raise ValueError("Pas assez de données pour LSTM")

            Xs = Xs.reshape(Xs.shape[0], Xs.shape[1], 1)

            # Architecture LSTM
            model = tf.keras.Sequential([
                tf.keras.layers.LSTM(self.cfg["units"][0], return_sequences=True,
                                     input_shape=(self._seq_len, 1)),
                tf.keras.layers.Dropout(self.cfg["dropout"]),
                tf.keras.layers.LSTM(self.cfg["units"][1], return_sequences=False),
                tf.keras.layers.Dropout(self.cfg["dropout"]),
                tf.keras.layers.Dense(16, activation="relu"),
                tf.keras.layers.Dense(1),
            ])
            model.compile(optimizer="adam", loss="mse", metrics=["mae"])

            callback = tf.keras.callbacks.EarlyStopping(
                patience=self.cfg["patience"], restore_best_weights=True
            )
            model.fit(
                Xs, ys,
                epochs=self.cfg["epochs"],
                batch_size=self.cfg["batch_size"],
                validation_split=0.1,
                callbacks=[callback],
                verbose=0,
            )
            self.model = model
            self._last_sequence = y_scaled[-self._seq_len:]
            logger.info(f"  LSTM entraîné — paramètres : {model.count_params():,}")

    def _predict(self, X: np.ndarray) -> np.ndarray:
        n = len(X)
        preds = []
        seq = self._last_sequence.copy()
        for _ in range(n):
            inp = seq[-self._seq_len:].reshape(1, self._seq_len, 1)
            pred_scaled = self.model.predict(inp, verbose=0)[0, 0]
            preds.append(pred_scaled)
            seq = np.append(seq, pred_scaled)
        return self._scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()

    def get_model_params(self) -> Dict:
        return {
            "sequence_length": self._seq_len,
            "units": str(self.cfg["units"]),
            "dropout": self.cfg["dropout"],
            "epochs": self.cfg["epochs"],
        }

    @staticmethod
    def _create_sequences(data: np.ndarray, seq_len: int):
        X, y = [], []
        for i in range(len(data) - seq_len):
            X.append(data[i: i + seq_len])
            y.append(data[i + seq_len])
        return np.array(X), np.array(y)


# 
# GRADIENT BOOSTING (XGBoost / LightGBM)
# 

class GradientBoostingModel(BaseClimateModel):
    """
    Gradient Boosting sur features temporelles (lags + tendance).
    Utilise XGBoost ou LightGBM selon la config.
    """

    def __init__(self, target: str = "temp_moy_c"):
        super().__init__(target=target, model_name="XGBoost")
        self.cfg = MODEL_CONFIG["gradient_boosting"]

    def _fit(self, X_train: np.ndarray, y_train: np.ndarray):
        try:
            if self.cfg["engine"] == "lightgbm":
                import lightgbm as lgb
                self.model = lgb.LGBMRegressor(
                    n_estimators=self.cfg["n_estimators"],
                    max_depth=self.cfg["max_depth"],
                    learning_rate=self.cfg["learning_rate"],
                    random_state=42, verbose=-1,
                )
            else:
                import xgboost as xgb
                self.model = xgb.XGBRegressor(
                    n_estimators=self.cfg["n_estimators"],
                    max_depth=self.cfg["max_depth"],
                    learning_rate=self.cfg["learning_rate"],
                    random_state=42, verbosity=0,
                )
            self.model.fit(X_train, y_train)
            logger.info(f"  {self.cfg['engine'].upper()} entraîné — {self.cfg['n_estimators']} arbres")

    def _predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def get_model_params(self) -> Dict:
        return {
            "engine": self.cfg["engine"],
            "n_estimators": self.cfg["n_estimators"],
            "max_depth": self.cfg["max_depth"],
            "learning_rate": self.cfg["learning_rate"],
        }


if __name__ == "__main__":
    # Test rapide : vérification imports
    print(" Modèles disponibles : ARIMAModel, ProphetModel, LSTMModel, GradientBoostingModel")
