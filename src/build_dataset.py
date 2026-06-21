"""
FIFA World Cup 2026 — Complete Dataset Builder
Sources: ESPN (primary schedule), FIFA.com, Wikipedia
Data current as of: 2026-06-21 (MD2 complete for Groups A-F; MD2 for G-L starts today)
"""

import csv, os, math
from datetime import datetime, timezone, timedelta

from pathlib import Path as _Path
_ROOT = _Path(__file__).parent.parent.parent
BASE = str(_ROOT)

# ─── STADIUM MASTER ────────────────────────────────────────────────────────────
STADIUMS = {
    "Estadio Azteca":          {"city":"Mexico City",   "country":"Mexico",  "lat":19.3029,  "lon":-99.1500,  "cap":87523, "tz_name":"America/Mexico_City",  "utc_offset":-6},
    "Estadio Akron":           {"city":"Zapopan",       "country":"Mexico",  "lat":20.6898,  "lon":-103.4672, "cap":44985, "tz_name":"America/Mexico_City",  "utc_offset":-6},
    "Estadio BBVA":            {"city":"Guadalupe",     "country":"Mexico",  "lat":25.6694,  "lon":-100.2437, "cap":53500, "tz_name":"America/Mexico_City",  "utc_offset":-6},
    "BMO Field":               {"city":"Toronto",       "country":"Canada",  "lat":43.6333,  "lon":-79.4167,  "cap":45000, "tz_name":"America/Toronto",      "utc_offset":-4},
    "SoFi Stadium":            {"city":"Inglewood",     "country":"USA",     "lat":33.9535,  "lon":-118.3392, "cap":70240, "tz_name":"America/Los_Angeles",  "utc_offset":-7},
    "MetLife Stadium":         {"city":"East Rutherford","country":"USA",    "lat":40.8136,  "lon":-74.0742,  "cap":82500, "tz_name":"America/New_York",     "utc_offset":-4},
    "Gillette Stadium":        {"city":"Foxborough",    "country":"USA",     "lat":42.0909,  "lon":-71.2643,  "cap":65878, "tz_name":"America/New_York",     "utc_offset":-4},
    "BC Place":                {"city":"Vancouver",     "country":"Canada",  "lat":49.2767,  "lon":-123.1115, "cap":54500, "tz_name":"America/Vancouver",    "utc_offset":-7},
    "Levi's Stadium":          {"city":"Santa Clara",   "country":"USA",     "lat":37.4032,  "lon":-121.9697, "cap":70909, "tz_name":"America/Los_Angeles",  "utc_offset":-7},
    "NRG Stadium":             {"city":"Houston",       "country":"USA",     "lat":29.6847,  "lon":-95.4107,  "cap":72220, "tz_name":"America/Chicago",      "utc_offset":-5},
    "Lincoln Financial Field": {"city":"Philadelphia",  "country":"USA",     "lat":39.9008,  "lon":-75.1675,  "cap":69176, "tz_name":"America/New_York",     "utc_offset":-4},
    "AT&T Stadium":            {"city":"Arlington",     "country":"USA",     "lat":32.7480,  "lon":-97.0930,  "cap":80000, "tz_name":"America/Chicago",      "utc_offset":-5},
    "Mercedes-Benz Stadium":   {"city":"Atlanta",       "country":"USA",     "lat":33.7555,  "lon":-84.4010,  "cap":71000, "tz_name":"America/New_York",     "utc_offset":-4},
    "Lumen Field":             {"city":"Seattle",       "country":"USA",     "lat":47.5952,  "lon":-122.3316, "cap":69000, "tz_name":"America/Los_Angeles",  "utc_offset":-7},
    "Hard Rock Stadium":       {"city":"Miami Gardens", "country":"USA",     "lat":25.9580,  "lon":-80.2389,  "cap":64767, "tz_name":"America/New_York",     "utc_offset":-4},
    "Arrowhead Stadium":       {"city":"Kansas City",   "country":"USA",     "lat":39.0489,  "lon":-94.4839,  "cap":76416, "tz_name":"America/Chicago",      "utc_offset":-5},
}

