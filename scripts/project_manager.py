"""
scripts/project_manager.py
============================
CLI de gestion de projet Hackathon #26.
Suivi des tâches, statuts, timeline et bilan de compétences.

Usage :
    python scripts/project_manager.py status       # Tableau de bord projet
    python scripts/project_manager.py tasks        # Liste toutes les tâches
    python scripts/project_manager.py done <id>    # Marquer une tâche terminée
    python scripts/project_manager.py next         # Prochaines tâches à faire
    python scripts/project_manager.py report       # Génère un rapport HTML
    python scripts/project_manager.py check        # Vérifie les fichiers du projet
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

#  Rich pour le terminal
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.columns import Columns
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# scripts/project_manager.py est dans scripts/ — la racine projet est un niveau au-dessus
ROOT = Path(__file__).parent.parent
STATE_FILE = ROOT / ".project_state.json"
console = Console() if HAS_RICH else None


#
# DÉFINITION DES TÂCHES DU PROJET
#
TASKS = {
    #  ÉTAPE 1 : Territoire
    "T01": {
        "titre": "Choisir et justifier le territoire d'étude",
        "etape": "1 - Territoire",
        "role": "Data",
        "priorite": "critique",
        "duree_h": 0.5,
        "dependances": [],
        "livrable": "Justification dans le README + config/settings.py",
        "conseils": "Choisir France entière pour plus de données disponibles (Météo France national).",
    },
    "T02": {
        "titre": "Analyser la disponibilité des sources de données",
        "etape": "1 - Territoire",
        "role": "Data",
        "priorite": "haute",
        "duree_h": 1.0,
        "dependances": ["T01"],
        "livrable": "Liste des sources validées dans le README",
        "conseils": "Tester les URLs de meteo.data.gouv.fr et NOAA avant de coder l'ingestion.",
    },

    #  ÉTAPE 2 : Indicateurs
    "T03": {
        "titre": "Sélectionner et scorer ≥ 8 indicateurs climatiques",
        "etape": "2 - Indicateurs",
        "role": "Data",
        "priorite": "critique",
        "duree_h": 1.0,
        "dependances": ["T01"],
        "livrable": "INDICATORS dict dans config/settings.py",
        "conseils": "Critères : potentiel narratif, lisibilité, pertinence citoyenne. Déjà configuré.",
    },

    #  ÉTAPE 3 : Pipeline Big Data
    "T04": {
        "titre": "Développer l'ingesteur Météo France",
        "etape": "3 - Pipeline",
        "role": "Data",
        "priorite": "critique",
        "duree_h": 2.0,
        "dependances": ["T02"],
        "livrable": "src/ingestion/meteo_france.py — données dans data/raw/meteofrance/",
        "conseils": "API OpenDataSoft peut être lente. Le fallback synthétique réaliste est déjà codé.",
    },
    "T05": {
        "titre": "Développer l'ingesteur NOAA CO₂/CH₄",
        "etape": "3 - Pipeline",
        "role": "Data",
        "priorite": "haute",
        "duree_h": 1.0,
        "dependances": ["T02"],
        "livrable": "src/ingestion/noaa_co2.py — données dans data/raw/noaa/",
        "conseils": "Données NOAA publiques et fiables. L'URL directe TXT est simple à parser.",
    },
    "T06": {
        "titre": "Développer l'ingesteur CITEPA Secten GES",
        "etape": "3 - Pipeline",
        "role": "Data",
        "priorite": "haute",
        "duree_h": 1.0,
        "dependances": ["T02"],
        "livrable": "src/ingestion/citepa_secten.py — GES France depuis 1990",
        "conseils": "Le fichier Excel Secten 2024 peut nécessiter une inscription. Fallback prévu.",
    },
    "T07": {
        "titre": "Nettoyer et transformer les données (cleaner + transformer)",
        "etape": "3 - Pipeline",
        "role": "Data",
        "priorite": "critique",
        "duree_h": 2.0,
        "dependances": ["T04", "T05", "T06"],
        "livrable": "data/processed/master_features.parquet",
        "conseils": "Lancer 'make process' après 'make ingest'. Vérifier les valeurs manquantes.",
    },
    "T08": {
        "titre": "Construire le master dataset avec feature engineering",
        "etape": "3 - Pipeline",
        "role": "Data",
        "priorite": "critique",
        "duree_h": 1.5,
        "dependances": ["T07"],
        "livrable": "src/processing/features.py — anomalies, lags, score risque",
        "conseils": "Le script features.py calcule automatiquement les 8+ indicateurs requis.",
    },

    #  ÉTAPE 4 : IA / Modèles
    "T09": {
        "titre": "Entraîner le modèle ARIMA/SARIMA",
        "etape": "4 - Modèles IA",
        "role": "Data Science",
        "priorite": "haute",
        "duree_h": 1.5,
        "dependances": ["T08"],
        "livrable": "Modèle loggué MLflow + métriques RMSE/MAE/R²",
        "conseils": "pmdarima.auto_arima sélectionne automatiquement les ordres. Très rapide.",
    },
    "T10": {
        "titre": "Entraîner le modèle Prophet",
        "etape": "4 - Modèles IA",
        "role": "Data Science",
        "priorite": "haute",
        "duree_h": 1.5,
        "dependances": ["T08"],
        "livrable": "Modèle Prophet loggué MLflow",
        "conseils": "Prophet gère bien les tendances à long terme. Idéal pour les projections 2100.",
    },
    "T11": {
        "titre": "Entraîner le modèle LSTM/GRU",
        "etape": "4 - Modèles IA",
        "role": "Data Science",
        "priorite": "moyenne",
        "duree_h": 2.5,
        "dependances": ["T08"],
        "livrable": "Modèle Keras loggué MLflow",
        "conseils": "Nécessite TensorFlow. Si trop long, réduire les epochs dans MODEL_CONFIG.",
    },
    "T12": {
        "titre": "Entraîner le modèle XGBoost/Gradient Boosting",
        "etape": "4 - Modèles IA",
        "role": "Data Science",
        "priorite": "haute",
        "duree_h": 1.5,
        "dependances": ["T08"],
        "livrable": "Modèle XGBoost loggué MLflow + feature importance",
        "conseils": "Souvent le meilleur résultat sur les données tabulaires climatiques.",
    },
    "T13": {
        "titre": "Benchmark et comparaison des 4 modèles",
        "etape": "4 - Modèles IA",
        "role": "Data Science",
        "priorite": "critique",
        "duree_h": 1.0,
        "dependances": ["T09", "T10", "T11", "T12"],
        "livrable": "reports/model_comparison.html + projections_all_models.csv",
        "conseils": "Lancer 'make compare'. Le rapport HTML est interactif (Plotly).",
    },
    "T14": {
        "titre": "Générer les projections 2030/2050/2100 (3 scénarios)",
        "etape": "4 - Modèles IA",
        "role": "Data Science",
        "priorite": "critique",
        "duree_h": 1.0,
        "dependances": ["T13"],
        "livrable": "reports/projections_all_models.csv",
        "conseils": "Scénarios SSP1-2.6, SSP2-4.5, SSP5-8.5 alignés avec les rapports GIEC 2023.",
    },

    #  ÉTAPE 5 : Dashboard
    "T15": {
        "titre": "Développer le dashboard Streamlit (onglets historique + projections)",
        "etape": "5 - Dashboard",
        "role": "Data Visu",
        "priorite": "critique",
        "duree_h": 3.0,
        "dependances": ["T14"],
        "livrable": "app.py + web/ — lancé avec 'streamlit run app.py'",
        "conseils": "Le dashboard est déjà structuré. Personnaliser les graphiques Plotly.",
    },
    "T16": {
        "titre": "Ajouter la cartographie interactive des régions",
        "etape": "5 - Dashboard",
        "role": "Data Visu",
        "priorite": "haute",
        "duree_h": 2.0,
        "dependances": ["T15"],
        "livrable": "Carte Folium/Plotly dans l'onglet cartographie",
        "conseils": "Utiliser le GeoJSON data/processed/france_departements_summary.geojson.",
    },
    "T17": {
        "titre": "Intégrer les préconisations citoyennes dans le dashboard",
        "etape": "5 - Dashboard",
        "role": "Data Visu",
        "priorite": "haute",
        "duree_h": 1.0,
        "dependances": ["T15"],
        "livrable": "Onglet 'Préconisations' du dashboard",
        "conseils": "Le moteur est dans src/recommendations/citizen_actions.py.",
    },

    #  ÉTAPE 6 : Pitch & Rapport
    "T18": {
        "titre": "Rédiger le rapport analytique",
        "etape": "6 - Livrables",
        "role": "CP IT",
        "priorite": "critique",
        "duree_h": 2.0,
        "dependances": ["T14", "T15"],
        "livrable": "reports/rapport_analytique.docx/.pdf",
        "conseils": "Inclure : territoire, indicateurs, méthodologie IA, projections, recommandations.",
    },
    "T19": {
        "titre": "Préparer le pitch de démonstration (10 min)",
        "etape": "6 - Livrables",
        "role": "CP IT + Data",
        "priorite": "critique",
        "duree_h": 2.0,
        "dependances": ["T18"],
        "livrable": "Présentation + démo live du dashboard",
        "conseils": "Structure : contexte → données → modèles → projections → actions citoyennes.",
    },
    "T20": {
        "titre": "Tests unitaires et validation du pipeline",
        "etape": "6 - Livrables",
        "role": "Data",
        "priorite": "moyenne",
        "duree_h": 1.0,
        "dependances": ["T08"],
        "livrable": "pytest tests/ — 0 erreur",
        "conseils": "Lancer 'make test' pour valider l'ensemble du pipeline.",
    },
}

# Planning suggéré (durées cumulatives en heures depuis le début)
PLANNING = {
    "J1_matin": {
        "heures": "09h00 - 12h30 (3.5h)",
        "taches": ["T01", "T02", "T03", "T04"],
        "objectif": "Territoire défini + ingestion Météo France opérationnelle"
    },
    "J1_aprem": {
        "heures": "13h30 - 17h30 (4h)",
        "taches": ["T05", "T06", "T07", "T08"],
        "objectif": "Pipeline complet — master_features.parquet disponible"
    },
    "J1_soir": {
        "heures": "17h30 - 20h00 (2.5h)",
        "taches": ["T09", "T10", "T12"],
        "objectif": "3 modèles entraînés (ARIMA, Prophet, XGBoost)"
    },
    "J2_matin": {
        "heures": "09h00 - 12h00 (3h)",
        "taches": ["T11", "T13", "T14"],
        "objectif": "LSTM + benchmark + projections 2100 générées"
    },
    "J2_aprem": {
        "heures": "13h00 - 16h00 (3h)",
        "taches": ["T15", "T16", "T17"],
        "objectif": "Dashboard complet avec carto + préconisations"
    },
    "J2_fin": {
        "heures": "16h00 - 18h00 (2h)",
        "taches": ["T18", "T19", "T20"],
        "objectif": "Rapport + pitch prêts pour la soutenance"
    },
}


#
# GESTIONNAIRE D'ÉTAT
#
class ProjectState:
    """Gère la persistance de l'état du projet en JSON."""

    def __init__(self):
        self.state = self._load()

    def _load(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {"tasks": {}, "started_at": datetime.now().isoformat()}

    def save(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def get_task_status(self, task_id: str) -> str:
        return self.state["tasks"].get(task_id, {}).get("status", "todo")

    def set_task_status(self, task_id: str, status: str):
        if task_id not in self.state["tasks"]:
            self.state["tasks"][task_id] = {}
        self.state["tasks"][task_id]["status"] = status
        self.state["tasks"][task_id]["updated_at"] = datetime.now().isoformat()
        self.save()

    def get_done_count(self) -> int:
        return sum(1 for t in self.state["tasks"].values() if t.get("status") == "done")

    def get_in_progress(self) -> List[str]:
        return [k for k, v in self.state["tasks"].items() if v.get("status") == "in_progress"]


#
# COMMANDES CLI
#
def cmd_status(state: ProjectState):
    """Tableau de bord projet complet."""
    done = state.get_done_count()
    total = len(TASKS)
    pct = done / total * 100

    print()
    if HAS_RICH:
        console.print(Panel.fit(
            f"[bold #6c5ce7] HACKATHON #26 — Changement Climatique[/]\n"
            f"[dim]Sup²Vinci · 16 & 17 Mars 2026[/]",
            border_style="#6c5ce7"
        ))

        # Barre de progression globale
        bar = "" * int(pct / 5) + "" * (20 - int(pct / 5))
        color = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"
        console.print(f"\n[{color}]Progression : [{bar}] {done}/{total} tâches ({pct:.0f}%)[/]")

        # Résumé par étape
        etapes = {}
        for tid, t in TASKS.items():
            etape = t["etape"]
            if etape not in etapes:
                etapes[etape] = {"total": 0, "done": 0}
            etapes[etape]["total"] += 1
            if state.get_task_status(tid) == "done":
                etapes[etape]["done"] += 1

        table = Table(title="\n Avancement par étape", box=box.ROUNDED, show_header=True)
        table.add_column("Étape", style="cyan", min_width=30)
        table.add_column("Fait", justify="center")
        table.add_column("Total", justify="center")
        table.add_column("Progression", min_width=20)

        for etape, counts in etapes.items():
            pct_e = counts["done"] / counts["total"] * 100
            bar_e = "" * int(pct_e / 10) + "" * (10 - int(pct_e / 10))
            color_e = "green" if pct_e == 100 else "yellow" if pct_e >= 50 else "red"
            table.add_row(
                etape,
                str(counts["done"]),
                str(counts["total"]),
                f"[{color_e}]{bar_e} {pct_e:.0f}%[/]",
            )
        console.print(table)

        # Planning
        console.print("\n[bold]  Planning suggéré :[/]")
        for slot_name, slot in PLANNING.items():
            done_count = sum(1 for t in slot["taches"] if state.get_task_status(t) == "done")
            slot_total = len(slot["taches"])
            icon = "" if done_count == slot_total else "" if done_count > 0 else ""
            console.print(
                f"  {icon} [cyan]{slot_name.replace('_', ' ').upper():12}[/] "
                f"{slot['heures']} — {slot['objectif']}"
            )
    else:
        print(f"Progression : {done}/{total} ({pct:.0f}%)")


def cmd_tasks(state: ProjectState, filtre_etape: str = None):
    """Liste toutes les tâches avec leur statut."""
    if HAS_RICH:
        table = Table(title=" Toutes les tâches", box=box.SIMPLE)
        table.add_column("ID", style="bold", width=5)
        table.add_column("Étape", style="cyan", width=20)
        table.add_column("Titre", width=45)
        table.add_column("Rôle", width=12)
        table.add_column("Prio", width=8)
        table.add_column("H", width=5, justify="right")
        table.add_column("Statut", width=12)

    for tid, task in TASKS.items():
        if filtre_etape and filtre_etape.lower() not in task["etape"].lower():
            continue

        status = state.get_task_status(tid)
        status_display = {
            "done":        " Fait",
            "in_progress": " En cours",
            "blocked":     " Bloqué",
            "todo":        " À faire",
        }.get(status, " À faire")

        prio_color = {
            "critique": "red",
            "haute":    "yellow",
            "moyenne":  "green",
        }.get(task["priorite"], "white")

        if HAS_RICH:
            table.add_row(
                tid,
                task["etape"],
                task["titre"][:44],
                task["role"],
                f"[{prio_color}]{task['priorite']}[/]",
                str(task["duree_h"]),
                status_display,
            )
        else:
            print(f"[{tid}] {status_display} | {task['titre']}")

    if HAS_RICH:
        console.print(table)


def cmd_done(state: ProjectState, task_id: str):
    """Marque une tâche comme terminée."""
    task_id = task_id.upper()
    if task_id not in TASKS:
        print(f" Tâche '{task_id}' introuvable.")
        return
    state.set_task_status(task_id, "done")
    task = TASKS[task_id]
    if HAS_RICH:
        console.print(f"[green] Tâche {task_id} marquée comme terminée : {task['titre']}[/]")
    else:
        print(f" {task_id} terminé : {task['titre']}")


def cmd_next(state: ProjectState):
    """Affiche les prochaines tâches à traiter."""
    if HAS_RICH:
        console.print("\n[bold] Prochaines tâches recommandées :[/]\n")

    priorite_order = {"critique": 0, "haute": 1, "moyenne": 2}
    candidats = []

    for tid, task in TASKS.items():
        if state.get_task_status(tid) == "done":
            continue
        # Vérifier que les dépendances sont satisfaites
        deps_ok = all(state.get_task_status(d) == "done" for d in task["dependances"])
        if deps_ok:
            candidats.append((priorite_order.get(task["priorite"], 3), tid, task))

    candidats.sort(key=lambda x: x[0])

    for i, (_, tid, task) in enumerate(candidats[:5]):
        prio_icon = "" if task["priorite"] == "critique" else "" if task["priorite"] == "haute" else ""
        if HAS_RICH:
            console.print(Panel(
                f"[bold]{task['titre']}[/]\n"
                f"[dim]Étape : {task['etape']} | Rôle : {task['role']} | ~{task['duree_h']}h[/]\n\n"
                f"[cyan]Livrable :[/] {task['livrable']}\n"
                f"[yellow] Conseil :[/] {task['conseils']}",
                title=f"{prio_icon} [{tid}] {task['priorite'].upper()}",
                border_style="blue" if i == 0 else "dim",
            ))
        else:
            print(f"[{tid}] {task['titre']} — {task['etape']}")

    if not candidats:
        if HAS_RICH:
            console.print("[bold green] Toutes les tâches sont terminées ![/]")


def cmd_check(state: ProjectState):
    """Vérifie l'existence des fichiers clés du projet."""
    checks = {
        "config/settings.py":                          ROOT / "config/settings.py",
        "src/data_loader.py":                          ROOT / "src/data_loader.py",
        "src/ingestion/pipeline.py":                   ROOT / "src/ingestion/pipeline.py",
        "src/ingestion/meteo_france.py":               ROOT / "src/ingestion/meteo_france.py",
        "src/ingestion/noaa_co2.py":                   ROOT / "src/ingestion/noaa_co2.py",
        "src/ingestion/citepa_secten.py":              ROOT / "src/ingestion/citepa_secten.py",
        "src/processing/cleaner.py":                   ROOT / "src/processing/cleaner.py",
        "src/processing/transformer.py":               ROOT / "src/processing/transformer.py",
        "src/processing/features.py":                  ROOT / "src/processing/features.py",
        "src/models/all_models.py":                    ROOT / "src/models/all_models.py",
        "src/models/model_comparison.py":              ROOT / "src/models/model_comparison.py",
        "src/recommendations/citizen_actions.py":      ROOT / "src/recommendations/citizen_actions.py",
        "web/tabs/__init__.py":                        ROOT / "web/tabs/__init__.py",
        "tests/test_pipeline.py":                      ROOT / "tests/test_pipeline.py",
        "scripts/run_model.py":                        ROOT / "scripts/run_model.py",
        "requirements.txt":                            ROOT / "requirements.txt",
        "Makefile":                                    ROOT / "Makefile",
        "[données] data/raw/meteofrance/":             ROOT / "data/raw/meteofrance",
        "[données] data/processed/master_features":    ROOT / "data/processed/master_features.parquet",
    }

    if HAS_RICH:
        table = Table(title=" Vérification des fichiers", box=box.SIMPLE)
        table.add_column("Fichier", width=50)
        table.add_column("Statut", width=15)

    ok_count = 0
    for name, path in checks.items():
        exists = path.exists()
        if exists:
            ok_count += 1
        status = "[green] OK[/]" if exists else "[red] Manquant[/]"
        if HAS_RICH:
            table.add_row(name, status)
        else:
            print(f"{'' if exists else ''} {name}")

    if HAS_RICH:
        console.print(table)
        console.print(f"\n[bold]Score : {ok_count}/{len(checks)} fichiers présents[/]")

    # Recommandations si des fichiers manquent
    missing_data = not (ROOT / "data/processed/master_features.parquet").exists()
    if missing_data and HAS_RICH:
        console.print("\n[yellow] Le master dataset n'existe pas encore. Lancer : [bold]make all[/][/]")


def cmd_report(state: ProjectState):
    """Génère un rapport HTML de suivi du projet."""
    done = state.get_done_count()
    total = len(TASKS)

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport projet — Hackathon #26</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0e1117; color: #e0e0e0; margin: 40px; }}
  h1 {{ color: #6c5ce7; }} h2 {{ color: #a29bfe; border-bottom: 1px solid #333; padding-bottom: 8px; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
  .critique {{ background: #c0392b; }} .haute {{ background: #e67e22; }} .moyenne {{ background: #27ae60; }}
  .done {{ background: #27ae60; }} .todo {{ background: #636e72; }} .in_progress {{ background: #f39c12; }}
  table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
  th {{ background: #1a1a2e; padding: 10px; text-align: left; color: #a29bfe; }}
  td {{ padding: 9px; border-bottom: 1px solid #2d2d2d; }}
  tr:hover {{ background: #1a1a2e; }}
  .progress-bar {{ background: #2d2d2d; border-radius: 8px; height: 20px; }}
  .progress-fill {{ height: 20px; border-radius: 8px; background: linear-gradient(90deg, #6c5ce7, #a29bfe); }}
</style>
</head>
<body>
<h1> Hackathon #26 — Rapport de projet</h1>
<p>Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')} | Sup²Vinci</p>

<h2> Avancement global</h2>
<p>{done} / {total} tâches terminées ({done/total*100:.0f}%)</p>
<div class="progress-bar">
  <div class="progress-fill" style="width:{done/total*100}%"></div>
</div>

<h2> Toutes les tâches</h2>
<table>
<tr>
  <th>ID</th><th>Étape</th><th>Titre</th><th>Rôle</th>
  <th>Priorité</th><th>Durée</th><th>Statut</th>
</tr>
"""
    for tid, task in TASKS.items():
        status = state.get_task_status(tid)
        html += f"""<tr>
  <td><b>{tid}</b></td>
  <td>{task['etape']}</td>
  <td>{task['titre']}</td>
  <td>{task['role']}</td>
  <td><span class="badge {task['priorite']}">{task['priorite'].upper()}</span></td>
  <td>{task['duree_h']}h</td>
  <td><span class="badge {status}">{status.upper()}</span></td>
</tr>"""

    html += """</table>
<h2> Planning</h2><table>
<tr><th>Créneau</th><th>Horaires</th><th>Tâches</th><th>Objectif</th></tr>"""

    for slot_name, slot in PLANNING.items():
        html += f"""<tr>
  <td>{slot_name.replace('_', ' ').upper()}</td>
  <td>{slot['heures']}</td>
  <td>{', '.join(slot['taches'])}</td>
  <td>{slot['objectif']}</td>
</tr>"""

    html += "</table></body></html>"

    out = ROOT / "reports" / "project_report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    if HAS_RICH:
        console.print(f"[green] Rapport généré : {out}[/]")
    else:
        print(f" Rapport : {out}")


#
# MAIN CLI
#
def main():
    state = ProjectState()
    args = sys.argv[1:]

    if not args:
        cmd_status(state)
        return

    cmd = args[0].lower()

    if cmd == "status":
        cmd_status(state)
    elif cmd == "tasks":
        filtre = args[1] if len(args) > 1 else None
        cmd_tasks(state, filtre)
    elif cmd == "done" and len(args) > 1:
        for tid in args[1:]:
            cmd_done(state, tid)
    elif cmd == "next":
        cmd_next(state)
    elif cmd == "check":
        cmd_check(state)
    elif cmd == "report":
        cmd_report(state)
    elif cmd == "reset":
        STATE_FILE.unlink(missing_ok=True)
        print(" État réinitialisé.")
    elif cmd == "help":
        print(__doc__)
    else:
        print(f"Commande inconnue : '{cmd}'")
        print("Usage : python scripts/project_manager.py [status|tasks|done <id>|next|check|report|reset]")


if __name__ == "__main__":
    main()
