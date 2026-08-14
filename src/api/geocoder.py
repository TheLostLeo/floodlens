"""
Nominatim geocoder — resolves a place name to a WGS84 bounding box.

Uses the public Nominatim API (OpenStreetMap). Follows the usage policy:
  - One request per second maximum (enforced by the caller, not here).
  - Descriptive User-Agent header required.
  - Results are not cached here; the API is only called once per job.
"""

from __future__ import annotations

import requests

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "FloodLens/0.2 (flood-risk research tool; local use)"

# Hard cap: reject requests larger than this in either dimension (degrees).
# ~600 km × 600 km at equatorial latitudes.
MAX_EXTENT_DEGREES = 5.5


class GeocoderError(Exception):
    """Raised when a place name cannot be resolved or the result is too large."""


def geocode_place(place_name: str) -> dict[str, float]:
    """
    Resolve a place name to a WGS84 bounding box.

    Returns
    -------
    dict with keys: south, north, west, east  (all float, degrees)

    Raises
    ------
    GeocoderError
        If the name cannot be resolved or the resulting area is too large.
    """
    place_name = place_name.strip()
    if not place_name:
        raise GeocoderError("Place name must not be empty.")

    params = {
        "q": place_name,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }

    try:
        response = requests.get(
            _NOMINATIM_URL,
            params=params,
            headers={"User-Agent": _USER_AGENT},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise GeocoderError(f"Nominatim request failed: {exc}") from exc

    if response.status_code != 200:
        raise GeocoderError(
            f"Nominatim returned HTTP {response.status_code}: {response.text[:200]}"
        )

    results = response.json()
    if not results:
        raise GeocoderError(
            f"No results found for '{place_name}'. "
            "Try a more specific name, e.g. 'Chennai, India' or 'Kerala state'."
        )

    hit = results[0]
    bb = hit.get("boundingbox")
    if not bb or len(bb) != 4:
        raise GeocoderError(
            f"Nominatim result for '{place_name}' has no bounding box."
        )

    # Nominatim returns [south, north, west, east] as strings.
    south, north, west, east = (float(v) for v in bb)

    width = east - west
    height = north - south

    if width > MAX_EXTENT_DEGREES or height > MAX_EXTENT_DEGREES:
        raise GeocoderError(
            f"'{place_name}' covers an area of {width:.1f}° × {height:.1f}°, "
            f"which exceeds the analysis limit of {MAX_EXTENT_DEGREES}° in either "
            "dimension (roughly 600 km). Please search for a smaller area such as "
            "a district, city, or region."
        )

    return {
        "south": south,
        "north": north,
        "west": west,
        "east": east,
        "display_name": hit.get("display_name", place_name),
    }
