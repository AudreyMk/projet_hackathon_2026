"""
scripts/run_model.py
=====================
CLI unifié pour entraîner les modèles de prédiction climatique.

Usage :
    python scripts/run_model.py arima      # ARIMA/SARIMA
    python scripts/run_model.py prophet    # Prophet
    python scripts/run_model.py lstm       # LSTM/GRU
    python scripts/run_model.py gb         # XGBoost / Gradient Boosting
    python scripts/run_model.py all        # Tous les modèles (benchmark)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from config.settings import PROCESSED_DIR
from src.models.all_models import ARIMAModel, ProphetModel, LSTMModel, GradientBoostingModel

MODEL_MAP = {
    "arima":   ("ARIMA/SARIMA",        ARIMAModel),
    "prophet": ("Prophet",             ProphetModel),
    "lstm":    ("LSTM/GRU",            LSTMModel),
    "gb":      ("Gradient Boosting",   GradientBoostingModel),
}


def run_model(name: str, df: pd.DataFrame):
    label, cls = MODEL_MAP[name]
    print(f"\n  Entraînement {label}…")
    model = cls()
    metrics = model.train(df)
    print(f"  {label} — RMSE: {metrics['rmse']:.4f} | MAE: {metrics['mae']:.4f} | R²: {metrics['r2']:.4f}")
    return metrics


if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    data_path = PROCESSED_DIR / "master_features.parquet"
    if not data_path.exists():
        print(f" Fichier introuvable : {data_path}")
        print("  Lancer d'abord : make process")
        sys.exit(1)

    df = pd.read_parquet(data_path)

    if target == "all":
        for name in MODEL_MAP:
            run_model(name, df)
    elif target in MODEL_MAP:
        run_model(target, df)
    else:
        print(f" Modèle inconnu : '{target}'")
        print(f"  Choix disponibles : {', '.join(MODEL_MAP.keys())} | all")
        sys.exit(1)
