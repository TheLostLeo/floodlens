import json
from pathlib import Path

from water_bodies.overpass_client import fetch_water_features, overpass_to_geojson


def download_water_bodies(south, north, west, east, output_path):
    """
    Download rivers, streams, canals, lakes, and reservoirs for a WGS84
    bounding box from OpenStreetMap (via Overpass) and save them as GeoJSON.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    overpass_json = fetch_water_features(south=south, north=north, west=west, east=east)
    geojson = overpass_to_geojson(overpass_json)

    if not geojson["features"]:
        raise RuntimeError("No water-body features were found in this bounding box.")

    output_path.write_text(json.dumps(geojson, indent=2))

    return output_path