def utc_time(local_hhmm, stadium):
    h, m = int(local_hhmm[:2]), int(local_hhmm[3:])
    offset = STADIUMS[stadium]["utc_offset"]
    utc_h = (h - offset) % 24
    return f"{utc_h:02d}:{m:02d}"

def winner(hg, ag, ht, at):
    if hg == "" or ag == "":
        return ""
    hg, ag = int(hg), int(ag)
    if hg > ag: return ht
    if ag > hg: return at
    return "Draw"

# ─── ALL MATCHES ───────────────────────────────────────────────────────────────
# Columns: match_id, stage, group, match_date, kickoff_time_local, kickoff_time_utc,
#          timezone, home_team, away_team, home_goals, away_goals, winner,
#          stadium, city, country, stadium_capacity, match_status

MATCHES = [
# ══ GROUP STAGE — MATCHDAY 1 (completed Jun 11-17) ══════════════════════════
# Group A
("WC2026-001","Group Stage","A","2026-06-11","20:00","","","Mexico","South Africa",2,0,"Estadio Azteca","Completed"),
("WC2026-002","Group Stage","A","2026-06-11","20:00","","","South Korea","Czechia",2,1,"Estadio Akron","Completed"),
# Group B
("WC2026-003","Group Stage","B","2026-06-12","19:00","","","Canada","Bosnia-Herzegovina",1,1,"BMO Field","Completed"),
# Group D
("WC2026-004","Group Stage","D","2026-06-12","15:00","","","USA","Paraguay",4,1,"SoFi Stadium","Completed"),
# Group B cont.
("WC2026-005","Group Stage","B","2026-06-13","20:00","","","Switzerland","Qatar",1,1,"Levi's Stadium","Completed"),
# Group C
("WC2026-006","Group Stage","C","2026-06-13","14:00","","","Brazil","Morocco",1,1,"MetLife Stadium","Completed"),
("WC2026-007","Group Stage","C","2026-06-13","17:00","","","Scotland","Haiti",1,0,"Gillette Stadium","Completed"),
# Group D cont.
("WC2026-008","Group Stage","D","2026-06-13","16:00","","","Australia","Turkiye",2,0,"BC Place","Completed"),
# Group E
("WC2026-009","Group Stage","E","2026-06-14","14:00","","","Germany","Curacao",7,1,"NRG Stadium","Completed"),
# Group F
("WC2026-010","Group Stage","F","2026-06-14","14:00","","","Netherlands","Japan",2,2,"AT&T Stadium","Completed"),
# Group E cont.
("WC2026-011","Group Stage","E","2026-06-14","17:00","","","Ivory Coast","Ecuador",1,0,"Lincoln Financial Field","Completed"),
# Group F cont.
("WC2026-012","Group Stage","F","2026-06-14","20:00","","","Sweden","Tunisia",5,1,"Estadio BBVA","Completed"),
# Group H
("WC2026-013","Group Stage","H","2026-06-15","12:00","","","Spain","Cape Verde",0,0,"Mercedes-Benz Stadium","Completed"),
# Group G
("WC2026-014","Group Stage","G","2026-06-15","14:00","","","Belgium","Egypt",1,1,"Lumen Field","Completed"),
# Group H cont.
("WC2026-015","Group Stage","H","2026-06-15","18:00","","","Saudi Arabia","Uruguay",1,1,"Hard Rock Stadium","Completed"),
# Group G cont.
("WC2026-016","Group Stage","G","2026-06-15","18:00","","","Iran","New Zealand",2,2,"SoFi Stadium","Completed"),
# Group I
("WC2026-017","Group Stage","I","2026-06-16","14:00","","","France","Senegal",3,1,"MetLife Stadium","Completed"),
("WC2026-018","Group Stage","I","2026-06-16","17:00","","","Norway","Iraq",4,1,"Gillette Stadium","Completed"),
# Group J
("WC2026-019","Group Stage","J","2026-06-16","18:00","","","Argentina","Algeria",3,0,"Arrowhead Stadium","Completed"),
("WC2026-020","Group Stage","J","2026-06-16","20:00","","","Austria","Jordan",3,1,"Levi's Stadium","Completed"),
# Group K
("WC2026-021","Group Stage","K","2026-06-17","14:00","","","Portugal","DR Congo",1,1,"NRG Stadium","Completed"),
# Group L
("WC2026-022","Group Stage","L","2026-06-17","14:00","","","England","Croatia",4,2,"AT&T Stadium","Completed"),
("WC2026-023","Group Stage","L","2026-06-17","19:00","","","Ghana","Panama",1,0,"BMO Field","Completed"),
# Group K cont.
("WC2026-024","Group Stage","K","2026-06-17","20:00","","","Uzbekistan","Colombia",1,3,"Estadio Azteca","Completed"),

# ══ GROUP STAGE — MATCHDAY 2 (completed Jun 18-20, Groups A-F) ══════════════
("WC2026-025","Group Stage","A","2026-06-18","12:00","","","Czechia","South Africa",1,1,"Mercedes-Benz Stadium","Completed"),
("WC2026-026","Group Stage","B","2026-06-18","12:00","","","Switzerland","Bosnia-Herzegovina",4,1,"SoFi Stadium","Completed"),
("WC2026-027","Group Stage","B","2026-06-18","16:00","","","Canada","Qatar",6,0,"BC Place","Completed"),
("WC2026-028","Group Stage","A","2026-06-18","20:00","","","Mexico","South Korea",1,0,"Estadio Akron","Completed"),
("WC2026-029","Group Stage","D","2026-06-19","14:00","","","USA","Australia",2,0,"Lumen Field","Completed"),
("WC2026-030","Group Stage","C","2026-06-19","14:00","","","Scotland","Morocco",0,1,"Gillette Stadium","Completed"),
("WC2026-031","Group Stage","C","2026-06-19","17:00","","","Brazil","Haiti",3,0,"Lincoln Financial Field","Completed"),
("WC2026-032","Group Stage","D","2026-06-19","20:00","","","Turkiye","Paraguay",0,1,"Levi's Stadium","Completed"),
("WC2026-033","Group Stage","F","2026-06-20","14:00","","","Netherlands","Sweden",5,1,"NRG Stadium","Completed"),
("WC2026-034","Group Stage","E","2026-06-20","19:00","","","Germany","Ivory Coast",2,1,"BMO Field","Completed"),
("WC2026-035","Group Stage","E","2026-06-20","18:00","","","Ecuador","Curacao",0,0,"Arrowhead Stadium","Completed"),
("WC2026-036","Group Stage","F","2026-06-20","20:00","","","Japan","Tunisia",4,0,"Estadio BBVA","Completed"),

# ══ GROUP STAGE — MATCHDAY 2 (scheduled Jun 21-23, Groups G-L) ══════════════
# Jun 21 — Groups G, H
("WC2026-037","Group Stage","H","2026-06-21","12:00","","","Spain","Saudi Arabia","","","Mercedes-Benz Stadium","Scheduled"),
("WC2026-038","Group Stage","G","2026-06-21","12:00","","","Belgium","Iran","","","SoFi Stadium","Scheduled"),
("WC2026-039","Group Stage","H","2026-06-21","18:00","","","Uruguay","Cape Verde","","","Hard Rock Stadium","Scheduled"),
("WC2026-040","Group Stage","G","2026-06-21","18:00","","","New Zealand","Egypt","","","BC Place","Scheduled"),
# Jun 22 — Groups I, J
("WC2026-041","Group Stage","J","2026-06-22","12:00","","","Argentina","Austria","","","AT&T Stadium","Scheduled"),
("WC2026-042","Group Stage","I","2026-06-22","17:00","","","France","Iraq","","","Lincoln Financial Field","Scheduled"),
("WC2026-043","Group Stage","I","2026-06-22","20:00","","","Norway","Senegal","","","MetLife Stadium","Scheduled"),
("WC2026-044","Group Stage","J","2026-06-22","20:00","","","Jordan","Algeria","","","Levi's Stadium","Scheduled"),
# Jun 23 — Groups K, L
("WC2026-045","Group Stage","K","2026-06-23","12:00","","","Portugal","Uzbekistan","","","NRG Stadium","Scheduled"),
("WC2026-046","Group Stage","L","2026-06-23","16:00","","","England","Ghana","","","Gillette Stadium","Scheduled"),
("WC2026-047","Group Stage","L","2026-06-23","19:00","","","Panama","Croatia","","","BMO Field","Scheduled"),
("WC2026-048","Group Stage","K","2026-06-23","20:00","","","Colombia","DR Congo","","","Estadio Akron","Scheduled"),

# ══ GROUP STAGE — MATCHDAY 3 (scheduled Jun 24-27) ═══════════════════════════
# Jun 24 — Groups A, B, C (simultaneous within group)
("WC2026-049","Group Stage","B","2026-06-24","12:00","","","Switzerland","Canada","","","BC Place","Scheduled"),
("WC2026-050","Group Stage","B","2026-06-24","12:00","","","Bosnia-Herzegovina","Qatar","","","Lumen Field","Scheduled"),
("WC2026-051","Group Stage","C","2026-06-24","18:00","","","Scotland","Brazil","","","Hard Rock Stadium","Scheduled"),
("WC2026-052","Group Stage","C","2026-06-24","18:00","","","Morocco","Haiti","","","Mercedes-Benz Stadium","Scheduled"),
("WC2026-053","Group Stage","A","2026-06-24","19:00","","","Czechia","Mexico","","","Estadio Azteca","Scheduled"),
("WC2026-054","Group Stage","A","2026-06-24","19:00","","","South Africa","South Korea","","","Estadio BBVA","Scheduled"),
# Jun 25 — Groups D, E, F
("WC2026-055","Group Stage","E","2026-06-25","16:00","","","Ecuador","Germany","","","MetLife Stadium","Scheduled"),
("WC2026-056","Group Stage","E","2026-06-25","16:00","","","Curacao","Ivory Coast","","","Lincoln Financial Field","Scheduled"),
("WC2026-057","Group Stage","F","2026-06-25","18:00","","","Japan","Sweden","","","AT&T Stadium","Scheduled"),
("WC2026-058","Group Stage","F","2026-06-25","18:00","","","Tunisia","Netherlands","","","Arrowhead Stadium","Scheduled"),
("WC2026-059","Group Stage","D","2026-06-25","19:00","","","Turkiye","USA","","","SoFi Stadium","Scheduled"),
("WC2026-060","Group Stage","D","2026-06-25","19:00","","","Paraguay","Australia","","","Levi's Stadium","Scheduled"),
# Jun 26 — Groups G, H, I
("WC2026-061","Group Stage","I","2026-06-26","15:00","","","Norway","France","","","Gillette Stadium","Scheduled"),
("WC2026-062","Group Stage","I","2026-06-26","15:00","","","Senegal","Iraq","","","BMO Field","Scheduled"),
("WC2026-063","Group Stage","H","2026-06-26","19:00","","","Cape Verde","Saudi Arabia","","","NRG Stadium","Scheduled"),
("WC2026-064","Group Stage","H","2026-06-26","18:00","","","Uruguay","Spain","","","Estadio Akron","Scheduled"),
("WC2026-065","Group Stage","G","2026-06-26","20:00","","","Egypt","Iran","","","Lumen Field","Scheduled"),
("WC2026-066","Group Stage","G","2026-06-26","20:00","","","New Zealand","Belgium","","","BC Place","Scheduled"),
# Jun 27 — Groups J, K, L
("WC2026-067","Group Stage","L","2026-06-27","17:00","","","Panama","England","","","MetLife Stadium","Scheduled"),
("WC2026-068","Group Stage","L","2026-06-27","17:00","","","Croatia","Ghana","","","Lincoln Financial Field","Scheduled"),
("WC2026-069","Group Stage","K","2026-06-27","19:30","","","Colombia","Portugal","","","Hard Rock Stadium","Scheduled"),
("WC2026-070","Group Stage","K","2026-06-27","19:30","","","DR Congo","Uzbekistan","","","Mercedes-Benz Stadium","Scheduled"),
("WC2026-071","Group Stage","J","2026-06-27","21:00","","","Algeria","Austria","","","Arrowhead Stadium","Scheduled"),
("WC2026-072","Group Stage","J","2026-06-27","21:00","","","Jordan","Argentina","","","AT&T Stadium","Scheduled"),

# ══ ROUND OF 32 (Jun 28 – Jul 3) — Teams TBD after group stage ══════════════
("WC2026-073","Round of 32","","2026-06-28","12:00","","","Grp-A Runner-up","Grp-B Runner-up","","","SoFi Stadium","TBD"),
("WC2026-074","Round of 32","","2026-06-29","12:00","","","Grp-C Winner","Grp-F Runner-up","","","NRG Stadium","TBD"),
("WC2026-075","Round of 32","","2026-06-29","16:30","","","Grp-E Winner","Best 3rd TBD","","","Gillette Stadium","TBD"),
("WC2026-076","Round of 32","","2026-06-29","19:00","","","Grp-F Winner","Grp-C Runner-up","","","Estadio BBVA","TBD"),
("WC2026-077","Round of 32","","2026-06-30","12:00","","","Grp-E Runner-up","Grp-I Runner-up","","","AT&T Stadium","TBD"),
("WC2026-078","Round of 32","","2026-06-30","17:00","","","Grp-I Winner","Best 3rd TBD","","","MetLife Stadium","TBD"),
("WC2026-079","Round of 32","","2026-06-30","19:00","","","Grp-A Winner","Best 3rd TBD","","","Estadio Azteca","TBD"),
("WC2026-080","Round of 32","","2026-07-01","12:00","","","Grp-L Winner","Best 3rd TBD","","","Mercedes-Benz Stadium","TBD"),
("WC2026-081","Round of 32","","2026-07-01","13:00","","","Grp-G Winner","Best 3rd TBD","","","Lumen Field","TBD"),
("WC2026-082","Round of 32","","2026-07-01","17:00","","","Grp-D Winner","Best 3rd TBD","","","Levi's Stadium","TBD"),
("WC2026-083","Round of 32","","2026-07-02","12:00","","","Grp-H Winner","Grp-J Runner-up","","","SoFi Stadium","TBD"),
("WC2026-084","Round of 32","","2026-07-02","19:00","","","Grp-K Runner-up","Grp-L Runner-up","","","BMO Field","TBD"),
("WC2026-085","Round of 32","","2026-07-02","20:00","","","Grp-B Winner","Best 3rd TBD","","","BC Place","TBD"),
("WC2026-086","Round of 32","","2026-07-03","12:00","","","Grp-D Runner-up","Grp-G Runner-up","","","AT&T Stadium","TBD"),
("WC2026-087","Round of 32","","2026-07-03","18:00","","","Grp-J Winner","Grp-H Runner-up","","","Hard Rock Stadium","TBD"),
("WC2026-088","Round of 32","","2026-07-03","20:30","","","Grp-K Winner","Best 3rd TBD","","","Arrowhead Stadium","TBD"),

# ══ ROUND OF 16 (Jul 4-7) ════════════════════════════════════════════════════
("WC2026-089","Round of 16","","2026-07-04","12:00","","","TBD","TBD","","","NRG Stadium","TBD"),
("WC2026-090","Round of 16","","2026-07-04","17:00","","","TBD","TBD","","","Lincoln Financial Field","TBD"),
("WC2026-091","Round of 16","","2026-07-05","16:00","","","TBD","TBD","","","MetLife Stadium","TBD"),
("WC2026-092","Round of 16","","2026-07-05","18:00","","","TBD","TBD","","","Estadio Azteca","TBD"),
("WC2026-093","Round of 16","","2026-07-06","14:00","","","TBD","TBD","","","AT&T Stadium","TBD"),
("WC2026-094","Round of 16","","2026-07-06","14:00","","","TBD","TBD","","","Lumen Field","TBD"),
("WC2026-095","Round of 16","","2026-07-07","12:00","","","TBD","TBD","","","Mercedes-Benz Stadium","TBD"),
("WC2026-096","Round of 16","","2026-07-07","13:00","","","TBD","TBD","","","BC Place","TBD"),

# ══ QUARTER-FINALS (Jul 9-11) ════════════════════════════════════════════════
("WC2026-097","Quarter-Final","","2026-07-09","16:00","","","TBD","TBD","","","Gillette Stadium","TBD"),
("WC2026-098","Quarter-Final","","2026-07-10","12:00","","","TBD","TBD","","","SoFi Stadium","TBD"),
("WC2026-099","Quarter-Final","","2026-07-11","17:00","","","TBD","TBD","","","Hard Rock Stadium","TBD"),
("WC2026-100","Quarter-Final","","2026-07-11","20:00","","","TBD","TBD","","","Arrowhead Stadium","TBD"),

# ══ SEMI-FINALS (Jul 14-15) ══════════════════════════════════════════════════
("WC2026-101","Semi-Final","","2026-07-14","14:00","","","TBD","TBD","","","AT&T Stadium","TBD"),
("WC2026-102","Semi-Final","","2026-07-15","15:00","","","TBD","TBD","","","Mercedes-Benz Stadium","TBD"),

# ══ THIRD PLACE (Jul 18) ═════════════════════════════════════════════════════
("WC2026-103","Third Place","","2026-07-18","17:00","","","TBD","TBD","","","Hard Rock Stadium","TBD"),

# ══ FINAL (Jul 19) ═══════════════════════════════════════════════════════════
("WC2026-104","Final","","2026-07-19","15:00","","","TBD","TBD","","","MetLife Stadium","TBD"),
]

