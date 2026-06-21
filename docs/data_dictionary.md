# Data Dictionary — FIFA World Cup 2026 Analysis

All datasets are stored as UTF-8 CSV files. Empty string = NULL for numeric fields.

## Field Availability Key

| Symbol | Meaning |
|--------|---------|
| **Yes** | Field is populated for this match type |
| **NULL** | Field exists in schema but is empty (data not yet available) |
| **--** | Field does not apply to this match type |

**Match status values used across datasets:**

| Status | Description |
|--------|-------------|
| `Completed` | Match has been played; official result available |
| `Scheduled` | Date and teams confirmed; match not yet played |
| `TBD` | Teams not yet determined (knockout stage before groups complete) |
| `In Progress` | Match currently being played (real-time updates only) |

---

## Dataset Index

| File | Rows | Covers | Location |
|------|------|--------|----------|
| world_cup_matches.csv | 104 | All matches — Completed + Scheduled + TBD | data/external/ |
| match_locations.csv | 16 | Stadium reference (lat, lon, capacity, timezone) | data/external/ |
| match_metadata.csv | 36 | Completed matches only | data/raw/ |
| team_match_stats.csv | 72 | Completed matches — 2 rows per match | data/raw/ |
| weather_data.csv | 28+ | Completed matches with confirmed venue | data/processed/ |
| modeling_dataset.csv | 36 | Completed matches — ML-ready features | data/processed/ |
| prediction_results.csv | 15 | Model CV comparison (3 models x 5 feature sets) | data/final/ |
| remaining_match_forecasts.csv | 68 | Upcoming matches — forecast weather + predictions | data/final/ |

---

## data/external/world_cup_matches.csv

**104 rows | Master schedule for the entire tournament | One row per match**

This is the authoritative source for all 104 matches. Completed matches have goals and winner populated. Scheduled matches have NULL goals. TBD matches have NULL home/away teams.

| Field | Type | Description | Completed | Scheduled | TBD | Example |
|-------|------|-------------|:---------:|:---------:|:---:|---------|
| match_id | string | Unique identifier — WC2026-001 through WC2026-104 | Yes | Yes | Yes | `WC2026-001` |
| stage | string | Tournament stage | Yes | Yes | Yes | `Group Stage` |
| group | string | Group letter A-L; empty for knockout rounds | Yes | Yes | Yes | `A` |
| match_date | date | Scheduled or played date (YYYY-MM-DD) | Yes | Yes | Yes | `2026-06-11` |
| kickoff_time_local | time | Local stadium kickoff time (HH:MM) | Yes | Yes | Yes | `20:00` |
| kickoff_time_utc | time | UTC kickoff time (HH:MM) | Yes | Yes | Yes | `00:00` |
| timezone | string | IANA timezone name | Yes | Yes | Yes | `America/New_York` |
| home_team | string | Home team name; NULL until bracket is set | Yes | Yes | NULL | `Mexico` |
| away_team | string | Away team name; NULL until bracket is set | Yes | Yes | NULL | `South Africa` |
| home_goals | integer | Goals scored by home team; NULL before kickoff | Yes | NULL | NULL | `2` |
| away_goals | integer | Goals scored by away team; NULL before kickoff | Yes | NULL | NULL | `0` |
| winner | string | Winning team / "Draw" / NULL before kickoff | Yes | NULL | NULL | `Mexico` |
| stadium | string | Official stadium name | Yes | Yes | Yes | `Estadio Azteca` |
| city | string | Host city | Yes | Yes | Yes | `Mexico City` |
| country | string | USA / Canada / Mexico | Yes | Yes | Yes | `Mexico` |
| stadium_capacity | integer | FIFA-confirmed seating capacity | Yes | Yes | Yes | `87523` |
| match_status | string | Completed / Scheduled / TBD | Yes | Yes | Yes | `Completed` |

---

## data/external/match_locations.csv

**16 rows | One row per stadium | Static reference — does not change during tournament**

