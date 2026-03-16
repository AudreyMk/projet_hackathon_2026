"""
Collecte climatologique multi-sources — Orchestrateur
======================================================
Lance tous les pôles en séquence. Pour un pôle seul, exécutez
directement le fichier correspondant, par exemple :
    python collect_noaa.py
    python collect_datagouv.py
    python collect_vigicrues.py
"""

from datetime import datetime
from pathlib import Path

from helpers import setup_dirs
from collect_datagouv  import collect_datagouv
from collect_vigicrues import collect_vigicrues
from collect_noaa      import collect_noaa
from config import ROOT_DIR


def main():
    setup_dirs()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'═' * 64}")
    print(f"  Collecte climatologique multi-sources — {ts}")
    print(f"{'═' * 64}")

    all_results: dict[str, Path] = {}

    all_results.update(collect_datagouv())

    p = collect_vigicrues()
    if p:
        all_results["vigicrues"] = p

    all_results.update(collect_noaa())

    # ── Récapitulatif en arbre ─────────────────────────────────────────────────
    print(f"\n{'═' * 64}")
    print("  RÉCAPITULATIF — fichiers produits")
    print(f"{'═' * 64}")
    print(f"\n  📁 {ROOT_DIR}/")

    if all_results:
        by_pole: dict[str, list[Path]] = {}
        for path in all_results.values():
            by_pole.setdefault(path.parent.name, []).append(path)

        for pole in sorted(by_pole):
            print(f"  ├── {pole}/")
            paths = sorted(by_pole[pole])
            for i, p in enumerate(paths):
                size_mb = p.stat().st_size / 1_048_576
                branch  = "└──" if i == len(paths) - 1 else "├──"
                print(f"  │   {branch} ✅  {p.name:<40} {size_mb:>6.2f} Mo")
    else:
        print("  └── (aucun fichier produit)")

    print(f"\n  ⚠️  Sources à traiter manuellement :")
    manual = [
        ("DRIAS-Climat",   "https://www.drias-climat.fr/                   portail interactif"),
        ("CITEPA Secten",  "https://www.citepa.org/                        PDF / Excel"),
        ("INSEE 8654458",  "https://www.insee.fr/fr/statistiques/8654458"),
        ("SDES empreinte", "https://statistiques.developpement-durable.gouv.fr/empreinte-carbone-2"),
        ("GéoRisques",     "https://www.georisques.gouv.fr/                WMS/WFS carto"),
    ]
    for name, url in manual:
        print(f"     – {name:<18}  {url}")
    print()


if __name__ == "__main__":
    main()