# ─── FILL IN UTC AND TIMEZONE FIELDS ──────────────────────────────────────────
def enrich(row):
    mid, stage, grp, date, kick_local, _, _, home, away, hg, ag, stadium, status = row
    s = STADIUMS[stadium]
    tz_name  = s["tz_name"]
    utc_off  = s["utc_offset"]
    h, m = int(kick_local[:2]), int(kick_local[3:])
    utc_h = (h - utc_off) % 24
    kick_utc = f"{utc_h:02d}:{m:02d}"
    city    = s["city"]
    country = s["country"]
    cap     = s["cap"]
    # winner
    if hg == "" or ag == "":
        win = ""
    else:
        hg_i, ag_i = int(hg), int(ag)
        if hg_i > ag_i: win = home
        elif ag_i > hg_i: win = away
        else: win = "Draw"
    hg_str = str(hg) if hg != "" else ""
    ag_str = str(ag) if ag != "" else ""
    return {
        "match_id": mid, "stage": stage, "group": grp,
        "match_date": date, "kickoff_time_local": kick_local,
        "kickoff_time_utc": kick_utc, "timezone": tz_name,
        "home_team": home, "away_team": away,
        "home_goals": hg_str, "away_goals": ag_str,
        "winner": win, "stadium": stadium, "city": city,
        "country": country, "stadium_capacity": cap,
        "match_status": status,
    }

