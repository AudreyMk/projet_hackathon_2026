"""
pipeline_climat.py
==================
Pipeline climatique — France entière
Etape 1 : Collecte des données (DataCollector)

Gestion automatique des formats :
    - CSV texte brut
    - ZIP  → extrait le premier CSV trouvé
    - GZ   → décompresse vers CSV
"""

import gzip
import io
import zipfile
import requests
from dataclasses import dataclass
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION GLOBALE
# ─────────────────────────────────────────────────────────────────────────────

RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
FINAL_DIR     = Path("data/final")

# Magic bytes des formats compressés
MAGIC_ZIP = b"PK\x03\x04"
MAGIC_GZ  = b"\x1f\x8b"


# ─────────────────────────────────────────────────────────────────────────────
# DATASOURCE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DataSource:
    """
    Représente une source de données téléchargeable.

    Attributs :
        name        : identifiant court        ex: "co2_noaa"
        url         : URL de téléchargement    ex: "https://..."
        subfolder   : sous-dossier dans raw/   ex: "co2"
        filename    : nom du fichier local     ex: "co2_noaa.txt"
        description : label lisible pour logs  ex: "CO2 NOAA Mauna Loa"
    """
    name        : str
    url         : str
    subfolder   : str
    filename    : str
    description : str

    @property
    def raw_path(self) -> Path:
        """Chemin complet du fichier brut final (toujours un CSV ou TXT)."""
        return RAW_DIR / self.subfolder / self.filename


# ─────────────────────────────────────────────────────────────────────────────
# LISTE DES SOURCES
# Pour ajouter une source : copier un bloc DataSource et l'ajouter ici
# ─────────────────────────────────────────────────────────────────────────────

SOURCES: list[DataSource] = [

    DataSource(
        name        = "co2_noaa",
        url         = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_mlo.csv",
        subfolder   = "co2",
        filename    = "co2_annmean_mlo.csv",
        description = "Concentrations CO2 atmosphérique annuelles — NOAA Mauna Loa",
    ),
        DataSource(
        name        = "co2_noaa",
        url         = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv",
        subfolder   = "co2",
        filename    = "co2_mm_mlo.csv",
        description = "Concentrations CO2 atmosphérique mensuelles — NOAA Mauna Loa",
    ),

    DataSource(
        name        = "temp_dept",
        url         = "https://www.data.gouv.fr/api/1/datasets/r/c04d778f-872a-4f41-a3ac-40a0477b4b78",
        subfolder   = "meteo",
        filename    = "temp_dept.csv",
        description = "Températures départementales — Météo France",
    ),

    DataSource(
        name        = "temp_quotidienne",
        url         = "https://www.data.gouv.fr/api/1/datasets/r/24169144-35d2-4866-a3c3-44b2d916525c",
        subfolder   = "meteo",
        filename    = "temp_quotidienne.csv",
        description = "Températures quotidiennes — Météo France",
    ),

    DataSource(
        name        = "precipitations",
        url         = "https://www.data.gouv.fr/api/1/datasets/r/5c2d02bc-da05-434a-a274-ff4953f74e50",
        subfolder   = "meteo",
        filename    = "precipitations.csv",
        description = "Précipitations mensuelles — Météo France",
    ),

    DataSource(
        name        = "indicateurs_extremes",
        url         = "https://www.data.gouv.fr/api/1/datasets/r/f292971a-dd3c-4d76-9e52-c265e2f909a5",
        subfolder   = "meteo",
        filename    = "indicateurs_extremes.csv",
        description = "Indicateurs d'événements extrêmes — Météo France",
    ),

    DataSource(
        name        = "clim_dept",
        url         = "https://www.data.gouv.fr/api/1/datasets/r/7194000c-de92-4e00-b5a7-4456cb473ec9",
        subfolder   = "meteo",
        filename    = "clim_dept.csv",
        description = "Climatologie départementale — Météo France",
    ),

    DataSource(
        name        = "ges_annuel",
        url         = "https://www.data.gouv.fr/api/1/datasets/r/c4dc2289-2451-482c-a566-857ab34165a7",
        subfolder   = "ges",
        filename    = "ges_annuel.csv",
        description = "Émissions GES annuelles France — CITEPA/Secten",
    ),

    # DataSource(
    #     name        = "ma_source",
    #     url         = "https://mon-lien-direct.csv",
    #     subfolder   = "mon_dossier",
    #     filename    = "mon_fichier.csv",
    #     description = "Description lisible",
    # ),

    # ── Pour ajouter une nouvelle source, copier ce bloc ─────────────────────
    # DataSource(
    #     name        = "ma_source",
    #     url         = "https://mon-lien-direct.csv",
    #     subfolder   = "mon_dossier",
    #     filename    = "mon_fichier.csv",
    #     description = "Description lisible",
    # ),

]


# ─────────────────────────────────────────────────────────────────────────────
# CLASSE 1 : DATACOLLECTOR
# ─────────────────────────────────────────────────────────────────────────────

