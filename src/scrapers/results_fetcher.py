"""
results_fetcher.py
==================
Fetches FIFA World Cup 2026 match results from the ESPN scoreboard API.
No API key required.

Public API:
    fetch_results(date_str: str) -> list[dict]
    normalize_team_name(name: str) -> str
"""

import time
import logging
import requests

logger = logging.getLogger(__name__)

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# ESPN display name → internal project name
ESPN_TEAM_MAP = {
    "Bosnia & Herzegovina":    "Bosnia-Herzegovina",
    "Bosnia-Herzegovina":      "Bosnia-Herzegovina",
    "Congo DR":                "DR Congo",
    "DR Congo":                "DR Congo",
    "Congo, DR":               "DR Congo",
    "Cote d'Ivoire":           "Ivory Coast",
    "Côte d'Ivoire":           "Ivory Coast",
    "Ivory Coast":             "Ivory Coast",
    "Korea Republic":          "South Korea",
    "South Korea":             "South Korea",
    "Republic of Korea":       "South Korea",
    "Iran":                    "Iran",
    "IR Iran":                 "Iran",
    "USA":                     "USA",
    "United States":           "USA",
    "Czech Republic":          "Czechia",
    "Czechia":                 "Czechia",
    "New Zealand":             "New Zealand",
    "New Zealand (NZ)":        "New Zealand",
    "Saudi Arabia":            "Saudi Arabia",
    "KSA":                     "Saudi Arabia",
    "Cape Verde":              "Cape Verde",
    "Cape Verde Islands":      "Cape Verde",
    "South Africa":            "South Africa",
    "Uzbekistan":              "Uzbekistan",
    "Curacao":                 "Curacao",
    "Curaçao":                 "Curacao",
    "Jordan":                  "Jordan",
    "Mexico":                  "Mexico",
    "Canada":                  "Canada",
    "France":                  "France",
    "Germany":                 "Germany",
    "Brazil":                  "Brazil",
    "Argentina":               "Argentina",
    "England":                 "England",
    "Portugal":                "Portugal",
    "Spain":                   "Spain",
    "Netherlands":             "Netherlands",
    "Belgium":                 "Belgium",
    "Morocco":                 "Morocco",
    "Japan":                   "Japan",
    "Switzerland":             "Switzerland",
    "Australia":               "Australia",
    "Senegal":                 "Senegal",
    "Turkey":                  "Turkiye",
    "Turkiye":                 "Turkiye",
    "Norway":                  "Norway",
    "Ecuador":                 "Ecuador",
    "Sweden":                  "Sweden",
    "Algeria":                 "Algeria",
    "Austria":                 "Austria",
    "Tunisia":                 "Tunisia",
    "Ghana":                   "Ghana",
    "Egypt":                   "Egypt",
    "Scotland":                "Scotland",
    "Iraq":                    "Iraq",
    "Croatia":                 "Croatia",
    "Colombia":                "Colombia",
    "Uruguay":                 "Uruguay",
    "Paraguay":                "Paraguay",
    "Qatar":                   "Qatar",
    "Haiti":                   "Haiti",
    "Panama":                  "Panama",
}


def normalize_team_name(name: str) -> str:
    """Normalize an ESPN team name to the project's internal name."""
    if not name:
        return name
    return ESPN_TEAM_MAP.get(name.strip(), name.strip())


def fetch_results(date_str: str, retries: int = 3, delay: float = 5.0) -> list:
    """
    Fetch all FIFA World Cup matches for a given date from ESPN.

    Args:
        date_str: Date in YYYY-MM-DD format.
        retries:  Number of retry attempts on failure.
        delay:    Seconds to wait between retries.

    Returns:
        List of dicts, one per completed match:
        {
            "home_team":   str,
            "away_team":   str,
            "home_goals":  int,
            "away_goals":  int,
            "completed":   bool,
            "match_date":  str,   # YYYY-MM-DD
            "venue":       str,   # stadium name or ""
            "city":        str,
        }
    """
    espn_date = date_str.replace("-", "")   # YYYYMMDD format
    params = {"dates": espn_date}

    for attempt in range(retries):
        try:
            resp = requests.get(SCOREBOARD_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return _parse_scoreboard(data, date_str)
        except requests.RequestException as e:
            logger.warning(f"ESPN fetch failed (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)

    logger.error(f"ESPN fetch failed after {retries} attempts for {date_str}")
    return []


def _parse_scoreboard(data: dict, date_str: str) -> list:
    """Parse ESPN scoreboard JSON into normalized match result dicts."""
    results = []
    events = data.get("events", [])

    for event in events:
        competitions = event.get("competitions", [])
        if not competitions:
            continue
        comp = competitions[0]

        status = comp.get("status", {})
        status_type = status.get("type", {})
        completed = bool(status_type.get("completed", False))

        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home_name = normalize_team_name(home.get("team", {}).get("displayName", ""))
        away_name = normalize_team_name(away.get("team", {}).get("displayName", ""))

        try:
            home_goals = int(home.get("score", 0) or 0)
            away_goals = int(away.get("score", 0) or 0)
        except (ValueError, TypeError):
            home_goals = 0
            away_goals = 0

        venue_info = comp.get("venue", {})
        venue_name = venue_info.get("fullName", "")
        venue_address = venue_info.get("address", {})
        city = venue_address.get("city", "")

        results.append({
            "home_team":  home_name,
            "away_team":  away_name,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "completed":  completed,
            "match_date": date_str,
            "venue":      venue_name,
            "city":       city,
        })

    return results


def find_match(results: list, home_team: str, away_team: str) -> dict | None:
    """
    Find a result for a specific match. Tries exact name match, then
    falls back to case-insensitive prefix match for robustness.
    """
    home_norm = normalize_team_name(home_team)
    away_norm = normalize_team_name(away_team)

    for r in results:
        if r["home_team"] == home_norm and r["away_team"] == away_norm:
            return r

    # Case-insensitive fallback
    for r in results:
        if (r["home_team"].lower() == home_norm.lower() and
                r["away_team"].lower() == away_norm.lower()):
            return r

    return None