| Field | Type | Description | Completed | Scheduled | TBD | Example |
|-------|------|-------------|:---------:|:---------:|:---:|---------|
| stadium | string | Official stadium name | Yes | Yes | Yes | `Estadio Azteca` |
| city | string | Host city | Yes | Yes | Yes | `Mexico City` |
| country | string | USA / Canada / Mexico | Yes | Yes | Yes | `Mexico` |
| latitude | float | Stadium latitude (decimal degrees) | Yes | Yes | Yes | `19.3029` |
| longitude | float | Stadium longitude (decimal degrees) | Yes | Yes | Yes | `-99.1500` |
| stadium_capacity | integer | FIFA-confirmed seating capacity | Yes | Yes | Yes | `87523` |
| timezone | string | IANA timezone name | Yes | Yes | Yes | `America/Mexico_City` |
| utc_offset_hours | integer | UTC offset during the tournament (DST applied for US/Canada) | Yes | Yes | Yes | `-6` |

---

## data/raw/match_metadata.csv

**36 rows | Completed group-stage matches only (MD1 + MD2) | One row per match**

This file grows as matches are played. Only completed matches appear here. For the full schedule including upcoming matches, see `world_cup_matches.csv`.

| Field | Type | Description | Completed | Scheduled | Example |
|-------|------|-------------|:---------:|:---------:|---------|
| match_id | string | Unique identifier — WC2026-001 through WC2026-036 | Yes | -- | `WC2026-001` |
| match_date | date | ISO 8601 match date | Yes | -- | `2026-06-11` |
| match_day_of_week | string | Day name | Yes | -- | `Thursday` |
| kickoff_time_local | time | Local stadium kickoff time (HH:MM) | Yes | -- | `20:00` |
| competition_stage | string | Always "Group Stage" for current data | Yes | -- | `Group Stage` |
| group | string | Group letter A-L | Yes | -- | `A` |
| home_team | string | Home team name (draw order — not host advantage) | Yes | -- | `Mexico` |
| away_team | string | Away team name | Yes | -- | `South Africa` |
| home_goals | integer | Goals scored by home team | Yes | -- | `2` |
| away_goals | integer | Goals scored by away team | Yes | -- | `0` |
| total_goals | integer | home_goals + away_goals | Yes | -- | `2` |
| result_home | string | Win / Draw / Loss from home team perspective | Yes | -- | `Win` |
| stadium | string | Official stadium name | Yes | -- | `Estadio Azteca` |
| city | string | Host city | Yes | -- | `Mexico City` |
| state_or_region | string | State, province, or federal entity | Yes | -- | `Mexico City` |
| country | string | USA / Canada / Mexico | Yes | -- | `Mexico` |
| latitude | float | Stadium latitude; NULL if unconfirmed at pipeline run time | Yes | -- | `19.3029` |
| longitude | float | Stadium longitude; NULL if unconfirmed | Yes | -- | `-99.1500` |
| venue_type | string | Open / Covered / Partial (roof type) | Yes | -- | `Open` |
| attendance | integer | Official attendance; NULL if not yet reported | Yes | -- | `87523` |

---

## data/raw/team_match_stats.csv

**72 rows | Completed matches only | Two rows per match (one per team)**

