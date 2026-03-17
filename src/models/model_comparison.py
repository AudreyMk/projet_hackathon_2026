"""
src/models/model_comparison.py
================================
Benchmark automatique de tous les modèles.
Génère un rapport HTML de comparaison avec métriques et graphiques.

Usage:
    python -m src.models.model_comparison
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from loguru import logger
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import PROCESSED_DIR, REPORTS_DIR, PROJECTION_YEARS, SCENARIOS
from src.models.all_models import ARIMAModel, ProphetModel, LSTMModel, GradientBoostingModel

console = Console()


class ModelBenchmark:
    """
    Compare tous les modèles sur le même jeu de données.

    Critères :
    - RMSE (Root Mean Square Error) — métrique principale
    - MAE (Mean Absolute Error)
    - MAPE (Mean Absolute Percentage Error)
    - R² (coefficient de détermination)
    - Temps d'entraînement
    - Plausibilité des projections
    """

    MODELS = {
        "SARIMA": ARIMAModel,
        "Prophet": ProphetModel,
        "LSTM": LSTMModel,
        "XGBoost": GradientBoostingModel,
    }

    def __init__(self, target: str = "temp_moy_c"):
        self.target = target
        self.results: Dict = {}
        self.projections: pd.DataFrame = pd.DataFrame()
        self.best_model_name: str = None

    def run(self) -> Dict:
        """Lance le benchmark complet."""
        logger.info(f" Benchmark des modèles — cible : {self.target}")

        # Chargement des données
        df = self._load_features()
        if df is None:
            logger.error(" Données master_features.parquet introuvables. Lance 'make process' d'abord.")
            return {}

        all_projections = []

        for model_name, ModelClass in self.MODELS.items():
            logger.info(f"\n {model_name} ")
            t0 = time.time()

            try:
                model = ModelClass(target=self.target)
                metrics = model.train(df, test_size=0.2)
                train_time = round(time.time() - t0, 2)

                self.results[model_name] = {
                    "metrics": metrics,
                    "train_time_s": train_time,
                    "status": "ok",
                }

                # Projections
                proj = model.generate_projections(df)
                proj["model"] = model_name
                all_projections.append(proj)

            except Exception as e:
                logger.error(f" {model_name} : {e}")
                self.results[model_name] = {"status": "error", "error": str(e)}

        if all_projections:
            self.projections = pd.concat(all_projections, ignore_index=True)

        self._select_best_model()
        self._print_leaderboard()
        self._generate_report()

        return self.results

    def _load_features(self) -> pd.DataFrame | None:
        path = PROCESSED_DIR / "master_features.parquet"
        if path.exists():
            return pd.read_parquet(path)

        # Fallback : données synthétiques pour démonstration
        logger.warning(" Utilisation données synthétiques pour le benchmark")
        years = list(range(1900, 2025))
        np.random.seed(42)
        trend = np.linspace(0, 1.7, len(years))
        noise = np.random.normal(0, 0.25, len(years))
        df = pd.DataFrame({
            "annee": years,
            "temp_moy_c": (12.0 + trend + noise).round(2),
            "co2_ppm": (296 + np.linspace(0, 127, len(years))).round(1),
            "anomalie_temp_c": (trend + noise).round(3),
        })
        df.to_parquet(PROCESSED_DIR / "master_features.parquet", index=False)
        return df

    def _select_best_model(self):
        """Sélectionne le meilleur modèle selon la RMSE."""
        valid = {
            k: v for k, v in self.results.items()
            if v.get("status") == "ok" and "metrics" in v
        }
        if not valid:
            return
        self.best_model_name = min(valid, key=lambda k: valid[k]["metrics"]["rmse"])
        logger.success(f" Meilleur modèle : {self.best_model_name} "
                       f"(RMSE={valid[self.best_model_name]['metrics']['rmse']:.4f})")

    def _print_leaderboard(self):
        """Affiche le classement des modèles dans le terminal."""
        table = Table(title=" Leaderboard des modèles", style="bold")
        table.add_column("Rang", justify="center")
        table.add_column("Modèle", style="cyan")
        table.add_column("RMSE ↓", justify="right", style="green")
        table.add_column("MAE ↓", justify="right")
        table.add_column("MAPE ↓", justify="right")
        table.add_column("R² ↑", justify="right")
        table.add_column("Temps (s)", justify="right", style="dim")
        table.add_column("Statut")

        valid_models = [
            (k, v) for k, v in self.results.items() if v.get("status") == "ok"
        ]
        valid_models.sort(key=lambda x: x[1]["metrics"]["rmse"])

        for rank, (name, info) in enumerate(valid_models, 1):
            m = info["metrics"]
            is_best = name == self.best_model_name
            table.add_row(
                f"{'' if rank==1 else '' if rank==2 else '' if rank==3 else str(rank)}",
                f"[bold]{name}[/]" if is_best else name,
                str(m.get("rmse", "—")),
                str(m.get("mae", "—")),
                f"{m.get('mape', '—'):.2f}%",
                str(m.get("r2", "—")),
                str(info.get("train_time_s", "—")),
                " Best" if is_best else "",
            )

        for name, info in self.results.items():
            if info.get("status") == "error":
                table.add_row("—", name, "—", "—", "—", "—", "—", " Erreur")

        console.print(table)

    def _generate_report(self):
        """Génère un rapport HTML interactif avec Plotly."""
        if not self.results:
            return

        fig = go.Figure()

        # Graphique comparaison des métriques
        model_names = [k for k, v in self.results.items() if v.get("status") == "ok"]
        rmse_values = [self.results[k]["metrics"]["rmse"] for k in model_names]
        r2_values = [self.results[k]["metrics"]["r2"] for k in model_names]

        colors = ["#6c5ce7" if n == self.best_model_name else "#a29bfe" for n in model_names]

        fig.add_trace(go.Bar(
            name="RMSE",
            x=model_names,
            y=rmse_values,
            marker_color=colors,
            text=[f"{v:.4f}" for v in rmse_values],
            textposition="outside",
        ))

        fig.update_layout(
            title=f" Comparaison des modèles — Cible : {self.target}",
            template="plotly_dark",
            xaxis_title="Modèle",
            yaxis_title="RMSE (plus bas = meilleur)",
            height=500,
        )

        # Projections superposées
        if not self.projections.empty:
            fig_proj = go.Figure()
            for model_name in self.projections["model"].unique():
                for scenario in ["optimiste", "intermediaire", "pessimiste"]:
                    mask = (self.projections["model"] == model_name) & \
                           (self.projections["scenario"] == scenario)
                    sub = self.projections[mask]
                    if len(sub) > 0:
                        fig_proj.add_trace(go.Scatter(
                            x=sub["annee"],
                            y=sub["prediction"],
                            mode="lines+markers",
                            name=f"{model_name} - {scenario}",
                            line=dict(dash="dot" if scenario != "intermediaire" else "solid"),
                        ))

            fig_proj.update_layout(
                title=" Projections climatiques 2030 / 2050 / 2100",
                template="plotly_dark",
                xaxis_title="Année",
                yaxis_title=self.target,
                height=600,
            )

        # Sauvegarde
        out = REPORTS_DIR / "model_comparison.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write("<html><head><meta charset='utf-8'><title>Benchmark Modèles Climatiques</title></head><body>")
            f.write("<h1 style='font-family:sans-serif;color:#6c5ce7'> Hackathon #26 — Comparaison des modèles</h1>")
            f.write(fig.to_html(full_html=False, include_plotlyjs="cdn"))
            if not self.projections.empty:
                f.write(fig_proj.to_html(full_html=False, include_plotlyjs=False))
            f.write("</body></html>")

        logger.success(f" Rapport généré : {out}")

        # Export CSV des projections
        if not self.projections.empty:
            self.projections.to_csv(REPORTS_DIR / "projections_all_models.csv", index=False)
            logger.info(f"  CSV projections : {REPORTS_DIR / 'projections_all_models.csv'}")


if __name__ == "__main__":
    benchmark = ModelBenchmark(target="temp_moy_c")
    results = benchmark.run()
