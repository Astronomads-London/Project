"""Seven-day chart data shared by the astronaut and flight surgeon dashboards."""
from datetime import timedelta

from app.utils.vital_signs import reading_status

CHART_DAYS = 7

# (field, title, unit, account field holding the target, target if unset)
_CHART_DEFINITIONS = (
    ("sleep_hours", "Sleep", "hours", "sleep_target", 8),
    ("resting_heart_rate", "Resting heart rate", "bpm", None, None),
    ("glucose_level", "Glucose", "mg/dL", None, None),
    ("blood_pressure", "Blood pressure · systolic", "mmHg", None, None),
    ("water", "Water intake", "ml", "water_target", 2500),
    ("breaths_per_min", "Breaths per minute", "breaths/min", None, None),
    ("o2_level", "Blood oxygen", "%", None, None),
    ("body_temp", "Body temperature", "°C", None, None),
)


def build_charts(records, user, today):
    """Return one chart per metric covering the CHART_DAYS days ending today.

    records are the account's daily logs (any order, extra days are ignored)
    and user is the account they belong to, which supplies the targets.
    """
    dates = [today - timedelta(days=offset) for offset in range(CHART_DAYS - 1, -1, -1)]
    water_target = user.get("water_target")
    records_by_date = {record.get("date"): record for record in records}
    charts = []
    for field, title, unit, target_field, default_target in _CHART_DEFINITIONS:
        points = []
        for day in dates:
            value = records_by_date.get(day.isoformat(), {}).get(field)
            # "normal", "concerning" or "critical": decides the bar's colour.
            status = reading_status(field, value, water_target)
            if field == "blood_pressure":
                value = str(value).strip() if value is not None else None
            elif value is not None:
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    value = None
            points.append({
                "label": day.strftime("%a"),
                "value": value,
                "status": status.lower() if status else None,
            })
        charts.append({
            "field": field,
            "title": title,
            "unit": unit,
            "target": user.get(target_field, default_target) if target_field else None,
            "points": points,
        })
    return charts
