"""
src/data_loader.py
==================
Chargement et transformation des données réelles :
  - data/raw/avant_1960.csv  + data/raw/apres_1960.csv  (Météo France mensuel)
  - data/raw/vigigrues.csv   (niveaux d'eau temps réel)

Produit les DataFrames consommés par le dashboard.
Compatible avec le reste du template Hackathon #26.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from loguru import logger


# ── Chemins ────────────────────────────────────────────────────────────────
# src/data_loader.py est dans src/ — la racine projet est un niveau au-dessus
ROOT_DIR  = Path(__file__).parent.parent
DATA_RAW  = ROOT_DIR / "data" / "raw"
DATA_PROC = ROOT_DIR / "data" / "processed"
DATA_PROC.mkdir(parents=True, exist_ok=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║  MÉTÉO FRANCE — données mensuelle par station               ║
# ╚══════════════════════════════════════════════════════════════╝

METEO_COLS = {
    "NUM_POSTE":  "num_poste",
    "NOM_USUEL":  "nom_station",
    "LAT":        "lat",
    "LON":        "lon",
    "ALTI":       "altitude",
    "AAAAMM":     "aaaamm",
    "TX":         "tmax",
    "TN":         "tmin",
    "TM":         "tmoy",
    "TMM":        "tmoy_mensuelle",
    "NBJTX30":    "nb_jours_tx30",
    "NBJTX35":    "nb_jours_tx35",
    "RR":         "precip_mm",
    "ETP":        "etp",
    "ANNEE":      "annee",
    "MOIS":       "mois",
}

# Colonnes numériques à convertir (les valeurs manquantes arrivent comme str vides)
NUMERIC_COLS = [
    "tmax", "tmin", "tmoy", "tmoy_mensuelle",
    "nb_jours_tx30", "nb_jours_tx35",
    "precip_mm", "etp", "lat", "lon", "altitude",
]


def _read_meteo_csv(path: Path) -> pd.DataFrame:
    """Lit un CSV Météo France en gérant les séparateurs et types."""
    df = pd.read_csv(
        path,
        sep=",",
        dtype=str,
        encoding="utf-8",
        low_memory=False,
    )
    # Renommer uniquement les colonnes présentes
    rename_map = {k: v for k, v in METEO_COLS.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "annee" in df.columns:
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce").astype("Int64")
    if "mois" in df.columns:
        df["mois"] = pd.to_numeric(df["mois"], errors="coerce").astype("Int64")

    return df


def load_meteo(
    avant_path:  Path | None = None,
    apres_path:  Path | None = None,
) -> pd.DataFrame:
    """
    Fusionne avant_1960.csv et apres_1960.csv en un seul DataFrame mensuel.

    Colonnes clés produites :
      annee, mois, nom_station, lat, lon, tmax, tmin, tmoy,
      tmoy_mensuelle, nb_jours_tx30, nb_jours_tx35, precip_mm, etp
    """
    avant_path = avant_path or DATA_RAW / "avant_1960.csv"
    apres_path = apres_path or DATA_RAW / "apres_1960.csv"

    frames: list[pd.DataFrame] = []

    for path, label in [(avant_path, "avant_1960"), (apres_path, "apres_1960")]:
        if path.exists():
            logger.info(f"📂 Lecture {label} ({path.name})…")
            df = _read_meteo_csv(path)
            frames.append(df)
            logger.success(f"   ✅ {len(df):,} lignes chargées")
        else:
            logger.warning(f"   ⚠️  {path} introuvable — ignoré")

    if not frames:
        logger.error("Aucun fichier météo trouvé. Retour DataFrame vide.")
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    # ── Déduplication et tri ───────────────────────────────────────────
    sort_cols = [c for c in ["num_poste", "annee", "mois"] if c in df_all.columns]
    if sort_cols:
        df_all = df_all.sort_values(sort_cols).drop_duplicates(subset=sort_cols)

    logger.info(f"📊 Données météo fusionnées : {len(df_all):,} lignes, "
                f"{df_all['annee'].min()}–{df_all['annee'].max()}")

    # ── Sauvegarde processed ───────────────────────────────────────────
    out = DATA_PROC / "meteo_mensuel.parquet"
    df_all.to_parquet(out, index=False)
    logger.info(f"💾 Sauvegardé → {out}")

    return df_all


# ╔══════════════════════════════════════════════════════════════╗
# ║  AGRÉGATION ANNUELLE  (pour les graphiques historiques)     ║
# ╚══════════════════════════════════════════════════════════════╝

def build_annual_features(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Agrège les données mensuelles à l'échelle annuelle (moyenne nationale).

    Colonnes produites :
      annee, temp_moy_c, tmax_moy_c, tmin_moy_c,
      nb_jours_tx30, precip_mm, anomalie_temp_c, nb_stations
    """
    if df_monthly.empty:
        return _fallback_annual()

    # ── Étape 1 : agréger les 12 mois → valeur annuelle PAR STATION ───
    # nb_jours_tx30 et precip_mm sont des cumuls YTD dans Météo France → on prend le max (= valeur décembre)
    # Les températures se moyennent.
    cumul_cols = [c for c in ["nb_jours_tx30", "nb_jours_tx35", "precip_mm"] if c in df_monthly.columns]
    mean_cols  = [c for c in ["tmoy", "tmax", "tmin"] if c in df_monthly.columns]

    if not mean_cols and not cumul_cols:
        return _fallback_annual()

    agg_station: dict[str, tuple] = {}
    for col in mean_cols:
        agg_station[col] = (col, "mean")
    for col in cumul_cols:
        agg_station[col] = (col, "sum")   # valeur mensuelle brute → sum = total annuel

    group_st = [c for c in ["num_poste", "annee"] if c in df_monthly.columns]
    if "annee" not in group_st:
        return _fallback_annual()

    df_by_station = (
        df_monthly
        .dropna(subset=["annee"])
        .groupby(group_st, as_index=False)
        .agg(**agg_station)
    )

    # ── Étape 2 : moyenne nationale (entre stations) par année ────────
    agg: dict[str, tuple] = {}
    for col in mean_cols:
        agg[col] = (col, "mean")
    for col in cumul_cols:
        agg[col] = (col, "mean")   # moyenne des stations = représentatif national

    df_ann = (
        df_by_station
        .groupby("annee", as_index=False)
        .agg(**agg)
    )

    # Renommages propres
    rename = {
        "tmoy": "temp_moy_c",
        "tmax": "tmax_moy_c",
        "tmin": "tmin_moy_c",
    }
    df_ann = df_ann.rename(columns={k: v for k, v in rename.items() if k in df_ann.columns})
    df_ann["annee"] = df_ann["annee"].astype(int)

    # ── Anomalie par rapport à la normale 1961-1990 ────────────────
    if "tmoy" in df_by_station.columns and "num_poste" in df_by_station.columns:
        ref_period = df_by_station[df_by_station["annee"].between(1961, 1990)]

        ref_counts = ref_period.groupby("num_poste")["tmoy"].count()
        stations_with_ref = ref_counts[ref_counts >= 5].index

        ref_per_station = (
            ref_period[ref_period["num_poste"].isin(stations_with_ref)]
            .groupby("num_poste")["tmoy"]
            .mean()
        )

        df_by_station["ref_station"] = df_by_station["num_poste"].map(ref_per_station)
        df_by_station["anomalie"] = df_by_station["tmoy"] - df_by_station["ref_station"]

        anom_ann = (
            df_by_station.dropna(subset=["anomalie"])
            .groupby("annee", as_index=False)["anomalie"]
            .mean()
            .rename(columns={"anomalie": "anomalie_temp_c"})
        )
        anom_ann["anomalie_temp_c"] = anom_ann["anomalie_temp_c"].round(3)
        df_ann = df_ann.merge(anom_ann, on="annee", how="left")
    elif "temp_moy_c" in df_ann.columns:
        ref_mask = df_ann["annee"].between(1961, 1990)
        ref_temp = df_ann.loc[ref_mask, "temp_moy_c"].mean()
        df_ann["anomalie_temp_c"] = (df_ann["temp_moy_c"] - ref_temp).round(3) if pd.notna(ref_temp) else np.nan

    # Cap à 2025 : l'année 2026 est incomplète et fausse les tendances
    df_ann = df_ann[df_ann["annee"] <= 2025]

    df_ann = df_ann.sort_values("annee").reset_index(drop=True)
    logger.info(f"📅 Agrégation annuelle : {len(df_ann)} années, "
                f"{df_ann['annee'].min()}–{df_ann['annee'].max()}")
    return df_ann


