"""
Flood risk scoring module.

Combines Phase 1 terrain/hydrology rasters into a single 0–1 flood-risk score.

Risk formula (weighted sum of normalised layers):
    risk = 0.25 × (1 − norm_elevation)      low-lying → higher risk
          + 0.25 × (1 − norm_slope)          flat terrain → higher risk
          + 0.35 × norm_log_flow_acc         high upstream drainage → higher risk
          + 0.15 × norm_drainage_paths       on a drainage channel → higher risk

All layers are aligned to the UTM DEM grid before combining.
NoData pixels are masked throughout and written as NoData in the output.
"""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject as rasterio_reproject, Resampling


# Fixed weights — internal implementation detail, not exposed to users.
_WEIGHT_ELEVATION = 0.25
_WEIGHT_SLOPE = 0.25
_WEIGHT_FLOW_ACC = 0.35
_WEIGHT_DRAINAGE = 0.15


def _normalise(array: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Min-max normalise `array` to [0, 1] using only unmasked pixels.

    Returns an array of the same shape. Masked pixels keep their
    original values but are excluded from statistics.
    """
    valid = array[~mask]
    if valid.size == 0:
        return np.zeros_like(array, dtype=np.float32)

    lo, hi = float(valid.min()), float(valid.max())
    if hi == lo:
        out = np.zeros_like(array, dtype=np.float32)
    else:
        out = ((array - lo) / (hi - lo)).astype(np.float32)

    return out


def _read_aligned(
    path: Path,
    ref_transform,
    ref_crs,
    ref_width: int,
    ref_height: int,
    nodata_fallback: float = -9999.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Read a raster and reproject/resample it onto the reference grid.

    Returns (data float32, mask bool) where mask is True for NoData cells.
    """
    with rasterio.open(path) as src:
        src_data = src.read(1).astype(np.float32)
        src_nodata = src.nodata if src.nodata is not None else nodata_fallback

        dst_data = np.empty((ref_height, ref_width), dtype=np.float32)

        rasterio_reproject(
            src_data,
            dst_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
            src_nodata=src_nodata,
            dst_nodata=src_nodata,
        )

    mask = ~np.isfinite(dst_data) | np.isclose(dst_data, src_nodata)
    return dst_data, mask


def calculate_flood_risk(
    dem_utm_path: Path | str,
    slope_path: Path | str,
    flow_accumulation_path: Path | str,
    drainage_paths_path: Path | str,
    output_path: Path | str,
) -> Path:
    """
    Combine Phase 1 raster outputs into a 0–1 flood-risk GeoTIFF.

    Parameters
    ----------
    dem_utm_path : Path | str
        UTM-projected DEM (the reference grid).
    slope_path : Path | str
        Slope-in-degrees raster.
    flow_accumulation_path : Path | str
        D8 flow-accumulation raster (cell count units).
    drainage_paths_path : Path | str
        Binary drainage-path raster (1 = drainage path, 0 = other).
    output_path : Path | str
        Destination for the flood-risk GeoTIFF.

    Returns
    -------
    Path
        The output path on success.
    """
    dem_utm_path = Path(dem_utm_path)
    slope_path = Path(slope_path)
    flow_accumulation_path = Path(flow_accumulation_path)
    drainage_paths_path = Path(drainage_paths_path)
    output_path = Path(output_path)

    for p in (dem_utm_path, slope_path, flow_accumulation_path, drainage_paths_path):
        if not p.exists():
            raise FileNotFoundError(f"Required raster not found: {p}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use the UTM DEM as the reference grid for all other layers.
    with rasterio.open(dem_utm_path) as ref:
        ref_transform = ref.transform
        ref_crs = ref.crs
        ref_width = ref.width
        ref_height = ref.height
        ref_nodata = ref.nodata if ref.nodata is not None else -9999.0
        ref_profile = ref.profile.copy()

        elev_raw = ref.read(1).astype(np.float32)
        elev_mask = ~np.isfinite(elev_raw) | np.isclose(elev_raw, ref_nodata)

    # Read and align all other layers to the reference grid.
    slope_raw, slope_mask = _read_aligned(
        slope_path, ref_transform, ref_crs, ref_width, ref_height
    )
    flow_raw, flow_mask = _read_aligned(
        flow_accumulation_path, ref_transform, ref_crs, ref_width, ref_height
    )
    drain_raw, drain_mask = _read_aligned(
        drainage_paths_path, ref_transform, ref_crs, ref_width, ref_height
    )

    # Combined NoData mask — a pixel is invalid if ANY layer is missing.
    combined_mask = elev_mask | slope_mask | flow_mask | drain_mask

    # --- Normalise each layer ---

    # Elevation: low → high risk, so invert after normalising.
    elev_norm = _normalise(elev_raw, combined_mask)
    elev_score = 1.0 - elev_norm

    # Slope: flat (low slope) → high risk, so invert after normalising.
    slope_norm = _normalise(slope_raw, combined_mask)
    slope_score = 1.0 - slope_norm

    # Flow accumulation: log-transform then normalise (heavy tail distribution).
    flow_log = np.log1p(np.maximum(flow_raw, 0.0))
    flow_score = _normalise(flow_log, combined_mask)

    # Drainage paths: already binary (0/1); normalise in case values differ.
    drain_score = _normalise(drain_raw, combined_mask)

    # --- Weighted combination ---
    risk = (
        _WEIGHT_ELEVATION * elev_score
        + _WEIGHT_SLOPE * slope_score
        + _WEIGHT_FLOW_ACC * flow_score
        + _WEIGHT_DRAINAGE * drain_score
    ).astype(np.float32)

    # Mask NoData pixels.
    output_nodata = -9999.0
    risk[combined_mask] = output_nodata

    # Write output raster using the reference grid's profile.
    ref_profile.update(
        dtype="float32",
        count=1,
        nodata=output_nodata,
        compress="lzw",
    )

    with rasterio.open(output_path, "w", **ref_profile) as dst:
        dst.write(risk, 1)
        dst.set_band_description(1, "Flood risk score (0 = low, 1 = high)")

    return output_path