class DataCollector:
    """
    Télécharge toutes les sources déclarées dans SOURCES.

    Comportement :
        - Crée la structure de dossiers automatiquement
        - Télécharge chaque source (re-télécharge toujours)
        - Détecte et décompresse automatiquement ZIP et GZ
        - Affiche un rapport clair en fin de collecte
    """

    def __init__(self, sources: list[DataSource]):
        self.sources = sources
        self._create_folders()

    # ── Privé ─────────────────────────────────────────────────────────────────

    def _create_folders(self):
        """Crée toute la structure de dossiers du projet."""
        for source in self.sources:
            source.raw_path.parent.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        FINAL_DIR.mkdir(parents=True, exist_ok=True)
        print("Structure de dossiers créée\n")

    def _detect_format(self, content: bytes) -> str:
        """
        Détecte le format du fichier à partir de ses magic bytes.
        Retourne : 'zip' | 'gz' | 'text'
        """
        if content[:4] == MAGIC_ZIP:
            return "zip"
        if content[:2] == MAGIC_GZ:
            return "gz"
        return "text"

    def _extract_zip(self, content: bytes, dest_path: Path) -> bool:
        """
        Extrait le premier CSV trouvé dans un ZIP.
        Si plusieurs CSV, prend le plus gros (le plus probable d'être le bon).
        """
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            # Lister tous les fichiers dans le ZIP
            all_files = zf.namelist()
            print(f"    Contenu ZIP : {all_files}")

            # Chercher les CSV dans le ZIP
            csv_files = [f for f in all_files if f.lower().endswith(".csv")]

            if not csv_files:
                # Pas de CSV → prendre le premier fichier quand même
                target = all_files[0]
                print(f"    ⚠️  Pas de CSV dans le ZIP, extraction de : {target}")
            else:
                # Prendre le CSV le plus gros
                target = max(csv_files, key=lambda f: zf.getinfo(f).file_size)
                print(f"    📦 CSV extrait depuis ZIP : {target}")

            with zf.open(target) as f:
                dest_path.write_bytes(f.read())

        return True

    def _extract_gz(self, content: bytes, dest_path: Path) -> bool:
        """Décompresse un fichier GZ."""
        with gzip.open(io.BytesIO(content)) as f:
            dest_path.write_bytes(f.read())
        print(f"    📦 Fichier GZ décompressé → {dest_path.name}")
        return True

    def _save_content(self, content: bytes, source: DataSource) -> bool:
        """
        Détecte le format et sauvegarde le contenu correctement.
        Gère automatiquement ZIP, GZ, et texte brut.
        """
        fmt = self._detect_format(content)
        print(f"    Format détecté : {fmt.upper()}")

        if fmt == "zip":
            return self._extract_zip(content, source.raw_path)
        elif fmt == "gz":
            return self._extract_gz(content, source.raw_path)
        else:
            # Texte brut (CSV, TXT...) → sauvegarde directe
            source.raw_path.write_bytes(content)
            return True

    def _download(self, source: DataSource) -> bool:
        """
        Télécharge un fichier, détecte son format et le sauvegarde.
        Retourne True si succès, False sinon.
        """
        try:
            print(f"  ⏳ {source.description}")
            response = requests.get(source.url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            content = response.content
            self._save_content(content, source)

            size_kb = source.raw_path.stat().st_size // 1024
            print(f"  ✅ OK — {size_kb} Ko → {source.raw_path}")
            return True

        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout — {source.url}")
            return False
        except requests.exceptions.HTTPError as e:
            print(f"  ❌ Erreur HTTP {e.response.status_code} — {source.url}")
            return False
        except zipfile.BadZipFile:
            print(f"  ❌ Archive ZIP corrompue — {source.name}")
            return False
        except Exception as e:
            print(f"  ❌ Erreur inattendue — {e}")
            return False

    # ── Public ────────────────────────────────────────────────────────────────

    def collect_all(self) -> dict[str, bool]:
        """
        Télécharge toutes les sources.
        Retourne un dictionnaire {nom_source: True/False}.
        """
        print("=" * 60)
        print("ÉTAPE 1 — COLLECTE DES DONNÉES")
        print("=" * 60)

        results = {}
        for source in self.sources:
            results[source.name] = self._download(source)
            print()  # ligne vide entre chaque source

        # ── Rapport final ─────────────────────────────────────────────────────
        ok  = [name for name, success in results.items() if success]
        nok = [name for name, success in results.items() if not success]

        print("─" * 60)
        print(f"  ✅ Réussis  ({len(ok)})  : {', '.join(ok) if ok else '—'}")
        print(f"  ❌ Échoués  ({len(nok)}) : {', '.join(nok) if nok else '—'}")
        print("─" * 60)

        return results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN (temporaire — sera enrichi à chaque étape)
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  PIPELINE CLIMAT — FRANCE ENTIÈRE")
    print("=" * 60 + "\n")

    # Étape 1 : Collecte
    collector = DataCollector(sources=SOURCES)
    results   = collector.collect_all()


if __name__ == "__main__":
    main()