records = [enrich(r) for r in MATCHES]

# ─── WRITE world_cup_matches.csv ───────────────────────────────────────────────
MATCH_COLS = ["match_id","stage","group","match_date","kickoff_time_local",
              "kickoff_time_utc","timezone","home_team","away_team",
              "home_goals","away_goals","winner","stadium","city","country",
              "stadium_capacity","match_status"]

p1 = str(_Path(BASE) / "data" / "external" / "world_cup_matches.csv")
with open(p1, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=MATCH_COLS)
    w.writeheader()
    w.writerows(records)
print(f"Written: {p1}  ({len(records)} rows)")

# ─── WRITE future_matches.csv ─────────────────────────────────────────────────
FUTURE_COLS = ["match_id","stage","group","match_date","kickoff_time_local",
               "kickoff_time_utc","timezone","home_team","away_team",
               "stadium","city","country","stadium_capacity"]

future = [r for r in records if r["match_status"] in ("Scheduled","TBD")]
p2 = str(_Path(BASE) / "data" / "external" / "future_matches.csv")
with open(p2, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FUTURE_COLS)
    w.writeheader()
    for r in future:
        w.writerow({k: r[k] for k in FUTURE_COLS})
print(f"Written: {p2}  ({len(future)} rows)")

# ─── WRITE tournament_timeline.csv ────────────────────────────────────────────
from collections import defaultdict
timeline = defaultdict(lambda: {"count":0,"stages":set(),"cities":set()})
for r in records:
    d = r["match_date"]
    timeline[d]["count"] += 1
    timeline[d]["stages"].add(r["stage"])
    timeline[d]["cities"].add(r["city"])

