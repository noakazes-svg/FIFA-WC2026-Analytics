"""
run_daily_update.py
===================
FIFA World Cup 2026 — Daily automated update pipeline.

Detects newly completed matches, fetches results (ESPN API) and archive
weather (Open-Meteo), rebuilds all datasets, retrains models, refreshes
predictions, and generates a daily summary report.

Idempotent: running multiple times for the same day produces the same result.

Usage:
    python run_daily_update.py                    # process today + past 3 days
    python run_daily_update.py --date 2026-06-21  # process a specific date only
    python run_daily_update.py --dry-run          # show what would change, no writes
"""

import os, sys, math, time, logging, argparse, csv
import requests
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent
RAW      = ROOT / "data" / "raw"
PROC     = ROOT / "data" / "processed"
FINAL    = ROOT / "data" / "final"
EXT      = ROOT / "data" / "external"
PRED_DIR = ROOT / "data" / "predictions"
LOGS_DIR = ROOT / "logs"
REPORTS  = ROOT / "reports"

sys.path.insert(0, str(ROOT / "src"))
from scrapers.results_fetcher import fetch_results, find_match, normalize_team_name
from reporting.daily_summary  import generate as write_summary

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS  = (
    "temperature_2m,apparent_temperature,dew_point_2m,"
    "relative_humidity_2m,precipitation,rain,"
    "wind_speed_10m,wind_gusts_10m,cloud_cover,surface_pressure"
)

ELO = {
    "Argentina": 2020, "France": 2015, "England": 1990, "Brazil": 1985,
    "Portugal": 1975, "Spain": 1970, "Netherlands": 1955, "Germany": 1950,
    "Belgium": 1945, "Uruguay": 1935, "Colombia": 1920, "USA": 1900,
    "Morocco": 1895, "Mexico": 1890, "Croatia": 1880, "Japan": 1870,
    "Switzerland": 1865, "South Korea": 1840, "Australia": 1835,
    "Senegal": 1830, "Turkiye": 1820, "Norway": 1810, "Iran": 1805,
    "Ecuador": 1800, "Sweden": 1800, "Algeria": 1795, "Canada": 1790,
    "Austria": 1785, "Tunisia": 1780, "Ghana": 1760, "Ivory Coast": 1755,
    "Egypt": 1750, "Czechia": 1745, "Scotland": 1740, "Saudi Arabia": 1720,
    "Iraq": 1710, "Jordan": 1690, "Cape Verde": 1685, "South Africa": 1680,
    "DR Congo": 1675, "Haiti": 1660, "Panama": 1655, "New Zealand": 1640,
    "Paraguay": 1635, "Qatar": 1630, "Bosnia-Herzegovina": 1625,
    "Curacao": 1610, "Uzbekistan": 1600,
}

VENUE_TYPE = {
    "Estadio Azteca":            ("Open",    "CDMX",           "Mexico"),
    "Estadio Akron":             ("Open",    "Jalisco",         "Mexico"),
    "Estadio BBVA":              ("Open",    "Nuevo León",      "Mexico"),
    "NRG Stadium":               ("Covered", "Texas",           "USA"),
    "AT&T Stadium":              ("Covered", "Texas",           "USA"),
    "Mercedes-Benz Stadium":     ("Covered", "Georgia",         "USA"),
    "BC Place":                  ("Covered", "British Columbia","Canada"),
    "SoFi Stadium":              ("Partial", "California",      "USA"),
    "Lumen Field":               ("Partial", "Washington",      "USA"),
    "Hard Rock Stadium":         ("Open",    "Florida",         "USA"),
    "MetLife Stadium":           ("Open",    "New Jersey",      "USA"),
    "Gillette Stadium":          ("Open",    "Massachusetts",   "USA"),
    "Lincoln Financial Field":   ("Open",    "Pennsylvania",    "USA"),
    "Levi's Stadium":            ("Open",    "California",      "USA"),
    "Arrowhead Stadium":         ("Open",    "Missouri",        "USA"),
    "BMO Field":                 ("Open",    "Ontario",         "Canada"),
}

# ── Heat metric helpers ───────────────────────────────────────────────────────

def _heat_index(T, RH):
    T_f = T * 9/5 + 32
    if T_f < 80 or RH < 40:
        return round(T, 2)
    hi = (-42.379 + 2.04901523*T_f + 10.14333127*RH - 0.22475541*T_f*RH
          - 6.83783e-3*T_f**2 - 5.391553e-2*RH**2 + 1.22874e-3*T_f**2*RH
          + 8.5282e-4*T_f*RH**2 - 1.99e-6*T_f**2*RH**2)
    return round((hi - 32) * 5/9, 2)

