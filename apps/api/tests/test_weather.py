import httpx
import pytest
from app.weather import WeatherUnavailable, fetch_open_meteo, summarize_rainfall


def test_provider_failure_is_explicit(monkeypatch):
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("app.weather.httpx.get", unavailable)
    with pytest.raises(WeatherUnavailable, match="offline"):
        fetch_open_meteo(0, 0)


def test_rainfall_summary_uses_provider_values():
    summary = summarize_rainfall({
        "timezone": "GMT",
        "hourly": {
            "time": ["2026-01-01T00:00", "2026-01-01T01:00"],
            "precipitation": [3.0, 18.0],
        },
    })
    assert summary["status"] == "available"
    assert summary["pressure_level"] == "moderate"
    assert summary["forecast_total_mm"] == 21.0