TIMELINE_COLS = ["date","number_of_matches","stages_played","cities_used"]
p3 = str(_Path(BASE) / "data" / "external" / "tournament_timeline.csv")
with open(p3, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=TIMELINE_COLS)
    w.writeheader()
    for d in sorted(timeline.keys()):
        t = timeline[d]
        w.writerow({
            "date": d,
            "number_of_matches": t["count"],
            "stages_played": " | ".join(sorted(t["stages"])),
            "cities_used": " | ".join(sorted(t["cities"])),
        })
print(f"Written: {p3}  ({len(timeline)} rows)")

# ─── WRITE match_locations.csv ────────────────────────────────────────────────
LOC_COLS = ["stadium","city","country","latitude","longitude",
            "stadium_capacity","timezone","utc_offset_hours"]
p4 = str(_Path(BASE) / "data" / "external" / "match_locations.csv")
with open(p4, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=LOC_COLS)
    w.writeheader()
    for name, s in STADIUMS.items():
        w.writerow({
            "stadium": name, "city": s["city"], "country": s["country"],
            "latitude": s["lat"], "longitude": s["lon"],
            "stadium_capacity": s["cap"],
            "timezone": s["tz_name"], "utc_offset_hours": s["utc_offset"],
        })
print(f"Written: {p4}  ({len(STADIUMS)} rows)")

