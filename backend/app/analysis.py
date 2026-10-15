"""Pure climate calculations; no network or database dependencies."""
from calendar import isleap
from datetime import date, timedelta
from math import isfinite
from statistics import mean

BASELINE_START = date(1991, 1, 1)
BASELINE_END = date(2020, 12, 31)
MIN_COVERAGE = 0.9


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered or not 0 <= fraction <= 1:
        raise ValueError("A percentile needs observations and a fraction from 0 to 1.")
    rank = (len(ordered) - 1) * fraction
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def normalize_weather(payload, start, end):
    """Validate the upstream schema, convert units, and preserve missing dates."""
    try:
        daily = payload["daily"]
        dates = daily["time"]
        temperatures = daily["temperature_2m_max"]
        unit = payload["daily_units"]["temperature_2m_max"]
    except (KeyError, TypeError):
        raise ValueError("Weather provider returned an incomplete daily-temperature response.") from None
    if unit not in ("°C", "°F", "K"):
        raise ValueError("Weather provider returned an unsupported temperature unit.")
    if not isinstance(dates, list) or not isinstance(temperatures, list) or len(dates) != len(temperatures):
        raise ValueError("Weather provider returned mismatched daily arrays.")
    by_date = {}
    for raw_date, value in zip(dates, temperatures):
        try:
            day = date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            raise ValueError("Weather provider returned an invalid date.") from None
        if raw_date != day.isoformat() or not start <= day <= end or day in by_date:
            raise ValueError("Weather provider returned duplicate or out-of-range dates.")
        quality = "valid"
        if value is None:
            quality = "missing"
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            quality = "invalid"
        else:
            value = (value - 32) * 5 / 9 if unit == "°F" else value - 273.15 if unit == "K" else value
            if not -90 <= value <= 65:
                quality = "outlier"
        by_date[day] = {"date": day.isoformat(), "tmax": float(value) if quality == "valid" else None, "quality": quality}
    records = []
    day = start
    while day <= end:
        records.append(by_date.get(day, {"date": day.isoformat(), "tmax": None, "quality": "missing"}))
        day += timedelta(days=1)
    return {"records": records, "quality": {
        "missing_days": sum(row["quality"] == "missing" for row in records),
        "invalid_days": sum(row["quality"] == "invalid" for row in records),
        "outlier_days": sum(row["quality"] == "outlier" for row in records),
        "converted_from": unit if unit != "°C" else None,
    }}


def linear_trend(years, values):
    if len(years) < 5:
        return None
    x_mean, y_mean = mean(years), mean(values)
    denominator = sum((year - x_mean) ** 2 for year in years)
    if denominator == 0:
        return None
    slope = sum((year - x_mean) * (value - y_mean) for year, value in zip(years, values)) / denominator
    intercept = y_mean - slope * x_mean
    residual = sum((value - (slope * year + intercept)) ** 2 for year, value in zip(years, values))
    total = sum((value - y_mean) ** 2 for value in values)
    return {"slope_per_decade": round(slope * 10, 4),
            "r_squared": round(max(0, min(1, 1 - residual / total)), 4) if total else None,
            "years_used": len(years)}