def _fallback_annual() -> pd.DataFrame:
    """Données annuelles synthétiques si les CSV sont absents."""
    np.random.seed(42)
    years = list(range(1900, 2025))
    n = len(years)
    trend = np.linspace(0, 1.7, n)
    noise = np.random.normal(0, 0.25, n)
    baseline = 12.0
    temp = baseline + trend + noise
    ref = temp[61:90].mean()  # 1961-1990
    return pd.DataFrame({
        "annee": years,
        "temp_moy_c": temp.round(2),
        "tmax_moy_c": (temp + 6).round(2),
        "tmin_moy_c": (temp - 6).round(2),
        "anomalie_temp_c": (temp - ref).round(3),
        "nb_jours_tx30": (10 + np.linspace(0, 20, n) + np.random.poisson(2, n)).clip(0).astype(int),
        "precip_mm": (700 + np.random.normal(0, 50, n)).round(1),
        "nb_stations": [1] * n,
        "ref_1961_1990": round(ref, 2),
    })


# ╔══════════════════════════════════════════════════════════════╗
# ║  LISTE DES STATIONS  (pour la carte et les filtres)         ║
# ╚══════════════════════════════════════════════════════════════╝

def build_stations_df(df_monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Retourne un DataFrame des stations uniques avec leur position GPS
    et les statistiques clés (température moyenne, précip totale).
    """
    if df_monthly.empty or "nom_station" not in df_monthly.columns:
        return pd.DataFrame()

    required = {"nom_station", "lat", "lon"}
    if not required.issubset(df_monthly.columns):
        return pd.DataFrame()

    agg_map: dict[str, tuple] = {
        "lat": ("lat", "first"),
        "lon": ("lon", "first"),
        "n_obs": ("annee", "count"),
    }
    if "tmoy" in df_monthly.columns:
        agg_map["temp_moy_c"] = ("tmoy", "mean")
    if "precip_mm" in df_monthly.columns:
        agg_map["precip_moy_mm"] = ("precip_mm", "mean")
    if "annee" in df_monthly.columns:
        agg_map["annee_min"] = ("annee", "min")
        agg_map["annee_max"] = ("annee", "max")

    df_st = (
        df_monthly
        .dropna(subset=["lat", "lon"])
        .groupby("nom_station", as_index=False)
        .agg(**agg_map)
    )
    for col in ["temp_moy_c", "precip_moy_mm"]:
        if col in df_st.columns:
            df_st[col] = df_st[col].round(2)

    logger.info(f"📍 {len(df_st)} stations extraites")
    return df_st


# ╔══════════════════════════════════════════════════════════════╗
# ║  VIGIGRUES — niveaux d'eau temps réel                       ║
# ╚══════════════════════════════════════════════════════════════╝

def load_vigigrues(path: Path | None = None) -> pd.DataFrame:
    """
    Charge vigigrues.csv (séparateur tabulation).

    Colonnes attendues : CdStation, DateObs, Valeur, Qualif, Continuite
    Colonnes produites : station, datetime_utc, hauteur_mm, date, heure
    """
    path = path or DATA_RAW / "vigigrues.csv"

    if not path.exists():
        logger.warning(f"⚠️  {path} introuvable — DataFrame vide retourné")
        return pd.DataFrame()

    # Détection automatique du séparateur : \t, ; ou ,
    df = None
    for sep in ["\t", ";", ","]:
        try:
            tmp = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8", nrows=2)
            if len(tmp.columns) > 1:
                df = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8")
                logger.info(f"Séparateur vigigrues détecté : {repr(sep)}")
                break
        except Exception:
            continue
    if df is None:
        logger.error("Impossible de lire vigigrues.csv avec les séparateurs \\t ; ,")
        return pd.DataFrame()

    # Nettoyage des noms de colonnes (espaces, BOM, caractères invisibles)
    df.columns = df.columns.str.strip().str.replace(r"[\ufeff\u200b]", "", regex=True)
    logger.info(f"Colonnes vigigrues brutes : {list(df.columns)}")

    # Renommage flexible : matching insensible à la casse et aux espaces
    col_map = {}
    for col in df.columns:
        col_clean = col.strip().lower().replace(" ", "").replace("_", "")
        if col_clean in ("cdstation", "codestation", "station"):
            col_map[col] = "station"
        elif col_clean in ("dateobs", "date", "datetime", "dateheure"):
            col_map[col] = "datetime_str"
        elif col_clean in ("valeur", "value", "hauteur", "niveau"):
            col_map[col] = "hauteur_mm"
        elif col_clean in ("qualif", "qualite", "quality"):
            col_map[col] = "qualif"
        elif col_clean in ("continuite", "continuity"):
            col_map[col] = "continuite"
    df = df.rename(columns=col_map)
    logger.info(f"Colonnes après renommage : {list(df.columns)}")

    if "hauteur_mm" in df.columns:
        df["hauteur_mm"] = pd.to_numeric(df["hauteur_mm"].str.strip(), errors="coerce")

    if "datetime_str" in df.columns:
        df["datetime_str"] = df["datetime_str"].str.strip()
        df["datetime_utc"] = pd.to_datetime(df["datetime_str"], utc=True, errors="coerce")
        df["date"]  = df["datetime_utc"].dt.date
        df["heure"] = df["datetime_utc"].dt.strftime("%H:%M")

    if "station" in df.columns:
        df["station"] = df["station"].str.strip()

    if "hauteur_mm" in df.columns:
        df = df.dropna(subset=["hauteur_mm"])
    df = df.sort_values("datetime_utc").reset_index(drop=True) if "datetime_utc" in df.columns else df

    logger.info(f"🌊 Vigigrues : {len(df):,} mesures, "
                f"{df['station'].nunique() if 'station' in df.columns else '?'} station(s)")
    return df


# ╔══════════════════════════════════════════════════════════════╗
# ║  POINT D'ENTRÉE UNIQUE (utilisé par le dashboard)           ║
# ╚══════════════════════════════════════════════════════════════╝

def _load_annual_parquet() -> pd.DataFrame:
    """
    Charge temperatures_annuelles.parquet si disponible et le met en forme
    pour que _build_hist() dans app.py puisse mapper les colonnes correctement.

    Colonnes source  → colonnes cibles attendues par _build_hist() :
      temp_anomalie_c → anomalie_temp_c
      jours_chauds_30 → nb_jours_tx30
    """
    parquet_path = DATA_RAW / "meteofrance" / "temperatures_annuelles.parquet"
    if not parquet_path.exists():
        return pd.DataFrame()

    df = pd.read_parquet(parquet_path)
    rename = {
        "temp_anomalie_c": "anomalie_temp_c",
        "jours_chauds_30": "nb_jours_tx30",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df = df.sort_values("annee").reset_index(drop=True)
    logger.info(f"📦 Parquet météo chargé : {len(df)} années "
                f"({df['annee'].min()}–{df['annee'].max()})")
    return df


def load_all(
    avant_path:    Path | None = None,
    apres_path:    Path | None = None,
    vigigrues_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Charge et transforme toutes les sources.

    Retourne un dict avec les clés :
      'meteo_monthly'  — données mensuelles brutes
      'meteo_annual'   — agrégat annuel (température, précip, anomalies)
      'stations'       — liste des stations GPS
      'vigigrues'      — niveaux d'eau vigigrues
    """
    df_monthly  = load_meteo(avant_path, apres_path)
    df_annual   = build_annual_features(df_monthly)

    # Si le pipeline CSV n'a rien produit (fichiers absents), utiliser le parquet existant
    if df_monthly.empty:
        parquet_annual = _load_annual_parquet()
        if not parquet_annual.empty:
            df_annual = parquet_annual
            logger.info("✅ Données annuelles chargées depuis temperatures_annuelles.parquet")

    df_stations = build_stations_df(df_monthly)
    df_vigi     = load_vigigrues(vigigrues_path)

    return {
        "meteo_monthly": df_monthly,
        "meteo_annual":  df_annual,
        "stations":      df_stations,
        "vigigrues":     df_vigi,
    }


# ── Test rapide en ligne de commande ───────────────────────────────────────
if __name__ == "__main__":
    data = load_all()
    for key, df in data.items():
        print(f"  {key:20s} → {len(df):>8,} lignes  |  colonnes : {list(df.columns)[:6]}")
