import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.terrain import classify_score, evaluate_terrain, score_from_metrics


def test_terrain_score_reflects_low_flat_position():
    result = score_from_metrics(
        point_elevation_m=2.0,
        p10_elevation_m=1.5,
        p90_elevation_m=20.0,
        median_slope_percent=0.5,
    )
    assert result["score"] > 60
    assert result["label"] == "higher relative terrain susceptibility"


def test_terrain_score_reflects_high_steep_position():
    result = score_from_metrics(
        point_elevation_m=30.0,
        p10_elevation_m=1.0,
        p90_elevation_m=31.0,
        median_slope_percent=8.0,
    )
    assert result["score"] < 20
    assert classify_score(0.1) == "lower relative terrain susceptibility"


def test_terrain_reads_a_wgs84_fabdem_tile(tmp_path):
    tile = tmp_path / "N12E080_FABDEM_V1-2.tif"
    with rasterio.open(
        tile,
        "w",
        driver="GTiff",
        height=100,
        width=100,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(80.0, 13.0, 0.01, 0.01),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(np.full((1, 100, 100), 12.0, dtype="float32"))

    result = evaluate_terrain(12.5, 80.5, 1, str(tmp_path), "test", 1_000)

    assert result["status"] == "available"
    assert result["provenance"]["tiles_used"] == [tile.name]
