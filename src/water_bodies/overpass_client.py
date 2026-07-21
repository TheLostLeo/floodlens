import requests


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Overpass rejects some requests with no descriptive User-Agent.
REQUEST_HEADERS = {"User-Agent": "FloodLens/0.1 (https://github.com/; dev/local use)"}

WATER_QUERY_TEMPLATE = """
[out:json][timeout:90];
(
  way["waterway"~"^(river|stream|canal)$"]({south},{west},{north},{east});
  way["natural"="water"]({south},{west},{north},{east});
  way["landuse"="reservoir"]({south},{west},{north},{east});
  relation["natural"="water"]({south},{west},{north},{east});
);
out geom;
"""


def fetch_water_features(south, north, west, east, timeout=120):
    """
    Query the Overpass API for rivers, streams, canals, lakes, and
    reservoirs inside a WGS84 bounding box.

    Returns the raw Overpass JSON response.
    """
    south, north, west, east = float(south), float(north), float(west), float(east)

    if south >= north or west >= east:
        raise ValueError("Bounding box is invalid: south/west must be less than north/east.")

    query = WATER_QUERY_TEMPLATE.format(south=south, west=west, north=north, east=east)

    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=REQUEST_HEADERS,
        timeout=timeout,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Overpass request failed ({response.status_code}): {response.text[:300]}"
        )

    return response.json()


def overpass_to_geojson(overpass_json):
    """
    Convert an Overpass `out geom` JSON response into a GeoJSON FeatureCollection.

    Closed ways (first and last node identical) are treated as polygons
    (lakes, reservoirs). Open ways are treated as line strings (rivers,
    streams, canals).
    """
    features = []

    for element in overpass_json.get("elements", []):
        geometry = element.get("geometry")
        if not geometry:
            continue

        coordinates = [[point["lon"], point["lat"]] for point in geometry]

        if len(coordinates) >= 4 and coordinates[0] == coordinates[-1]:
            geom = {"type": "Polygon", "coordinates": [coordinates]}
        else:
            geom = {"type": "LineString", "coordinates": coordinates}

        features.append(
            {
                "type": "Feature",
                "properties": element.get("tags", {}),
                "geometry": geom,
            }
        )

    return {"type": "FeatureCollection", "features": features}