# ─── VALIDATION REPORT ────────────────────────────────────────────────────────
print("\n" + "="*60)
print("VALIDATION REPORT")
print("="*60)

ids = [r["match_id"] for r in records]
print(f"1. Total records            : {len(records)} (expected 104)")
print(f"2. Unique match IDs         : {len(set(ids))} (expected 104)")
dup = [mid for mid in ids if ids.count(mid) > 1]
print(f"3. Duplicate match IDs      : {len(dup)}")

no_stage = [r["match_id"] for r in records if not r["stage"]]
print(f"4. Missing stage            : {len(no_stage)}")

no_city = [r["match_id"] for r in records if not r["city"]]
print(f"5. Missing city             : {len(no_city)}")

no_stadium = [r["match_id"] for r in records if not r["stadium"]]
print(f"6. Missing stadium          : {len(no_stadium)}")

completed = [r for r in records if r["match_status"] == "Completed"]
scheduled = [r for r in records if r["match_status"] == "Scheduled"]
tbd_list  = [r for r in records if r["match_status"] == "TBD"]
print(f"7. Completed matches        : {len(completed)}")
print(f"8. Scheduled (teams known)  : {len(scheduled)}")
print(f"9. TBD (teams unknown)      : {len(tbd_list)}")
print(f"10. Future total            : {len(scheduled)+len(tbd_list)}")

