"""
daily_summary.py
================
Generates reports/daily_summary.md after each pipeline run.
"""

import os
from datetime import date
from pathlib import Path


def generate(
    run_date: str,
    newly_completed: list,
    weather_fetched: int,
    weather_failed: int,
    predictions_updated: int,
    model_retrained: bool,
    dq_issues: list,
    prediction_accuracy: dict | None,
    root: Path,
) -> str:
    """
    Write reports/daily_summary.md and return the file path.

    newly_completed : list of dicts with match info for matches added today
    weather_fetched : number of weather records successfully fetched
    weather_failed  : number of weather fetch failures
    predictions_updated : number of upcoming matches with refreshed forecasts
    model_retrained : whether models were retrained this run
    dq_issues       : list of human-readable data quality issue strings
    prediction_accuracy : dict with mae/rmse/n keys (or None if no completed predictions)
    """
    reports_dir = root / "reports"
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / "daily_summary.md"

    lines = []
    lines.append(f"# Daily Update — {run_date}")
    lines.append(f"*Generated automatically by `run_daily_update.py`*")
    lines.append("")

    # ── New matches ──────────────────────────────────────────────────────────
    lines.append(f"## Matches Completed Today ({len(newly_completed)})")
    if newly_completed:
        lines.append("")
        lines.append("| Match ID | Home | Away | Score | Stage |")
        lines.append("|----------|------|------|-------|-------|")
        for m in newly_completed:
            score = f"{int(m.get('home_goals',0))}–{int(m.get('away_goals',0))}"
            lines.append(
                f"| {m['match_id']} | {m['home_team']} | {m['away_team']} "
                f"| {score} | {m.get('stage','')} |"
            )
    else:
        lines.append("")
        lines.append("No new completed matches detected.")
    lines.append("")

    # ── Weather ──────────────────────────────────────────────────────────────
    lines.append("## Weather Data")
    lines.append("")
    lines.append(f"- Records fetched: **{weather_fetched}**")
    lines.append(f"- Fetch failures:  **{weather_failed}**")
    if weather_failed > 0:
        lines.append(f"  - ⚠ Check logs for stadium coordinate issues")
    lines.append("")

    # ── Predictions ──────────────────────────────────────────────────────────
    lines.append("## Predictions")
    lines.append("")
    lines.append(f"- Model retrained:          **{'Yes' if model_retrained else 'No'}**")
    lines.append(f"- Upcoming match forecasts: **{predictions_updated}**")
    if prediction_accuracy:
        n   = prediction_accuracy.get("n", 0)
        mae = prediction_accuracy.get("mae", None)
        rmse = prediction_accuracy.get("rmse", None)
        lines.append(f"- Prediction accuracy (n={n} resolved): "
                     f"MAE = {mae:.2f}, RMSE = {rmse:.2f}" if mae is not None
                     else f"- Prediction accuracy: no resolved predictions yet")
    lines.append("")

    # ── Data quality ─────────────────────────────────────────────────────────
    lines.append("## Data Quality")
    lines.append("")
    if dq_issues:
        for issue in dq_issues:
            lines.append(f"- ⚠ {issue}")
    else:
        lines.append("- No issues detected")
    lines.append("")

    # ── Footer ───────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("*Pipeline: `run_daily_update.py` → ESPN API + Open-Meteo API*")

    content = "\n".join(lines) + "\n"
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)
