"""Leakage-free Sentinel-1 summary features for chip classification."""

from __future__ import annotations

import numpy as np


def sar_summary_features(image: np.ndarray) -> tuple[np.ndarray, list[str]]:
    image = np.asarray(image, dtype=np.float32)
    if image.ndim != 3 or image.shape[0] != 2:
        raise ValueError("Expected Sentinel-1 image shaped (2, height, width)")
    channels = {"vv": image[0], "vh": image[1], "vh_minus_vv": image[1] - image[0]}
    names: list[str] = []
    values: list[float] = []
    for name, channel in channels.items():
        finite = channel[np.isfinite(channel)]
        if finite.size == 0:
            raise ValueError("SAR chip contains no finite pixels")
        for label, value in zip(("p10", "p25", "median", "p75", "p90"), np.percentile(finite, [10, 25, 50, 75, 90])):
            names.append(f"{name}_{label}")
            values.append(float(value))
        names.extend((f"{name}_mean", f"{name}_std"))
        values.extend((float(finite.mean()), float(finite.std())))
    for name, channel in (("vv", image[0]), ("vh", image[1])):
        vertical, horizontal = np.gradient(channel)
        magnitude = np.sqrt(vertical * vertical + horizontal * horizontal)
        names.extend((f"{name}_gradient_mean", f"{name}_gradient_p90"))
        values.extend((float(np.nanmean(magnitude)), float(np.nanpercentile(magnitude, 90))))
    result = np.asarray(values, dtype=np.float32)
    if not np.isfinite(result).all():
        raise ValueError("SAR summary features are not finite")
    return result, names