gs = [r for r in records if r["stage"]=="Group Stage"]
r32 = [r for r in records if r["stage"]=="Round of 32"]
r16 = [r for r in records if r["stage"]=="Round of 16"]
qf  = [r for r in records if r["stage"]=="Quarter-Final"]
sf  = [r for r in records if r["stage"]=="Semi-Final"]
tp  = [r for r in records if r["stage"]=="Third Place"]
fn  = [r for r in records if r["stage"]=="Final"]
print(f"11. Group Stage matches     : {len(gs)} (expected 72)")
print(f"12. Round of 32 matches     : {len(r32)} (expected 16)")
print(f"13. Round of 16 matches     : {len(r16)} (expected 8)")
print(f"14. Quarter-Finals          : {len(qf)} (expected 4)")
print(f"15. Semi-Finals             : {len(sf)} (expected 2)")
print(f"16. Third Place             : {len(tp)} (expected 1)")
print(f"17. Final                   : {len(fn)} (expected 1)")
print(f"18. Total                   : {len(gs)+len(r32)+len(r16)+len(qf)+len(sf)+len(tp)+len(fn)} (expected 104)")

# ─── SUMMARY STATISTICS ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY STATISTICS")
print("="*60)

total_goals = sum(int(r["home_goals"])+int(r["away_goals"])
                  for r in completed if r["home_goals"] != "")