| Field | Type | Description | Completed | Scheduled | Example |
|-------|------|-------------|:---------:|:---------:|---------|
| match_id | string | Foreign key to match_metadata | Yes | -- | `WC2026-001` |
| team | string | Team name (this row's perspective) | Yes | -- | `Mexico` |
| opponent | string | Opposing team name | Yes | -- | `South Africa` |
| goals_scored | integer | Goals scored by this team | Yes | -- | `2` |
| goals_conceded | integer | Goals conceded by this team | Yes | -- | `0` |
| result | string | Win / Draw / Loss | Yes | -- | `Win` |
| goal_difference | integer | goals_scored minus goals_conceded | Yes | -- | `2` |

---

## data/processed/weather_data.csv

**28+ rows | One row per match with confirmed venue | Grows as matches are played**

Historical matches use the Open-Meteo Archive API. Future matches in `remaining_match_forecasts.csv` use the Forecast API with the same parameters. The `weather_source` field identifies the data origin.

| Field | Type | Description | Completed | Scheduled | Example |
|-------|------|-------------|:---------:|:---------:|---------|
| match_id | string | Foreign key | Yes | -- | `WC2026-001` |
| weather_source | string | API source and version | Yes | -- | `Open-Meteo Archive v1.0` |
| rain_flag | integer | 1 if precipitation_mm > 0, else 0 | Yes | -- | `0` |
| precipitation_mm | float | Total precipitation at kickoff hour (mm) | Yes | -- | `0.0` |
| temperature_c | float | Dry-bulb temperature at 2 m (degrees C) | Yes | -- | `28.4` |
| apparent_temperature_c | float | Feels-like temperature from API (degrees C) | Yes | -- | `31.2` |
| humidity_percent | float | Relative humidity (%) | Yes | -- | `72` |
| dew_point_c | float | Dew point at 2 m (degrees C) | Yes | -- | `22.1` |
| wind_speed_kmh | float | Wind speed at 10 m (km/h) | Yes | -- | `14.4` |
| wind_gust_kmh | float | Wind gust at 10 m (km/h) | Yes | -- | `22.0` |
| cloud_cover_percent | float | Total cloud cover (%) | Yes | -- | `45` |
| pressure_hpa | float | Surface pressure (hPa) | Yes | -- | `1013.2` |
| heat_index_c | float | NOAA Rothfusz heat index (degrees C); equals temperature_c outside valid range | Yes | -- | `32.1` |
| wet_bulb_temperature_c | float | Stull (2011) wet-bulb temperature (degrees C) | Yes | -- | `24.6` |
| feels_like_temperature_c | float | Same as apparent_temperature_c | Yes | -- | `31.2` |
| wbgt_c | float | Simplified WBGT in shade: 0.7 * WB + 0.3 * T (degrees C) | Yes | -- | `26.7` |
| cooling_break_flag | integer | 1 if WBGT >= 28 degrees C (FIFA protocol threshold) | Yes | -- | `0` |
| cooling_break_count | integer | 1 if WBGT 28-31 degrees C; 2 if WBGT >= 32 degrees C | Yes | -- | `0` |
| heat_index_bucket | string | Low (<=27 C) / Medium (27-35 C) / High (>=35 C) | Yes | -- | `Medium` |
| wet_bulb_bucket | string | Low (<=18 C) / Medium (18-25 C) / High (>=25 C) | Yes | -- | `Medium` |
| temperature_bucket | string | Low (<=20 C) / Medium (20-30 C) / High (>=30 C) | Yes | -- | `Medium` |
| humidity_bucket | string | Low (<=50%) / Medium (50-70%) / High (>=70%) | Yes | -- | `High` |

> For forecast weather on upcoming matches, see the `forecast_*` columns in `remaining_match_forecasts.csv`.

---

## data/processed/modeling_dataset.csv

**36 rows | ML-ready merged dataset | Historical matches only | Grows as matches complete**

Includes all columns from `match_metadata.csv` plus engineered features. This is the training dataset for all models. Future match feature vectors (for prediction) are constructed by `pipeline.py` at runtime and not saved separately.

| Field | Type | Description | Completed | Scheduled | Example |
|-------|------|-------------|:---------:|:---------:|---------|
| *(all match_metadata fields)* | | See match_metadata.csv | Yes | -- | |
| home_elo | integer | Home team pre-tournament ELO rating estimate | Yes | -- | `1850` |
| away_elo | integer | Away team pre-tournament ELO rating estimate | Yes | -- | `1620` |
| elo_difference | integer | home_elo minus away_elo (positive = home is stronger) | Yes | -- | `230` |
| home_avg_goals_before | float | Expanding-window mean goals scored by home team in prior tournament matches | Yes | -- | `1.5` |
| away_avg_goals_before | float | Expanding-window mean goals scored by away team in prior tournament matches | Yes | -- | `0.0` |
| home_avg_conceded_before | float | Expanding-window mean goals conceded by home team | Yes | -- | `0.5` |
| away_avg_conceded_before | float | Expanding-window mean goals conceded by away team | Yes | -- | `2.0` |
| home_travel_km | float | Straight-line distance (km) from home team's capital to stadium | Yes | -- | `4820` |
| away_travel_km | float | Straight-line distance (km) from away team's capital to stadium | Yes | -- | `9340` |
| precipitation_bucket | string | None (0 mm) / Light (0-5 mm) / Heavy (>=5 mm) | Yes | -- | `None` |
| matchup_type | string | Inter-confederation / Same confederation | Yes | -- | `Inter-confederation` |
| matchup_type_enc | integer | 0 = same confederation; 1 = inter-confederation | Yes | -- | `1` |
| venue_type_enc | integer | 0 = Open; 1 = Partial; 2 = Covered | Yes | -- | `0` |
| kickoff_hour | integer | Local kickoff hour (integer, 24-hour clock) | Yes | -- | `20` |

> Note: `home_avg_goals_before` and `away_avg_goals_before` are NULL (NaN) for a team's first match in the tournament and are replaced with 0 in the model.

---

## data/final/prediction_results.csv

**15 rows | Model cross-validation comparison | 3 models x 5 feature sets**

This is an evaluation summary table, not match-level data. Populated from historical matches only. Re-run `pipeline.py` as more matches complete to update CV metrics.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| model | string | LinearRegression / RandomForest / GradientBoosting | `RandomForest` |
| feature_set | string | Baseline / Rain / Heat / Rain+Heat / Full | `Full` |
| cv_r2_mean | float | Mean 5-fold cross-validated R2 | `-0.234` |
| cv_r2_std | float | Standard deviation of CV R2 across folds | `0.412` |
| cv_mae | float | Mean absolute error (CV mean) | `1.21` |
| cv_rmse | float | Root mean squared error (CV mean) | `1.54` |
| train_r2 | float | In-sample R2 (training data, not held out) | `0.891` |

> All CV R2 values are currently negative (expected at n = 28). The sample mean is the best predictor until n grows.

---

## data/final/remaining_match_forecasts.csv

**68 rows | Upcoming matches | Forecast weather + model predictions**

One row per scheduled or TBD match. Rows with TBD teams have NULL for home_team/away_team and NULL for predicted goals. Refreshed each time `pipeline.py` runs.

| Field | Type | Description | Scheduled | TBD | Example |
|-------|------|-------------|:---------:|:---:|---------|
| match_id | string | Foreign key to world_cup_matches | Yes | Yes | `WC2026-037` |
| home_team | string | Home team; NULL for TBD knockouts | Yes | NULL | `Argentina` |
| away_team | string | Away team; NULL for TBD knockouts | Yes | NULL | `France` |
| match_date | date | Scheduled match date | Yes | Yes | `2026-06-21` |
| stadium | string | Venue name | Yes | Yes | `Levi's Stadium` |
| city | string | Host city | Yes | Yes | `Santa Clara` |
| country | string | USA / Canada / Mexico | Yes | Yes | `USA` |
| forecast_temperature_c | float | Forecast air temperature at kickoff (degrees C) | Yes | Yes | `21.3` |
| forecast_humidity_percent | float | Forecast relative humidity (%) | Yes | Yes | `68` |
| forecast_precipitation_mm | float | Forecast precipitation at kickoff hour (mm) | Yes | Yes | `0.0` |
| forecast_heat_index_c | float | Calculated heat index from forecast data (degrees C) | Yes | Yes | `23.1` |
| forecast_wet_bulb_c | float | Calculated wet-bulb from forecast data (degrees C) | Yes | Yes | `17.8` |
| forecast_wbgt_c | float | Calculated WBGT from forecast data (degrees C) | Yes | Yes | `19.1` |
| predicted_total_goals | float | RF model prediction (expected combined goals) | Yes | NULL | `2.8` |
| probability_over_2_5_goals | float | Poisson-based P(total goals > 2.5) given predicted mean | Yes | NULL | `0.53` |

---

## Field Availability Summary

The table below shows which fields are available before vs after a match is played.

| Category | Fields | Before Kickoff | After Kickoff |
|----------|--------|:--------------:|:-------------:|
| Identity | match_id, stage, group, match_date | Yes | Yes |
| Venue | stadium, city, country, lat, lon, capacity | Yes* | Yes |
| Teams | home_team, away_team | Yes** | Yes |
| Schedule | kickoff_time_local, kickoff_time_utc, timezone | Yes | Yes |
| Result | home_goals, away_goals, total_goals, winner, result_home | No | Yes |
| Weather (actual) | temperature_c, precipitation_mm, humidity_percent, heat_index_c, wbgt_c, etc. | No | Yes |
| Weather (forecast) | forecast_temperature_c, forecast_precipitation_mm, forecast_wbgt_c, etc. | Yes | -- |
| Team strength | home_elo, away_elo, elo_difference | Yes | Yes |
| Form | home_avg_goals_before, away_avg_goals_before, etc. | Yes*** | Yes |
| Travel | home_travel_km, away_travel_km | Yes** | Yes |
| Predictions | predicted_total_goals, probability_over_2_5_goals | Yes** | Yes (for evaluation) |

\* Venue is confirmed for all group-stage matches; knockout venues are confirmed in the bracket.  
\*\* Available once teams are confirmed (not TBD).  
\*\*\* Rolling averages are computed from completed matches only; first-match value is 0.

---

*Last updated: 2026-06-21 | Source: Open-Meteo API, ESPN, FIFA.com*
