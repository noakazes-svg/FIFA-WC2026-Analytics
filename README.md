# FIFA World Cup 2026 — Weather, Heat & Goals

**Scope:** All 104 matches | Historical results + Future forecasts | Group Stage through Final  
**Tournament:** 2026 FIFA World Cup — USA / Canada / Mexico | June 11 – July 19, 2026  
**Status:** 36 of 104 matches completed | 68 upcoming | Updated as the tournament progresses

---

## Project Objectives

### 1. Historical Analysis
Analyse the relationship between real weather conditions and goals scored in completed matches.

- Weather fetched from the Open-Meteo **Archive** API at each match's exact kickoff time and stadium coordinates
- Heat stress metrics: Heat Index (NOAA Rothfusz), Wet-Bulb Temperature (Stull 2011), WBGT
- Statistical tests: Pearson correlation, Welch t-test, Cohen's d, one-way ANOVA
- Machine learning: Random Forest, Gradient Boosting, Linear Regression — 5-fold cross-validation

### 2. Future Match Forecasting
Predict total goals for all scheduled matches before they are played.

- Weather fetched from the Open-Meteo **Forecast** API using the same parameters and stadium coordinates
- Model trained on all completed matches with confirmed weather; predictions refresh as match date approaches
- Knockout-stage matches: prediction generated once both teams are confirmed after their group concludes
- All forecasts are probabilistic — uncertainty increases with lead time

---

## Prediction Pipeline

```
Scheduled Match (fixture confirmed: teams + stadium + date known)
         |
         v
Weather Forecast  <--  Open-Meteo Forecast API
                        stadium lat/lon + kickoff hour (UTC)
         |
         v
Feature Engineering
   ELO difference, rolling averages (from completed matches),
   travel distance, venue type, kickoff hour, heat stress metrics
         |
         v
Model Prediction  <--  RandomForest trained on completed matches
         |
         v
Outputs saved to remaining_match_forecasts.csv
   predicted_total_goals | probability_over_2_5_goals | forecast weather
         |
         +------------- Kickoff -------------+
         |
         v
Actual Result recorded in match_metadata.csv
         |
         v
Model Evaluation  <--  compare predicted vs actual
Rolling averages updated for next prediction cycle
```

---

## Data Coverage

| Category | Matches | Dates | Status |
|----------|---------|-------|--------|
| Group Stage MD1 | 24 | Jun 11-15 | Completed |
| Group Stage MD2 (first 12) | 12 | Jun 16-20 | Completed |
| Group Stage MD2 (remaining) | 12 | Jun 21-23 | Scheduled |
| Group Stage MD3 | 24 | Jun 24-27 | Scheduled |
| Round of 32 | 16 | Jun 29 - Jul 5 | TBD (teams after group stage) |
| Round of 16 | 8 | Jul 7-10 | TBD |
| Quarter-Finals | 4 | Jul 12-13 | TBD |
| Semi-Finals | 2 | Jul 16 | TBD |
| Third Place | 1 | Jul 19 | TBD |
| Final | 1 | Jul 19 | TBD |
| **Total** | **104** | Jun 11 - Jul 19 | |

**Field availability by match status:**

| Field | Completed | Scheduled | TBD |
|-------|:---------:|:---------:|:---:|
| match_id, stage, date, stadium | Yes | Yes | Yes |
| home_team / away_team | Yes | Yes | NULL |
| home_goals / away_goals / winner | Yes | NULL | NULL |
| Weather (actual, archive API) | Yes | -- | -- |
| Weather (forecast API) | -- | Yes | Yes (when date known) |
| ELO, travel distance, venue type | Yes | Yes | Yes (when teams/stadium known) |
| predicted_total_goals | Yes (retrospective) | Yes | Yes (when teams known) |

---

## Research Questions

| # | Question | Data Type |
|---|----------|-----------|
| 1 | Does goal timing (1H vs 2H split) shift in hotter or rainy matches? | Historical |
| 2 | Does team strength (ELO) predict result better in rain vs dry? | Historical |
| 3 | Is there a relationship between heat and disciplinary cards? | Historical |
| 4 | Does heat reduce match tempo (passes, distance covered)? | Historical |
| 5 | Does rain suppress shooting volume and xG? | Historical |
| 6 | Do later kickoff times correlate with more goals? | Historical |
| 7 | Which stadiums produce the most goals? | Historical |
| 8 | Does higher attendance drive more goals? | Historical |
| 9 | Does long-haul travel fatigue affect away-team performance? | Historical |
| 10 | Do inter-confederation matchups produce different goal totals? | Historical |
| 11 | Can a weather + ELO model outperform a naive mean predictor at scale? | Predictive |