avg_goals   = total_goals / len(completed) if completed else 0
print(f"Total goals scored so far   : {total_goals}")
print(f"Matches completed           : {len(completed)}")
print(f"Matches remaining           : {len(scheduled)+len(tbd_list)}")
print(f"Average goals per match     : {avg_goals:.2f}")

scored = [(r, int(r["home_goals"])+int(r["away_goals"]))
          for r in completed if r["home_goals"] != ""]
if scored:
    best = max(scored, key=lambda x: x[1])
    worst = min(scored, key=lambda x: x[1])
    print(f"Highest-scoring match       : {best[0]['home_team']} vs {best[0]['away_team']} ({best[0]['home_goals']}-{best[0]['away_goals']}) — {best[1]} goals")
    print(f"Lowest-scoring match        : {worst[0]['home_team']} vs {worst[0]['away_team']} ({worst[0]['home_goals']}-{worst[0]['away_goals']}) — {worst[1]} goals")

print("\nMatches by stage:")
for stage_name, lst in [("Group Stage",gs),("Round of 32",r32),("Round of 16",r16),
                          ("Quarter-Final",qf),("Semi-Final",sf),("Third Place",tp),("Final",fn)]:
    print(f"  {stage_name:18s}: {len(lst):3d}")

print("\nMatches by host city (group stage only):")
city_counts = defaultdict(int)
for r in records:
    city_counts[r["city"]] += 1
for city, cnt in sorted(city_counts.items(), key=lambda x: -x[1]):
    print(f"  {city:25s}: {cnt}")

print("\nMatches by kickoff hour (local, completed only):")
hour_counts = defaultdict(int)
for r in completed:
    h = int(r["kickoff_time_local"][:2])
    hour_counts[h] += 1
for h in sorted(hour_counts):
    print(f"  {h:02d}:00 local  : {hour_counts[h]} matches")

# ─── UPCOMING MATCHES FOR GOAL PREDICTION ─────────────────────────────────────
print("\n" + "="*60)
print("UPCOMING MATCHES FOR GOAL PREDICTION")
print("="*60)
print(f"{'#':<4} {'Match':<40} {'Date':<12} {'Local KO':<10} {'Stadium':<28} {'City'}")
print("-"*120)
for i, r in enumerate([r for r in records if r["match_status"] in ("Scheduled","TBD")], 1):
    matchup = f"{r['home_team']} vs {r['away_team']}"
    print(f"{i:<4} {matchup:<40} {r['match_date']:<12} {r['kickoff_time_local']:<10} {r['stadium']:<28} {r['city']}")

print("\nAll done. Files written to:", BASE)
