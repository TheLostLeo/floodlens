import httpx


class WeatherUnavailable(Exception):
    pass


def fetch_open_meteo(latitude: float, longitude: float) -> dict:
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "precipitation",
                "forecast_days": 2,
                "timezone": "GMT",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()
        if "hourly" not in body:
            raise WeatherUnavailable("Open-Meteo response has no hourly forecast")
        return body
    except (httpx.HTTPError, ValueError) as error:
        raise WeatherUnavailable(str(error)) from error


def summarize_rainfall(response: dict | None) -> dict:
    if not response:
        return {
            "status": "unavailable",
            "message": "Rainfall forecast is unavailable.",
            "limitations": ["Rainfall context is not an official warning and must not be used for emergency decisions."],
        }
    precipitation = response.get("hourly", {}).get("precipitation") or []
    usable = [float(value) for value in precipitation if value is not None]
    if not usable:
        return {
            "status": "unavailable",
            "message": "Open-Meteo returned no usable precipitation values.",
            "limitations": ["Rainfall context is not an official warning and must not be used for emergency decisions."],
        }
    total_mm = round(sum(usable), 1)
    max_hourly_mm = round(max(usable), 1)
    wet_hours = sum(1 for value in usable if value > 0)
    if total_mm >= 50 or max_hourly_mm >= 20:
        level = "high"
    elif total_mm >= 20 or max_hourly_mm >= 10:
        level = "moderate"
    elif total_mm > 0:
        level = "low"
    else:
        level = "none"
    return {
        "status": "available",
        "message": f"Open-Meteo rainfall pressure is {level}.",
        "pressure_level": level,
        "forecast_total_mm": total_mm,
        "max_hourly_mm": max_hourly_mm,
        "wet_hours": wet_hours,
        "forecast_hours": len(usable),
        "provenance": {
            "provider": "Open-Meteo",
            "timezone": response.get("timezone"),
            "forecast_start": (response.get("hourly", {}).get("time") or [None])[0],
            "forecast_end": (response.get("hourly", {}).get("time") or [None])[-1],
        },
        "limitations": [
            "Rainfall pressure describes provider forecast rainfall only; it is not an official alert.",
            "Flooding also depends on drainage, tide, soil moisture, reservoirs, blocked channels, and local operations.",
        ],
    }