def _wet_bulb(T, RH):
    return round(
        T * math.atan(0.151977 * (RH + 8.313659)**0.5)
        + math.atan(T + RH) - math.atan(RH - 1.676331)
        + 0.00391838 * RH**1.5 * math.atan(0.023101 * RH) - 4.686035, 2)

def _wbgt(T, RH):
    wb = _wet_bulb(T, RH)
    return round(0.7 * wb + 0.3 * T, 2)

def _cooling_break(wbgt_val):
    if wbgt_val is None:
        return None, None
    if wbgt_val >= 32:
        return 1, 2
    if wbgt_val >= 28:
        return 1, 1
    return 0, 0

def _bucket(val, low_max, high_min, labels=("Low", "Medium", "High")):
    if val is None:
        return None
    if val <= low_max:
        return labels[0]
    if val >= high_min:
        return labels[2]
    return labels[1]

def _poisson_over_25(lam):
    return round(1 - sum(math.exp(-lam) * lam**k / math.factorial(k) for k in range(3)), 3)

# ── Weather fetch ─────────────────────────────────────────────────────────────

def fetch_archive_weather(lat, lon, match_date, kickoff_hour, tz):
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": match_date, "end_date": match_date,
        "hourly": HOURLY_VARS, "timezone": tz,
    }
    try:
        r = requests.get(ARCHIVE_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        hours = data["hourly"]["time"]
        target = f"{match_date}T{int(kickoff_hour):02d}:00"
        idx = hours.index(target) if target in hours else min(int(kickoff_hour), len(hours)-1)
        return {k: data["hourly"][k][idx] for k in data["hourly"] if k != "time"}
    except Exception as e:
        log.warning(f"Archive weather fetch failed for {match_date} ({lat},{lon}): {e}")
        return None

def fetch_forecast_weather(lat, lon, match_date, kickoff_hour, tz):
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": match_date, "end_date": match_date,
        "hourly": HOURLY_VARS, "timezone": tz,
    }
    try:
        r = requests.get(FORECAST_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        hours = data["hourly"]["time"]
        target = f"{match_date}T{int(kickoff_hour):02d}:00"
        idx = hours.index(target) if target in hours else min(int(kickoff_hour), len(hours)-1)
        return {k: data["hourly"][k][idx] for k in data["hourly"] if k != "time"}
    except Exception as e:
        log.warning(f"Forecast weather fetch failed for {match_date} ({lat},{lon}): {e}")
        return None

def _build_weather_row(match_id, raw):
    """Turn raw Open-Meteo hourly dict into a weather_data.csv row."""
    if raw is None:
        return {"match_id": match_id}
    T   = raw.get("temperature_2m")
    RH  = raw.get("relative_humidity_2m")
    prec = raw.get("precipitation", 0) or 0
    rain = raw.get("rain", 0) or 0
    cloud = raw.get("cloud_cover", 0) or 0

    hi   = _heat_index(T, RH) if (T and RH) else None
    wb   = _wet_bulb(T, RH)   if (T and RH) else None
    wbgt = _wbgt(T, RH)       if (T and RH) else None
    cb_f, cb_c = _cooling_break(wbgt)

    if prec > 2:    cond = "Rain"
    elif prec > 0:  cond = "Light Rain"
    elif cloud > 80: cond = "Overcast"
    elif cloud > 40: cond = "Partly Cloudy"
    else:            cond = "Clear"

    return {
        "match_id":                match_id,
        "weather_source":          "Open-Meteo Archive API",
        "weather_condition":       cond,
        "rain_flag":               1 if rain > 0 else 0,
        "precipitation_mm":        round(prec, 2),
        "temperature_c":           T,
        "apparent_temperature_c":  raw.get("apparent_temperature"),
        "humidity_percent":        RH,
        "dew_point_c":             raw.get("dew_point_2m"),
        "wind_speed_kmh":          raw.get("wind_speed_10m"),
        "wind_gust_kmh":           raw.get("wind_gusts_10m"),
        "cloud_cover_percent":     cloud,
        "pressure_hpa":            raw.get("surface_pressure"),
        "heat_index_c":            hi,
        "wet_bulb_temperature_c":  wb,
        "feels_like_temperature_c": raw.get("apparent_temperature"),
        "wbgt_c":                  wbgt,
        "cooling_break_flag":      cb_f,
        "cooling_break_count":     cb_c,
        "heat_index_bucket":       _bucket(hi, 27, 35) if hi is not None else None,
        "wet_bulb_bucket":         _bucket(wb, 18, 25) if wb is not None else None,
        "temperature_bucket":      _bucket(T,  20, 30) if T  is not None else None,
        "humidity_bucket":         _bucket(RH, 50, 70) if RH is not None else None,
    }

# ── Modeling ──────────────────────────────────────────────────────────────────

def rebuild_modeling_dataset(t1, t2, t3):
    """Merge match + team_stats + weather into modeling_dataset.csv columns."""
    from sklearn.impute import SimpleImputer

    t2s = t2.sort_values("match_id").copy()

    def rolling_avg(df, team_col, stat_col):
        out = {}
        for team, grp in df.groupby(team_col):
            cumsum, n = 0, 0
            for idx, row in grp.iterrows():
                out[idx] = cumsum / n if n > 0 else None
                cumsum += row[stat_col]; n += 1
        return out

    avg_sc = rolling_avg(t2s, "team", "goals_scored")
    avg_co = rolling_avg(t2s, "team", "goals_conceded")
    t2s["avg_goals_before"]    = t2s.index.map(avg_sc)
    t2s["avg_conceded_before"] = t2s.index.map(avg_co)

    home_avg = t2s.groupby("match_id").first()["avg_goals_before"].rename("home_avg_goals_before")
    away_avg = t2s.groupby("match_id").last()["avg_goals_before"].rename("away_avg_goals_before")
    home_con = t2s.groupby("match_id").first()["avg_conceded_before"].rename("home_avg_conceded_before")
    away_con = t2s.groupby("match_id").last()["avg_conceded_before"].rename("away_avg_conceded_before")

    df = (t1.set_index("match_id")
           .join(t3.set_index("match_id"))
           .join(home_avg).join(away_avg).join(home_con).join(away_con)
           .reset_index())

    df["home_elo"]       = df["home_team"].map(ELO)
    df["away_elo"]       = df["away_team"].map(ELO)
    df["elo_difference"] = df["home_elo"] - df["away_elo"]
    df["total_goals"]    = df.get("home_goals", pd.Series(dtype=float)) + \
                           df.get("away_goals", pd.Series(dtype=float))
    df["precipitation_bucket"] = df.get("precipitation_mm", pd.Series(dtype=float)).apply(
        lambda x: _bucket(x, 0.1, 5.0, ("None","Light","Heavy")) if pd.notna(x) else None)

    keep = [
        "match_id","match_date","home_team","away_team",
        "home_goals","away_goals","total_goals",
        "elo_difference","home_elo","away_elo",
        "home_avg_goals_before","away_avg_goals_before",
        "home_avg_conceded_before","away_avg_conceded_before",
        "rain_flag","precipitation_mm","precipitation_bucket",
        "temperature_c","temperature_bucket",
        "humidity_percent","humidity_bucket",
        "heat_index_c","heat_index_bucket",
        "wet_bulb_temperature_c","wet_bulb_bucket",
        "wbgt_c","wind_speed_kmh","cloud_cover_percent","pressure_hpa",
        "cooling_break_flag","cooling_break_count","venue_type",
    ]
    return df[[c for c in keep if c in df.columns]]

def train_best_model(df_model):
    """Retrain RF on all completed matches with weather. Return fitted model + imputer."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer

    feat_cols = [c for c in [
        "rain_flag","precipitation_mm","temperature_c","heat_index_c",
        "wet_bulb_temperature_c","wbgt_c","humidity_percent",
        "cloud_cover_percent","wind_speed_kmh","elo_difference",
        "home_avg_goals_before","away_avg_goals_before",
        "home_avg_conceded_before","away_avg_conceded_before",
    ] if c in df_model.columns]

    sub = df_model[feat_cols + ["total_goals"]].dropna(subset=["total_goals"])
    if len(sub) < 6:
        return None, None, feat_cols

    imp = SimpleImputer(strategy="median")
    X = imp.fit_transform(sub[feat_cols])
    y = sub["total_goals"].values
    rf = RandomForestRegressor(n_estimators=200, max_depth=4, random_state=42)
    rf.fit(X, y)
    log.info(f"Model trained on {len(y)} completed matches")
    return rf, imp, feat_cols

# ── Prediction history ────────────────────────────────────────────────────────

PRED_HISTORY_COLS = [
    "match_id","match_date","home_team","away_team",
    "prediction_date","predicted_total_goals","probability_over_2_5",
    "actual_total_goals","actual_home_goals","actual_away_goals",
    "prediction_error",
]

def load_prediction_history():
    p = PRED_DIR / "prediction_history.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame(columns=PRED_HISTORY_COLS)

def save_prediction_history(df):
    PRED_DIR.mkdir(exist_ok=True)
    df.to_csv(PRED_DIR / "prediction_history.csv", index=False)

# ── Logging ───────────────────────────────────────────────────────────────────

def append_update_log(run_date, n_new, n_weather, n_preds, model_retrained):
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / "update_log.csv"
    header = ["run_date","run_ts","new_matches","weather_records","predictions_updated","model_retrained"]
    row = [run_date, datetime.utcnow().isoformat(timespec="seconds"),
           n_new, n_weather, n_preds, int(model_retrained)]
    write_header = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(header)
        w.writerow(row)

# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(target_dates: list[str], dry_run: bool = False):
    today_str = date.today().isoformat()
    log.info(f"=== Daily Update  run_date={today_str}  target_dates={target_dates} ===")
    if dry_run:
        log.info("DRY RUN — no files will be written")

    # ── 1. Load current data ─────────────────────────────────────────────────
    world_cup  = pd.read_csv(EXT / "world_cup_matches.csv")
    locations  = pd.read_csv(EXT / "match_locations.csv")
    t1         = pd.read_csv(RAW / "match_metadata.csv")
    t2         = pd.read_csv(RAW / "team_match_stats.csv")
    t3         = pd.read_csv(PROC / "weather_data.csv")
    forecasts  = pd.read_csv(FINAL / "remaining_match_forecasts.csv")
    pred_hist  = load_prediction_history()

    existing_completed = set(t1["match_id"].tolist())
    existing_weather   = set(t3["match_id"].tolist()) if "match_id" in t3.columns else set()

    # ── 2. Detect newly completed matches ────────────────────────────────────
    newly_completed = []
    dq_issues = []

    for check_date in sorted(set(target_dates)):
        log.info(f"Checking ESPN for results on {check_date} …")
        espn_results = fetch_results(check_date)
        log.info(f"  ESPN returned {len(espn_results)} events")

        candidates = world_cup[
            (world_cup["match_date"] == check_date) &
            (world_cup["match_status"] != "Completed")
        ]

        for _, match in candidates.iterrows():
            mid = match["match_id"]
            home = str(match["home_team"]) if pd.notna(match["home_team"]) else None
            away = str(match["away_team"]) if pd.notna(match["away_team"]) else None

            if home is None or away is None:
                log.info(f"  {mid}: skipping — TBD teams")
                continue

            result = find_match(espn_results, home, away)

            if result is None:
                log.info(f"  {mid} {home} vs {away}: no ESPN result found")
                continue

            if not result["completed"]:
                log.info(f"  {mid} {home} vs {away}: not yet completed")
                continue

            if mid in existing_completed:
                log.info(f"  {mid}: already in match_metadata.csv, skipping")
                continue

            hg = result["home_goals"]
            ag = result["away_goals"]
            winner = home if hg > ag else (away if ag > hg else "Draw")

            log.info(f"  NEW  {mid}  {home} {hg}–{ag} {away}")
            newly_completed.append({
                "match_id":    mid,
                "home_team":   home,
                "away_team":   away,
                "home_goals":  hg,
                "away_goals":  ag,
                "winner":      winner,
                "match_date":  check_date,
                "stage":       str(match.get("stage", "")),
                "group":       str(match.get("group", "")),
                "stadium":     str(match.get("stadium", "")),
                "city":        str(match.get("city", "")),
                "country":     str(match.get("country", "")),
            })

    if not newly_completed and not dry_run:
        log.info("No new completed matches — checking if forecast refresh needed")
        weather_fetched, weather_failed = 0, 0
        n_preds = _refresh_forecasts(world_cup, locations, forecasts, t1, t2, t3, dry_run)
        _write_summary(today_str, [], 0, 0, n_preds, False, dq_issues, pred_hist, ROOT)
        append_update_log(today_str, 0, 0, n_preds, False)
        return

    if dry_run:
        log.info(f"DRY RUN: would update {len(newly_completed)} matches")
        for m in newly_completed:
            log.info(f"  {m['match_id']}  {m['home_team']} {m['home_goals']}–{m['away_goals']} {m['away_team']}")
        return

    # ── 3. Update world_cup_matches.csv ──────────────────────────────────────
    for m in newly_completed:
        mask = world_cup["match_id"] == m["match_id"]
        world_cup.loc[mask, "match_status"] = "Completed"
        world_cup.loc[mask, "home_goals"]   = m["home_goals"]
        world_cup.loc[mask, "away_goals"]   = m["away_goals"]
        world_cup.loc[mask, "winner"]       = m["winner"]

    world_cup.to_csv(EXT / "world_cup_matches.csv", index=False)
    log.info(f"Updated world_cup_matches.csv")

    # ── 4. Append to match_metadata.csv and team_match_stats.csv ────────────
    loc_idx = locations.set_index("stadium")
    new_t1_rows = []
    new_t2_rows = []

    for m in newly_completed:
        stadium = m["stadium"]
        loc_row = loc_idx.loc[stadium] if stadium in loc_idx.index else None
        lat  = loc_row["latitude"]  if loc_row is not None else None
        lon  = loc_row["longitude"] if loc_row is not None else None
        tz   = loc_row["timezone"]  if loc_row is not None else None
        vt, state, _ = VENUE_TYPE.get(stadium, ("Unknown", "", m["country"]))
        kickoff_info = world_cup[world_cup["match_id"] == m["match_id"]]["kickoff_time_local"]
        kickoff = kickoff_info.iloc[0] if len(kickoff_info) else None
        dow = pd.to_datetime(m["match_date"]).day_name()

        new_t1_rows.append({
            "match_id":         m["match_id"],
            "match_date":       m["match_date"],
            "match_day_of_week": dow,
            "kickoff_time_local": kickoff,
            "competition_stage": m["stage"],
            "group":            m["group"],
            "home_team":        m["home_team"],
            "away_team":        m["away_team"],
            "stadium":          stadium,
            "city":             m["city"],
            "state_or_region":  state,
            "country":          m["country"],
            "latitude":         lat,
            "longitude":        lon,
            "venue_type":       vt,
            "attendance":       None,
        })

        for team, opp, gs, gc in [
            (m["home_team"], m["away_team"], m["home_goals"], m["away_goals"]),
            (m["away_team"], m["home_team"], m["away_goals"], m["home_goals"]),
        ]:
            result = "Win" if gs > gc else ("Draw" if gs == gc else "Loss")
            new_t2_rows.append({
                "match_id":       m["match_id"],
                "team":           team,
                "opponent":       opp,
                "goals_scored":   gs,
                "goals_conceded": gc,
                "result":         result,
                "goal_difference": gs - gc,
            })

        if lat is None:
            dq_issues.append(f"{m['match_id']}: no coordinates for stadium '{stadium}' — weather skipped")

    t1 = pd.concat([t1, pd.DataFrame(new_t1_rows)], ignore_index=True)
    t2 = pd.concat([t2, pd.DataFrame(new_t2_rows)], ignore_index=True)
    t1.to_csv(RAW / "match_metadata.csv", index=False)
    t2.to_csv(RAW / "team_match_stats.csv", index=False)
    log.info(f"match_metadata.csv: {len(t1)} rows | team_match_stats.csv: {len(t2)} rows")

    # ── 5. Fetch archive weather for newly completed matches ─────────────────
    weather_fetched = 0
    weather_failed  = 0
    new_weather_rows = []

    for m in newly_completed:
        mid = m["match_id"]
        if mid in existing_weather:
            log.info(f"  {mid}: weather already exists, skipping")
            continue
        t1_row = t1[t1["match_id"] == mid].iloc[0]
        lat = t1_row.get("latitude")
        lon = t1_row.get("longitude")
        tz  = locations[locations["stadium"] == t1_row.get("stadium", "")]["timezone"]
        tz  = tz.iloc[0] if len(tz) else None

        if pd.isna(lat) or lat is None:
            log.warning(f"  {mid}: no coordinates — weather skipped")
            weather_failed += 1
            new_weather_rows.append({"match_id": mid})
            continue

        kickoff_str = str(t1_row.get("kickoff_time_local", "18:00") or "18:00")
        kickoff_hour = int(kickoff_str[:2])

        log.info(f"  Fetching weather {mid}  {m['home_team']} vs {m['away_team']}  {lat},{lon} …")
        raw = fetch_archive_weather(lat, lon, m["match_date"], kickoff_hour, tz)
        time.sleep(0.35)

        row = _build_weather_row(mid, raw)
        new_weather_rows.append(row)
        if raw is not None:
            weather_fetched += 1
            log.info(f"    T={raw.get('temperature_2m')}°C  RH={raw.get('relative_humidity_2m')}%")
        else:
            weather_failed += 1

    if new_weather_rows:
        t3 = pd.concat([t3, pd.DataFrame(new_weather_rows)], ignore_index=True)
        t3.to_csv(PROC / "weather_data.csv", index=False)
        log.info(f"weather_data.csv: {len(t3)} rows ({weather_fetched} new, {weather_failed} failed)")

    # ── 6. Rebuild modeling_dataset.csv ─────────────────────────────────────
    df_model = rebuild_modeling_dataset(t1, t2, t3)
    df_model.to_csv(PROC / "modeling_dataset.csv", index=False)
    log.info(f"modeling_dataset.csv: {len(df_model)} rows")

    # ── 7. Retrain models (if >= 3 new matches) ──────────────────────────────
    model_retrained = False
    rf_model = None
    rf_imp   = None
    feat_cols = []

    if len(newly_completed) >= 3:
        rf_model, rf_imp, feat_cols = train_best_model(df_model)
        if rf_model is not None:
            model_retrained = True
            _save_cv_results(df_model, feat_cols)
    else:
        log.info(f"Only {len(newly_completed)} new match(es) — skipping retrain (threshold: 3)")

    # ── 8. Refresh forecasts for upcoming matches ────────────────────────────
    n_preds = _refresh_forecasts(world_cup, locations, forecasts, t1, t2, t3, dry_run,
                                 rf_model=rf_model, rf_imp=rf_imp, feat_cols=feat_cols,
                                 df_model=df_model)

    # ── 9. Update prediction history ─────────────────────────────────────────
    fresh_forecasts = pd.read_csv(FINAL / "remaining_match_forecasts.csv")

    # Add new predictions to history — team names from world_cup (authoritative)
    wc_idx = world_cup.set_index("match_id")
    pred_ids_in_history = set(pred_hist["match_id"].tolist()) if len(pred_hist) else set()
    for _, row in fresh_forecasts.iterrows():
        mid = row["match_id"]
        if mid not in pred_ids_in_history and pd.notna(row.get("predicted_total_goals")):
            wc_row = wc_idx.loc[mid] if mid in wc_idx.index else None
            pred_hist = pd.concat([pred_hist, pd.DataFrame([{
                "match_id":                mid,
                "match_date":              wc_row["match_date"] if wc_row is not None else row.get("match_date"),
                "home_team":               wc_row["home_team"]  if wc_row is not None else row.get("home_team"),
                "away_team":               wc_row["away_team"]  if wc_row is not None else row.get("away_team"),
                "prediction_date":         today_str,
                "predicted_total_goals":   row.get("predicted_total_goals"),
                "probability_over_2_5":    row.get("probability_over_2_5_goals"),
                "actual_total_goals":      None,
                "actual_home_goals":       None,
                "actual_away_goals":       None,
                "prediction_error":        None,
            }])], ignore_index=True)

    # Fill actuals for newly completed matches
    for m in newly_completed:
        mid = m["match_id"]
        actual_total = m["home_goals"] + m["away_goals"]
        mask = pred_hist["match_id"] == mid
        if mask.any():
            pred_hist.loc[mask, "actual_total_goals"] = actual_total
            pred_hist.loc[mask, "actual_home_goals"]  = m["home_goals"]
            pred_hist.loc[mask, "actual_away_goals"]  = m["away_goals"]
            pred_val = pred_hist.loc[mask, "predicted_total_goals"].iloc[0]
            if pd.notna(pred_val):
                pred_hist.loc[mask, "prediction_error"] = round(float(pred_val) - actual_total, 3)
            log.info(f"  Prediction history updated for {mid}")

    save_prediction_history(pred_hist)

    # Compute rolling accuracy
    resolved = pred_hist.dropna(subset=["actual_total_goals","predicted_total_goals"])
    pred_accuracy = None
    if len(resolved) >= 3:
        errors = (resolved["predicted_total_goals"] - resolved["actual_total_goals"]).abs()
        pred_accuracy = {
            "n":    len(resolved),
            "mae":  round(errors.mean(), 3),
            "rmse": round(np.sqrt((errors**2).mean()), 3),
        }
        log.info(f"Prediction accuracy: n={pred_accuracy['n']}  MAE={pred_accuracy['mae']}  RMSE={pred_accuracy['rmse']}")

    # ── 10. Generate daily summary ────────────────────────────────────────────
    _write_summary(today_str, newly_completed, weather_fetched, weather_failed,
                   n_preds, model_retrained, dq_issues, pred_accuracy, ROOT)

    # ── 11. Append to update log ──────────────────────────────────────────────
    append_update_log(today_str, len(newly_completed), weather_fetched, n_preds, model_retrained)
    log.info(f"=== Update complete: {len(newly_completed)} new match(es) processed ===")


def _refresh_forecasts(world_cup, locations, old_forecasts, t1, t2, t3,
                       dry_run, rf_model=None, rf_imp=None, feat_cols=None, df_model=None):
    """Regenerate remaining_match_forecasts.csv for all non-completed matches."""
    upcoming = world_cup[world_cup["match_status"] != "Completed"].copy()
    if upcoming.empty:
        log.info("No upcoming matches to forecast")
        return 0

    loc_idx  = locations.set_index("stadium")
    mean_goals = 3.0

    # Compute latest rolling averages from t2 for ELO + avg features
    if df_model is not None and len(df_model):
        completed_model = df_model.dropna(subset=["total_goals"])
        if len(completed_model):
            mean_goals = completed_model["total_goals"].mean()

    rows = []
    n_preds = 0

    for _, match in upcoming.iterrows():
        mid    = match["match_id"]
        home   = match["home_team"] if pd.notna(match["home_team"]) else None
        away   = match["away_team"] if pd.notna(match["away_team"]) else None
        mdate  = match["match_date"]
        stadium = match.get("stadium", "")

        loc_row = loc_idx.loc[stadium] if (pd.notna(stadium) and stadium in loc_idx.index) else None
        lat = loc_row["latitude"]  if loc_row is not None else None
        lon = loc_row["longitude"] if loc_row is not None else None
        tz  = loc_row["timezone"]  if loc_row is not None else None
        kickoff = match.get("kickoff_time_local","18:00") or "18:00"
        kickoff_hour = int(str(kickoff)[:2])

        row = {
            "match_id":        mid,
            "match_date":      mdate,
            "home_team":       home,
            "away_team":       away,
            "competition_stage": match.get("stage",""),
            "stadium":         stadium,
            "city":            match.get("city",""),
            "country":         match.get("country",""),
        }

        if home is None or away is None or lat is None:
            row["predicted_total_goals"]      = None
            row["probability_over_2_5_goals"] = None
            row["forecast_source"]            = "TBD — teams or venue unknown"
            rows.append(row)
            continue

        # Fetch forecast weather
        if not dry_run and pd.notna(lat):
            raw = fetch_forecast_weather(lat, lon, mdate, kickoff_hour, tz)
            time.sleep(0.35)
        else:
            raw = None

        T   = raw["temperature_2m"]           if raw else 25.0
        RH  = raw["relative_humidity_2m"]     if raw else 55.0
        prec = raw.get("precipitation", 0)    if raw else 0
        rain = raw.get("rain", 0)             if raw else 0
        wind = raw.get("wind_speed_10m", 10)  if raw else 10.0
        hi   = _heat_index(T, RH)
        wb   = _wet_bulb(T, RH)
        wbgt = _wbgt(T, RH)
        cb_f, _ = _cooling_break(wbgt)

        # Prediction
        h_elo = ELO.get(home, 1750)
        a_elo = ELO.get(away, 1750)
        elo_d = h_elo - a_elo

        if rf_model is not None and rf_imp is not None and feat_cols:
            feat_map = {
                "rain_flag": 1 if rain > 0 else 0,
                "precipitation_mm": prec,
                "temperature_c": T, "heat_index_c": hi,
                "wet_bulb_temperature_c": wb, "wbgt_c": wbgt,
                "humidity_percent": RH, "cloud_cover_percent": raw.get("cloud_cover",50) if raw else 50,
                "wind_speed_kmh": wind, "elo_difference": elo_d,
                "home_avg_goals_before": mean_goals/2,
                "away_avg_goals_before": mean_goals/2,
                "home_avg_conceded_before": mean_goals/2,
                "away_avg_conceded_before": mean_goals/2,
            }
            X_pred = rf_imp.transform([[feat_map.get(f, 0) for f in feat_cols]])
            pred = max(0.5, round(float(rf_model.predict(X_pred)[0]), 2))
        else:
            # Naive: mean + ELO adjustment
            elo_adj = elo_d / 2000.0
            pred = max(0.5, round(mean_goals + elo_adj * 0.5, 2))

        row.update({
            "forecast_temperature_c":   T,
            "forecast_humidity_percent": RH,
            "forecast_precipitation_mm": round(prec, 2),
            "forecast_heat_index_c":    hi,
            "forecast_wet_bulb_c":      wb,
            "forecast_wbgt_c":          wbgt,
            "predicted_cooling_break":  cb_f,
            "predicted_total_goals":    pred,
            "probability_over_2_5_goals": _poisson_over_25(pred),
            "forecast_source":          "Open-Meteo Forecast API" if raw else "Naive (no forecast available)",
        })
        n_preds += 1
        rows.append(row)

    if not dry_run:
        df_fc = pd.DataFrame(rows)
        df_fc.to_csv(FINAL / "remaining_match_forecasts.csv", index=False)
        log.info(f"remaining_match_forecasts.csv: {len(df_fc)} rows ({n_preds} with predictions)")

    return n_preds


def _save_cv_results(df_model, feat_cols):
    """Re-run cross-validation and update prediction_results.csv."""
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import cross_val_score, KFold
    from sklearn.impute import SimpleImputer

    FEATURE_SETS = {
        "Baseline":  ["elo_difference"],
        "Rain":      ["rain_flag","precipitation_mm","elo_difference"],
        "Heat":      ["temperature_c","heat_index_c","wet_bulb_temperature_c","wbgt_c","humidity_percent","elo_difference"],
        "Rain+Heat": ["rain_flag","precipitation_mm","temperature_c","heat_index_c","wet_bulb_temperature_c","wbgt_c","humidity_percent","elo_difference"],
        "Full":      feat_cols,
    }
    MODELS = {
        "LinearRegression": LinearRegression(),
        "RandomForest":     RandomForestRegressor(n_estimators=100, max_depth=3, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=50, max_depth=2, learning_rate=0.1, random_state=42),
    }
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rows = []
    for fs_name, features in FEATURE_SETS.items():
        avail = [f for f in features if f in df_model.columns]
        sub = df_model[avail + ["total_goals"]].dropna(subset=["total_goals"])
        if len(sub) < 6:
            continue
        imp = SimpleImputer(strategy="median")
        X = imp.fit_transform(sub[avail])
        y = sub["total_goals"].values
        for mn, model in MODELS.items():
            cv_r2  = cross_val_score(model, X, y, cv=kf, scoring="r2")
            cv_mae = cross_val_score(model, X, y, cv=kf, scoring="neg_mean_absolute_error")
            rows.append({"feature_set": fs_name, "model": mn, "n_samples": len(y),
                         "cv_r2_mean": round(cv_r2.mean(),3), "cv_r2_std": round(cv_r2.std(),3),
                         "cv_mae": round(-cv_mae.mean(),3)})
    if rows:
        pd.DataFrame(rows).to_csv(FINAL / "prediction_results.csv", index=False)
        log.info(f"prediction_results.csv updated ({len(rows)} rows)")


def _write_summary(run_date, newly_completed, weather_fetched, weather_failed,
                   n_preds, model_retrained, dq_issues, pred_accuracy, root):
    path = write_summary(
        run_date=run_date,
        newly_completed=newly_completed,
        weather_fetched=weather_fetched,
        weather_failed=weather_failed,
        predictions_updated=n_preds,
        model_retrained=model_retrained,
        dq_issues=dq_issues,
        prediction_accuracy=pred_accuracy,
        root=root,
    )
    log.info(f"Daily summary: {path}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FIFA WC 2026 Daily Update Pipeline")
    parser.add_argument("--date",      help="Process a specific date (YYYY-MM-DD)")
    parser.add_argument("--lookback",  type=int, default=3,
                        help="Number of past days to check in addition to today (default: 3)")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Show what would change without writing any files")
    args = parser.parse_args()

    if args.date:
        dates = [args.date]
    else:
        today = date.today()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(args.lookback + 1)]
        dates = [d for d in dates if d >= "2026-06-11"]  # tournament start

    run(target_dates=dates, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
