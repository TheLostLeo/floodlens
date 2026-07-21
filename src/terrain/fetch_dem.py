import os
import math
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

OPENTOPOGRAPHY_URL = "https://portal.opentopography.org/API/globaldem"


def buffer_bounds(south, north, west, east, buffer_km=5.0):
    """
    Expand a WGS84 bounding box outward by buffer_km kilometres.

    A buffer is added around a user's selected area because surface
    runoff can flow in from higher terrain just outside the selection.

    Argument order matches fetch_dem() and fetch_water_features()
    (south, north, west, east) to avoid accidental swaps.
    """
    south, north, west, east = float(south), float(north), float(west), float(east)
    buffer_km = float(buffer_km)

    if buffer_km < 0:
        raise ValueError("buffer_km must not be negative.")

    if west >= east or south >= north:
        raise ValueError("Bounding box is invalid: west/south must be less than east/north.")

    center_lat = (south + north) / 2
    lat_buffer = buffer_km / 111.0
    lon_buffer = buffer_km / (111.0 * max(math.cos(math.radians(center_lat)), 1e-6))

    return {
        "west": west - lon_buffer,
        "south": south - lat_buffer,
        "east": east + lon_buffer,
        "north": north + lat_buffer,
    }


def fetch_dem(south, north, west, east, output_path, dem_type="SRTMGL1", api_key=None):
    """
    Download a DEM clipped to a WGS84 bounding box from the OpenTopography API.

    Requires a free OpenTopography API key, either passed directly or set
    as the OPENTOPOGRAPHY_API_KEY environment variable (see .env.example).
    """
    south, north, west, east = float(south), float(north), float(west), float(east)

    if south >= north or west >= east:
        raise ValueError("Bounding box is invalid: south/west must be less than north/east.")

    api_key = api_key or os.environ.get("OPENTOPOGRAPHY_API_KEY")
    if not api_key:
        raise ValueError(
            "An OpenTopography API key is required. Set OPENTOPOGRAPHY_API_KEY "
            "in your environment or .env file (see .env.example)."
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    params = {
        "demtype": dem_type,
        "south": south,
        "north": north,
        "west": west,
        "east": east,
        "outputFormat": "GTiff",
        "API_Key": api_key,
    }

    response = requests.get(OPENTOPOGRAPHY_URL, params=params, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenTopography request failed ({response.status_code}): {response.text[:300]}"
        )

    content_type = response.headers.get("Content-Type", "").lower()
    if "tif" not in content_type and "octet-stream" not in content_type:
        raise RuntimeError(
            f"OpenTopography did not return a GeoTIFF (Content-Type: {content_type}). "
            f"Response: {response.text[:300]}"
        )

    output_path.write_bytes(response.content)

    return output_path