---

## Data Sources

| Type | Source | Notes |
|------|--------|-------|
| Match results | CBSSports / Wikipedia group pages | MD1-MD2 results |
| Full schedule | ESPN / FIFA.com | All 104 matches |
| Stadium coordinates | Wikipedia | Decimal degrees |
| Historical weather | Open-Meteo Archive API | No API key required |
| Forecast weather | Open-Meteo Forecast API | No API key required |
| ELO ratings | eloratings.net (pre-tournament estimates) | Approximate; not updated mid-tournament |
| Attendance | footballgroundguide.com | Partial |

---

## Key Findings — Completed Matches (n = 36)

- **Rain has no significant effect on goals** — r = +0.071, p = 0.719. Rain vs dry: 3.22 vs 2.95 goals (p = 0.759).
- **Heat shows the strongest weather trend** — wet-bulb temperature r = +0.316, p = 0.101; not yet significant at n = 28.
- **Continental matchup is the only statistically significant finding** — same-confederation matches: 5.67 goals vs 2.79 inter-confederation (p = 0.011).
- **ELO is the strongest structural predictor** — larger pre-tournament rating gaps correlate with larger goal margins.
- **No ML model outperforms the sample mean** — all CV R2 are negative at n = 28. Expected at this sample size.
- **Cooling break threshold not reached** — no match exceeded WBGT = 28°C in the 28 confirmed-weather matches.

---

## Prediction Outputs — Upcoming Matches

For each scheduled match, the pipeline generates:

| Output Field | Description | Method |
|--------------|-------------|--------|
| `predicted_total_goals` | Expected combined goals | RandomForest regression |
| `probability_over_2_5_goals` | P(total goals > 2.5) | Poisson model on predicted mean |
| `forecast_temperature_c` | Air temperature at kickoff (degrees C) | Open-Meteo Forecast API |
| `forecast_precipitation_mm` | Rainfall at kickoff hour (mm) | Open-Meteo Forecast API |
| `forecast_heat_index_c` | Apparent temperature (degrees C) | Rothfusz formula on forecast data |
| `forecast_wet_bulb_c` | Wet-bulb temperature (degrees C) | Stull 2011 on forecast data |
| `forecast_wbgt_c` | Heat stress index (degrees C) | WBGT = 0.7*WB + 0.3*T |

Predictions refresh each time `pipeline.py` runs. Forecast accuracy improves within 7 days of kickoff.
Knockout predictions are generated once both teams are confirmed.

---

## Repository Structure

```
FIFA_analysis/
|
+-- README.md                          Project overview, findings, prediction workflow
+-- requirements.txt                   Python dependencies
+-- .gitignore
|
+-- data/
|   +-- raw/                           Completed-match outputs (official results only)
|   |   +-- match_metadata.csv         36 completed matches: venue, kickoff, goals
|   |   +-- team_match_stats.csv       72 rows: team-level goals and results
|   +-- external/                      Full-tournament reference data
|   |   +-- world_cup_matches.csv      Master schedule: all 104 matches (Completed/Scheduled/TBD)
|   |   +-- match_locations.csv        16 stadiums: lat, lon, capacity, timezone
|   +-- processed/                     Feature-enriched datasets
|   |   +-- weather_data.csv           Archive weather + heat stress metrics (28 matches)
|   |   +-- modeling_dataset.csv       ML-ready: merged features + ELO + rolling averages
|   +-- final/                         Model outputs and forecasts
|       +-- prediction_results.csv     CV model comparison (R2, MAE, RMSE)
|       +-- remaining_match_forecasts.csv  Forecast weather + predicted goals (upcoming matches)
|
+-- notebooks/
|   +-- 01_data_collection.ipynb       API calls, pipeline logic, raw data ingestion
|   +-- 02_data_quality.ipynb          Data quality: completeness, consistency, schema validation
|   +-- 03_weather_analysis.ipynb      Rain, heat index, wet-bulb vs goals + correlation matrix
|   +-- 04_match_analysis.ipynb        Kickoff time, stadium effects, attendance vs goals
|   +-- 05_confederation_analysis.ipynb  Only significant finding: same-confederation = 103% more goals
|   +-- 06_predictive_modeling.ipynb   RF feature importance, model comparison, why R2 is negative
|   +-- 07_future_predictions.ipynb    Forecast weather + predicted goals for upcoming matches
|   +-- 08_linkedin_insights.ipynb     3 key findings for non-technical audiences
|
+-- src/
|   +-- pipeline.py                    Full pipeline: fetch weather, engineer features, predict
|   +-- build_dataset.py               Build 104-match schedule CSV from fixture data
|
+-- docs/
    +-- data_dictionary.md             Column docs with type, description, availability per match status
```

