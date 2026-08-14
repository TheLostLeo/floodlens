"""
Heatmap exporter.

Converts a 0–1 flood-risk GeoTIFF into a transparent RGBA PNG suitable
for Leaflet's L.imageOverlay, together with the WGS84 bounding box
needed to position it on the map.

Colour scale:
    0.0  →  deep blue   (no / very low risk)
    0.5  →  yellow      (moderate risk)
    1.0  →  deep red    (high risk)

NoData cells are rendered fully transparent.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import calculate_default_transform, reproject as rasterio_reproject, Resampling

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Pillow is required for heatmap export. "
        "Add 'Pillow' to requirements.txt and reinstall."
    ) from exc


# Colour stops for the flood-risk colour ramp (value, R, G, B).
# Matches a blue → yellow → red diverging scheme.
_COLOUR_STOPS = np.array(
    [
        [0.00, 0,   0,   180],   # deep blue
        [0.25, 30,  120, 220],   # sky blue
        [0.50, 240, 220, 20],    # yellow
        [0.75, 240, 100, 20],    # orange
        [1.00, 180, 0,   0],     # deep red
    ],
    dtype=np.float32,
)


def _risk_to_rgba(risk: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Map a 0–1 float32 array to an RGBA uint8 image array.

    Masked (NoData) pixels are rendered as fully transparent.
    """
    h, w = risk.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    # Clamp risk to [0, 1] for safety.
    r = np.clip(risk, 0.0, 1.0)

    stops_v = _COLOUR_STOPS[:, 0]
    stops_rgb = _COLOUR_STOPS[:, 1:4]

    # Vectorised piecewise linear interpolation across colour stops.
    indices = np.searchsorted(stops_v, r, side="right")
    indices = np.clip(indices, 1, len(stops_v) - 1)

    lo = indices - 1
    hi = indices

    v_lo = stops_v[lo]
    v_hi = stops_v[hi]

    # Avoid division by zero at exact stop boundaries.
    span = np.where(v_hi == v_lo, 1.0, v_hi - v_lo)
    t = ((r - v_lo) / span)[..., np.newaxis]

    rgb_lo = stops_rgb[lo]
    rgb_hi = stops_rgb[hi]

    rgba[..., :3] = np.clip(rgb_lo + t * (rgb_hi - rgb_lo), 0, 255).astype(np.uint8)
    rgba[..., 3] = np.where(mask, 0, 200).astype(np.uint8)   # alpha: 0=transparent, 200=semi-opaque

    return rgba


def _wgs84_bounds(raster_path: Path) -> dict[str, float]:
    """
    Return the WGS84 bounding box of a raster (may already be in WGS84).
    """
    wgs84 = CRS.from_epsg(4326)

    with rasterio.open(raster_path) as src:
        if src.crs == wgs84 or src.crs.to_epsg() == 4326:
            b = src.bounds
            return {"south": b.bottom, "west": b.left, "north": b.top, "east": b.right}

        # Reproject the four corners.
        transform, width, height = calculate_default_transform(
            src.crs, wgs84, src.width, src.height, *src.bounds
        )

    # The transform's origin is the top-left corner.
    west = transform.c
    north = transform.f
    east = west + transform.a * width
    south = north + transform.e * height   # transform.e is negative

    return {"south": south, "west": west, "north": north, "east": east}


def export_heatmap(
    risk_raster_path: Path | str,
    output_png_path: Path | str,
    output_bounds_path: Path | str,
) -> tuple[Path, Path]:
    """
    Convert a flood-risk GeoTIFF (0–1) to a web-ready RGBA PNG.

    Parameters
    ----------
    risk_raster_path : Path | str
        The 0–1 flood-risk raster produced by ``flood_risk_score``.
    output_png_path : Path | str
        Destination for the RGBA PNG heatmap image.
    output_bounds_path : Path | str
        Destination for a JSON file containing WGS84 bounds
        ``{"south", "west", "north", "east"}``.

    Returns
    -------
    (png_path, bounds_path)
    """
    risk_raster_path = Path(risk_raster_path)
    output_png_path = Path(output_png_path)
    output_bounds_path = Path(output_bounds_path)

    if not risk_raster_path.exists():
        raise FileNotFoundError(f"Risk raster not found: {risk_raster_path}")

    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    output_bounds_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(risk_raster_path) as src:
        risk = src.read(1).astype(np.float32)
        nodata = src.nodata if src.nodata is not None else -9999.0

    mask = ~np.isfinite(risk) | np.isclose(risk, nodata)

    rgba = _risk_to_rgba(risk, mask)

    img = Image.fromarray(rgba, mode="RGBA")
    img.save(output_png_path, format="PNG", optimize=True)

    bounds = _wgs84_bounds(risk_raster_path)
    output_bounds_path.write_text(json.dumps(bounds, indent=2))

    return output_png_path, output_bounds_path
