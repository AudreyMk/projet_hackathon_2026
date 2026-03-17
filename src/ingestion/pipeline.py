"""
src/ingestion/pipeline.py
=========================
Orchestrateur principal du pipeline d'ingestion.
Lance tous les téléchargements de données en parallèle.

Usage:
    python -m src.ingestion.pipeline --territory france
    python -m src.ingestion.pipeline --territory region --code 11
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

# Ajout du root au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import RAW_DIR, TERRITORY, DATA_SOURCES
from src.ingestion.meteo_france import MeteoFranceIngester
from src.ingestion.noaa_co2 import NOAACo2Ingester
from src.ingestion.citepa_secten import CitepaIngester

console = Console()


class DataPipeline:
    """
    Orchestrateur principal d'ingestion multi-source.

    Télécharge et stocke en parallèle :
    - Météo France (températures, précipitations, stations)
    - NOAA (CO₂/CH₄)
    - CITEPA Secten (GES France)
    """

    def __init__(self, territory=None):
        self.territory = territory or TERRITORY
        self.ingesters = {
            "Météo France":  MeteoFranceIngester(self.territory),
            "NOAA CO₂/CH₄": NOAACo2Ingester(),
            "CITEPA GES":    CitepaIngester(),
        }
        self.results: dict = {}

    def run(self, parallel: bool = True) -> dict:
        """
        Lance tous les ingesteurs.

        Args:
            parallel: Si True, exécution en parallèle (ThreadPool).

        Returns:
            dict: {source_name: {"status": "ok"|"error", "files": [...], "rows": int}}
        """
        console.print(f"\n[bold #6c5ce7]🌍 Pipeline d'ingestion — Territoire : {self.territory.name}[/]")
        console.print(f"[dim]Destination : {RAW_DIR}[/]\n")

        if parallel:
            self._run_parallel()
        else:
            self._run_sequential()

        self._print_summary()
        return self.results

    def _run_parallel(self):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            tasks = {
                name: progress.add_task(f"[cyan]{name}...", total=None)
                for name in self.ingesters
            }

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(self._run_ingester, name, ingester): name
                    for name, ingester in self.ingesters.items()
                }
                for future in as_completed(futures):
                    name = futures[future]
                    result = future.result()
                    self.results[name] = result
                    progress.update(tasks[name], completed=True,
                                    description=f"[{'green' if result['status']=='ok' else 'red'}]{name}")

    def _run_sequential(self):
        for name, ingester in self.ingesters.items():
            console.print(f"[cyan]▶ {name}...[/]")
            self.results[name] = self._run_ingester(name, ingester)

    def _run_ingester(self, name: str, ingester) -> dict:
        """Exécute un ingesteur et capture les erreurs."""
        try:
            files = ingester.run()
            rows = ingester.get_row_count()
            logger.info(f"{name} — {rows:,} lignes — {len(files)} fichiers")
            return {"status": "ok", "files": files, "rows": rows, "error": None}
        except Exception as e:
            logger.error(f"{name} — {e}")
            return {"status": "error", "files": [], "rows": 0, "error": str(e)}

    def _print_summary(self):
        """Affiche un tableau récapitulatif dans le terminal."""
        table = Table(title="📋 Résumé de l'ingestion", style="bold")
        table.add_column("Source", style="cyan")
        table.add_column("Statut", justify="center")
        table.add_column("Lignes", justify="right", style="green")
        table.add_column("Fichiers", justify="right")
        table.add_column("Erreur", style="red")

        total_rows = 0
        for name, r in self.results.items():
            status_str = "✅ OK" if r["status"] == "ok" else "❌ ERREUR"
            table.add_row(
                name,
                status_str,
                f"{r['rows']:,}" if r["rows"] else "—",
                str(len(r["files"])),
                r.get("error") or "—",
            )
            total_rows += r["rows"]

        console.print(table)
        console.print(f"\n[bold green]Total : {total_rows:,} lignes ingérées[/]")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="Pipeline d'ingestion climatique")
    parser.add_argument("--territory", default="france",
                        choices=["france", "region", "commune"],
                        help="Niveau du territoire d'étude")
    parser.add_argument("--region-code", default=None,
                        help="Code région INSEE (ex: 11 pour IDF)")
    parser.add_argument("--sequential", action="store_true",
                        help="Exécution séquentielle (debug)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    from config.settings import Territory
    territory = Territory(
        name=args.territory.title(),
        level=args.territory,
        region_code=args.region_code,
    )

    pipeline = DataPipeline(territory=territory)
    results = pipeline.run(parallel=not args.sequential)

    # Code de sortie selon le succès
    errors = [n for n, r in results.items() if r["status"] == "error"]
    sys.exit(1 if errors else 0)