---

## Setup & How to Run

```bash
pip install -r requirements.txt
```

No API keys required. All weather data from the free Open-Meteo API.

### Run the full pipeline (historical + forecasts)

```bash
python src/pipeline.py
```

Fetches archive weather for completed matches, forecast weather for upcoming matches, computes heat stress metrics for all, trains models on historical data, and writes all output files.

### Build the 104-match schedule

```bash
python src/build_dataset.py
```

### Open notebooks

```bash
jupyter lab
```

Recommended order: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08

### Re-execute notebooks headless

```bash
python -m nbconvert --to notebook --execute --inplace notebooks/01_data_collection.ipynb
python -m nbconvert --to notebook --execute --inplace notebooks/02_data_quality.ipynb
python -m nbconvert --to notebook --execute --inplace notebooks/03_weather_analysis.ipynb
```

---

## Statistical Highlights

### Weather vs Goals (n = 28 matches with confirmed weather data)

| Variable | Pearson r | p-value | Note |
|----------|-----------|---------|------|
| Wet-Bulb Temperature | +0.316 | 0.101 | Strongest weather signal |
| Heat Index | +0.287 | 0.139 | |
| WBGT | +0.276 | 0.155 | |
| Humidity | +0.197 | 0.316 | |
| Kickoff Hour | +0.197 | 0.251 | |
| ELO Difference | +0.182 | 0.287 | |
| Temperature | +0.135 | 0.494 | |
| Precipitation | -0.133 | 0.501 | |
| Rain Flag | +0.071 | 0.719 | Near-zero effect |

No variable reaches p < 0.05 at n = 28. Rerun after the Final (n = 104).

---

## Heat Stress Methodology

**Heat Index** (NOAA Rothfusz — valid when T >= 27 degrees C and RH >= 40%):

```
HI_F = -42.379 + 2.049*T + 10.143*RH - 0.225*T*RH - 6.84e-3*T^2
       - 5.39e-2*RH^2 + 1.23e-3*T^2*RH + 8.53e-4*T*RH^2 - 1.99e-6*T^2*RH^2
HI_C  = (HI_F - 32) * 5/9
```

Outside valid range: `heat_index_c = temperature_c`

**Wet-Bulb Temperature** (Stull 2011):

```
WB = T*atan(0.151977*(RH+8.313659)^0.5) + atan(T+RH)
   - atan(RH-1.676331) + 0.00391838*RH^1.5*atan(0.023101*RH) - 4.686035
```

**WBGT (simplified shade):** `WBGT = 0.7*WB + 0.3*T`

**FIFA cooling break:** triggered when WBGT >= 28 degrees C. Not reached in any MD1/MD2 match.

---

## Limitations

1. **Sample size (n = 28 with confirmed weather):** Insufficient statistical power. Conclusions are directional only until n = 104.
2. **Covered stadiums:** NRG (Houston), AT&T (Arlington), Mercedes-Benz (Atlanta), BC Place (Vancouver) have retractable or fixed roofs. Outdoor API weather may not match in-stadium conditions.
3. **Forecast accuracy:** Open-Meteo forecasts beyond 7 days degrade. Rerun `pipeline.py` closer to each match date for better predictions.
4. **TBD teams:** Knockout predictions cannot be generated until both teams are confirmed after their group stage concludes.
5. **ELO ratings:** Pre-tournament approximations; not updated after each match.
6. **Synthetic data:** Cards, passes, shots, xG, and distance covered are simulated from historical WC distributions, not official match data.
7. **Model underfitting:** All CV R2 negative at n = 28. The sample mean (~3.0 goals/match) is the correct null predictor at this stage.

---

## Answer to the Research Question

> **Is there a relationship between rainfall during a match and the number of goals scored?**

**No statistically significant relationship was found (r = +0.071, p = 0.719, Cohen's d = -0.15) in the 28 confirmed-weather matches.**

Heat stress shows a modest positive trend (r ~ +0.28-0.32) but does not reach significance at this sample size. The continental matchup effect (p = 0.011) is the strongest finding to date. The full 104-match dataset (available after July 19) will provide approximately 4x more statistical power and may shift these conclusions.

---

*Data: Open-Meteo API (free, no key) | Analysis: Python / pandas / scikit-learn | Visualisation: matplotlib / seaborn*  
*Tournament in progress — data and forecasts updated as matches are played.*
