"""
Listing des stations Vigicrues et Refmar disponibles pour la France
====================================================================
Exécution :
    python list_stations.py

Produit deux fichiers dans le répertoire courant :
    stations_vigicrues.csv   — stations hydrométriques (Hub'Eau)
    stations_refmar.csv      — marégraphes SHOM/Refmar
"""

import requests
import pandas as pd

# ═══════════════════════════════════════════════════════════════════════════════
#  VIGICRUES — via Hub'Eau v2
# ═══════════════════════════════════════════════════════════════════════════════

def list_vigicrues():
    print("\n══════════════════════════════════════════════════════════════")
    print("  STATIONS VIGICRUES (Hub'Eau — réseau hydrométrique France)")
    print("══════════════════════════════════════════════════════════════")

    all_rows = []
    page     = 1
    size     = 1000
    url      = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/referentiel/stations"

    while True:
        params = {
            "size":   size,
            "page":   page,
            "format": "json",
            "fields": "code_station,libelle_station,libelle_cours_eau,"
                      "libelle_departement,code_departement,"
                      "longitude_station,latitude_station",
        }
        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            data  = resp.json()
            items = data.get("data", [])
            if not items:
                break
            all_rows.extend(items)
            count = data.get("count", 0)
            print(f"  Page {page} — {len(all_rows)}/{count} stations chargées")
            if len(all_rows) >= count:
                break
            page += 1
        except Exception as e:
            print(f"  ❌ Erreur : {e}")
            break

    if not all_rows:
        print("  Aucune station récupérée.")
        return

    df = pd.DataFrame(all_rows).rename(columns={
        "code_station":       "Code",
        "libelle_station":    "Nom",
        "libelle_cours_eau":  "Cours_deau",
        "libelle_departement":"Departement",
        "code_departement":   "Num_dept",
        "longitude_station":  "Longitude",
        "latitude_station":   "Latitude",
    })
    df.sort_values(["Num_dept", "Nom"], inplace=True)
    df.to_csv("stations_vigicrues.csv", index=False, encoding="utf-8-sig", sep=";")

    print(f"\n  ✅ {len(df)} stations sauvegardées → stations_vigicrues.csv")
    print(f"\n  Aperçu (10 premières) :")
    print(df[["Code", "Nom", "Cours_deau", "Departement"]].head(10).to_string(index=False))

    # Résumé par département
    print(f"\n  Stations par département (top 10) :")
    print(df.groupby("Departement").size().sort_values(ascending=False)
            .head(10).to_string())


# ═══════════════════════════════════════════════════════════════════════════════
#  REFMAR — via API SHOM
# ═══════════════════════════════════════════════════════════════════════════════

def list_refmar():
    print("\n══════════════════════════════════════════════════════════════")
    print("  STATIONS REFMAR (SHOM — marégraphes France)")
    print("══════════════════════════════════════════════════════════════")

    # Endpoint catalogue des stations Refmar
    url = "https://services.data.shom.fr/support/fr/services/refmar/stations"

    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ❌ Erreur API SHOM : {e}")
        _list_refmar_fallback()
        return

    # Le format exact dépend de la version de l'API — on tente les deux formes
    stations = data if isinstance(data, list) else data.get("stations", data.get("data", []))

    if not stations:
        print("  ⚠️  Réponse vide, tentative via le catalogue alternatif...")
        _list_refmar_fallback()
        return

    rows = []
    for s in stations:
        rows.append({
            "Code":      s.get("code") or s.get("id") or s.get("codeStation"),
            "Nom":       s.get("name") or s.get("nom") or s.get("libelle"),
            "Pays":      s.get("country") or s.get("pays", "France"),
            "Longitude": s.get("longitude") or s.get("lon"),
            "Latitude":  s.get("latitude") or s.get("lat"),
            "Actif":     s.get("active") or s.get("actif", True),
        })

    df = pd.DataFrame(rows)
    df_fr = df[df["Pays"].str.upper().str.contains("FRANCE|FR", na=False)] \
            if "Pays" in df.columns else df
    df_fr.to_csv("stations_refmar.csv", index=False, encoding="utf-8-sig", sep=";")

    print(f"  ✅ {len(df_fr)} stations françaises sauvegardées → stations_refmar.csv")
    print(f"\n  Liste complète :")
    print(df_fr[["Code", "Nom", "Latitude", "Longitude"]].to_string(index=False))


def _list_refmar_fallback():
    """
    Liste de référence des principales stations Refmar françaises.
    Source : https://data.shom.fr/refmar  (consultation manuelle)
    Utilisez ces codes dans REFMAR_STATIONS de config.py.
    """
    stations = [
        # Manche / Atlantique Nord
        ("DUNKERQUE",       "Dunkerque",            "51.047", "2.367"),
        ("CALAIS",          "Calais",                "50.971", "1.870"),
        ("BOULOGNE",        "Boulogne-sur-Mer",      "50.726", "1.613"),
        ("DIEPPE",          "Dieppe",                "49.933", "1.083"),
        ("LE_HAVRE",        "Le Havre",              "49.488", "0.107"),
        ("CHERBOURG",       "Cherbourg",             "49.648", "-1.623"),
        ("ST_MALO",         "Saint-Malo",            "48.637", "-2.022"),
        ("BREST",           "Brest",                 "48.383", "-4.495"),
        # Atlantique
        ("SAINT_NAZAIRE",   "Saint-Nazaire",         "47.267", "-2.200"),
        ("LA_ROCHELLE",     "La Rochelle",           "46.155", "-1.151"),
        ("LE_VERDON",       "Le Verdon-sur-Mer",     "45.540", "-1.062"),
        ("BORDEAUX",        "Bordeaux",              "44.854", "-0.556"),
        ("ARCACHON",        "Arcachon (Eyrac)",      "44.663", "-1.165"),
        ("BAYONNE",         "Bayonne",               "43.493", "-1.475"),
        # Méditerranée
        ("MARSEILLE",       "Marseille",             "43.296", "5.352"),
        ("TOULON",          "Toulon",                "43.124", "5.934"),
        ("NICE",            "Nice",                  "43.695", "7.267"),
        ("SETE",            "Sète",                  "43.401", "3.700"),
        ("PORT_VENDRES",    "Port-Vendres",          "42.520", "3.112"),
        # DOM
        ("MARTINIQUE_FDF",  "Fort-de-France (Martinique)", "14.601", "-61.073"),
        ("GUADELOUPE_PaP",  "Pointe-à-Pitre (Guadeloupe)", "16.236", "-61.529"),
        ("GUYANE_DKR",      "Dégrad des Cannes (Guyane)",  "4.851",  "-52.264"),
        ("REUNION_PRT",     "Port-Réunion (La Réunion)",   "-20.930","55.290"),
        ("MAYOTTE_DZA",     "Dzaoudzi (Mayotte)",          "-12.785","45.258"),
    ]

    df = pd.DataFrame(stations, columns=["Code", "Nom", "Latitude", "Longitude"])
    df.to_csv("stations_refmar.csv", index=False, encoding="utf-8-sig", sep=";")
    print("  ℹ️  API SHOM non accessible — liste de référence statique utilisée.")
    print(f"  ✅ {len(df)} stations sauvegardées → stations_refmar.csv")
    print(f"\n  Liste :")
    print(df.to_string(index=False))


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    list_vigicrues()
    list_refmar()
    print("\n  Fichiers produits : stations_vigicrues.csv  /  stations_refmar.csv\n")
