from datetime import date, timedelta
import math
import pytest

from app.analysis import analyze, linear_trend, normalize_weather, percentile


def records(start, end, value=20):
    result = []
    day = date.fromisoformat(start)
    while day <= date.fromisoformat(end):
        result.append({"date": day.isoformat(), "tmax": value, "quality": "valid"})
        day += timedelta(days=1)
    return result


def baseline():
    return records("1991-01-01", "2020-12-31")


def test_percentile_uses_linear_interpolation():
    assert percentile([0, 10, 20, 30], 0.95) == pytest.approx(28.5)
    assert percentile([7], 0.95) == 7
    with pytest.raises(ValueError):
        percentile([], 0.95)


def test_strict_threshold_and_three_day_minimum():
    data = baseline() + records("2021-01-01", "2021-12-31")
    for row in data:
        if row["date"] in ["2021-01-01", "2021-01-02", "2021-01-03"]:
            row["tmax"] = 30
        if row["date"] in ["2021-02-01", "2021-02-02"]:
            row["tmax"] = 30
    result = analyze(data, 2021, 2021)
    assert result["methodology"]["threshold_c"] == 20
    assert result["summary"]["total_events"] == 1
    assert result["events"][0]["duration"] == 3
    assert result["annual"][0]["mean_exceedance"] == 10
    assert result["events"][0]["boundary_truncated"] is True


def test_gap_and_null_break_consecutive_runs():
    data = baseline() + records("2021-01-01", "2021-12-31")
    for row in data:
        if "2021-02-01" <= row["date"] <= "2021-02-05":
            row["tmax"] = 30
    data = [row for row in data if row["date"] != "2021-02-03"]
    assert analyze(data, 2021, 2021)["events"] == []
    data.append({"date": "2021-02-03", "tmax": None, "quality": "missing"})
    assert analyze(data, 2021, 2021)["events"] == []


def test_cross_year_event_counted_once_and_days_split():
    data = baseline() + records("2021-01-01", "2022-12-31")
    for row in data:
        if "2021-12-30" <= row["date"] <= "2022-01-02":
            row["tmax"] = 30
    result = analyze(data, 2021, 2022)
    assert result["summary"]["total_events"] == 1
    assert result["events"][0]["duration"] == 4
    assert [row["events"] for row in result["annual"]] == [1, 0]
    assert [row["heatwave_days"] for row in result["annual"]] == [2, 2]
    assert result["annual"][0]["mean_duration"] == 4


def test_normalize_converts_units_and_keeps_missing_days():
    payload = {"daily_units": {"temperature_2m_max": "°F"}, "daily": {
        "time": ["2021-01-01", "2021-01-03", "2021-01-04", "2021-01-05", "2021-01-06"],
        "temperature_2m_max": [86, None, 500, "bad", True]}}
    result = normalize_weather(payload, date(2021, 1, 1), date(2021, 1, 6))
    assert result["records"][0]["tmax"] == 30
    assert [row["tmax"] for row in result["records"]][1:] == [None] * 5
    assert result["quality"]["missing_days"] == 2
    assert result["quality"]["outlier_days"] == 1
    assert result["quality"]["invalid_days"] == 2
    assert result["quality"]["converted_from"] == "°F"


@pytest.mark.parametrize("payload", [
    {},
    {"daily_units": {"temperature_2m_max": "bananas"}, "daily": {"time": [], "temperature_2m_max": []}},
    {"daily_units": {"temperature_2m_max": "°C"}, "daily": {"time": ["invalid"], "temperature_2m_max": [20]}},
    {"daily_units": {"temperature_2m_max": "°C"}, "daily": {"time": ["2021-01-01"] * 2, "temperature_2m_max": [20, 30]}},
    {"daily_units": {"temperature_2m_max": "°C"}, "daily": {"time": ["2021-01-01"], "temperature_2m_max": []}},
])
def test_malformed_weather_is_rejected(payload):
    with pytest.raises(ValueError):
        normalize_weather(payload, date(2021, 1, 1), date(2021, 1, 2))


def test_nonfinite_temperature_is_missing_not_an_event():
    payload = {"daily_units": {"temperature_2m_max": "°C"}, "daily": {
        "time": ["2021-01-01", "2021-01-02"], "temperature_2m_max": [math.inf, math.nan]}}
    result = normalize_weather(payload, date(2021, 1, 1), date(2021, 1, 2))
    assert result["quality"]["invalid_days"] == 2


def test_coverage_exclusion_zero_years_and_rolling_average():
    data = baseline() + records("2021-01-01", "2025-12-31")
    result = analyze(data, 2021, 2025)
    assert len(result["annual"]) == 5
    assert result["annual"][2]["rolling_events"] == 0
    assert result["trends"]["events"]["slope_per_decade"] == 0
    data = [row for row in data if not "2023-01-01" <= row["date"] <= "2023-03-01"]
    result = analyze(data, 2021, 2025)
    assert result["quality"]["low_coverage_years"] == [2023]
    assert result["annual"][2]["rolling_events"] is None
    assert result["annual"][4]["rolling_events"] is None
    assert result["trends"]["events"] is None


def test_inadequate_baseline_is_rejected():
    with pytest.raises(ValueError, match="baseline"):
        analyze(records("2021-01-01", "2021-12-31"), 2021, 2021)
    data = baseline()
    for row in data:
        if row["date"].startswith("2000-"):
            row["tmax"] = None
    with pytest.raises(ValueError, match="baseline"):
        analyze(data, 1991, 2020)


def test_regression_is_hand_calculated_and_requires_five_years():
    result = linear_trend([2000, 2001, 2002, 2003, 2004], [1, 3, 5, 7, 9])
    assert result["slope_per_decade"] == 20
    assert result["r_squared"] == 1
    assert result["years_used"] == 5
    assert linear_trend([2000, 2001], [1, 2]) is None