def analyze(records, start_year, end_year):
    by_date = {row["date"]: row for row in records}
    baseline = [row for row in records if BASELINE_START.isoformat() <= row["date"] <= BASELINE_END.isoformat()]
    valid_baseline = [row["tmax"] for row in baseline if row["tmax"] is not None]
    baseline_expected = (BASELINE_END - BASELINE_START).days + 1
    baseline_coverage = len(valid_baseline) / baseline_expected
    baseline_counts = {year: 0 for year in range(1991, 2021)}
    for row in baseline:
        if row["tmax"] is not None:
            baseline_counts[int(row["date"][:4])] += 1
    if baseline_coverage < MIN_COVERAGE or any(
        count / (366 if isleap(year) else 365) < MIN_COVERAGE for year, count in baseline_counts.items()
    ):
        raise ValueError("Insufficient baseline coverage: need at least 90% valid days in every 1991–2020 year.")
    threshold = percentile(valid_baseline, 0.95)
    first, last = date(start_year, 1, 1), date(end_year, 12, 31)
    selected = []
    day = first
    while day <= last:
        selected.append(by_date.get(day.isoformat(), {"date": day.isoformat(), "tmax": None, "quality": "missing"}))
        day += timedelta(days=1)

    events, run = [], []
    # Runs operate on a complete calendar, so missing observations always split them.
    for row in selected + [{"date": "", "tmax": None}]:
        if row["tmax"] is not None and row["tmax"] > threshold:
            run.append(row)
            continue
        if len(run) >= 3:
            events.append({"start": run[0]["date"], "end": run[-1]["date"], "duration": len(run),
                           "peak_temperature": round(max(item["tmax"] for item in run), 2),
                           "mean_exceedance": round(mean(item["tmax"] - threshold for item in run), 2),
                           "boundary_truncated": run[0]["date"] == first.isoformat() or run[-1]["date"] == last.isoformat()})
        run = []

    annual = []
    hot_dates = set()
    for event in events:
        day = date.fromisoformat(event["start"])
        while day <= date.fromisoformat(event["end"]):
            hot_dates.add(day.isoformat())
            day += timedelta(days=1)
    yearly_records = {year: [] for year in range(start_year, end_year + 1)}
    for row in selected:
        yearly_records[int(row["date"][:4])].append(row)
    for year, rows in yearly_records.items():
        starting_events = [event for event in events if int(event["start"][:4]) == year]
        hot = [row["tmax"] for row in rows if row["date"] in hot_dates]
        valid_days = sum(row["tmax"] is not None for row in rows)
        coverage = valid_days / len(rows)
        annual.append({"year": year, "events": len(starting_events), "heatwave_days": len(hot),
                       "mean_duration": round(mean(event["duration"] for event in starting_events), 2) if starting_events else 0,
                       "max_duration": max((event["duration"] for event in starting_events), default=0),
                       "mean_exceedance": round(mean(value - threshold for value in hot), 2) if hot else 0,
                       "peak_temperature": round(max(hot), 2) if hot else None,
                       "valid_days": valid_days, "expected_days": len(rows), "coverage": round(coverage, 4),
                       "eligible": coverage >= MIN_COVERAGE})
    for index, row in enumerate(annual):
        window = annual[max(0, index - 2):index + 1]
        for metric, output in [("events", "rolling_events"), ("mean_duration", "rolling_duration"), ("mean_exceedance", "rolling_intensity")]:
            row[output] = round(mean(item[metric] for item in window), 2) if len(window) == 3 and all(item["eligible"] for item in window) else None
    eligible = [row for row in annual if row["eligible"]]
    trends = {key: linear_trend([row["year"] for row in eligible], [row[metric] for row in eligible])
              for key, metric in [("events", "events"), ("duration", "mean_duration"), ("intensity", "mean_exceedance")]}
    valid_days = sum(row["tmax"] is not None for row in selected)
    return {
        "methodology": {"baseline": "1991–2020", "percentile": 95, "threshold_c": round(threshold, 4),
                        "minimum_consecutive_days": 3, "comparison": "strictly above", "model": "ERA5",
                        "coverage_required": MIN_COVERAGE, "rolling_window_years": 3},
        "quality": {"valid_days": valid_days, "expected_days": len(selected), "coverage": round(valid_days / len(selected), 4),
                    "missing_days": sum(row.get("quality") == "missing" for row in selected),
                    "invalid_days": sum(row.get("quality") == "invalid" for row in selected),
                    "outlier_days": sum(row.get("quality") == "outlier" for row in selected),
                    "baseline_coverage": round(baseline_coverage, 4),
                    "low_coverage_years": [row["year"] for row in annual if not row["eligible"]]},
        "annual": annual, "events": events, "trends": trends,
        "summary": {"total_events": len(events), "heatwave_days": len(hot_dates),
                    "longest_event": max((event["duration"] for event in events), default=0),
                    "mean_duration": round(mean(event["duration"] for event in events), 2) if events else 0,
                    "peak_temperature": max((event["peak_temperature"] for event in events), default=None),
                    "eligible_years": len(eligible), "boundary_events": sum(event["boundary_truncated"] for event in events)},
    }
