import numpy as np

from floodlens_research.chip_features import sar_summary_features


def test_sar_summary_features_are_finite_and_spatially_richer_than_means():
    vv = np.arange(16, dtype=np.float32).reshape(4, 4)
    vh = vv / 2
    values, names = sar_summary_features(np.stack([vv, vh]))

    assert values.shape == (len(names),)
    assert len(names) >= 15
    assert np.isfinite(values).all()
    assert values[names.index("vv_p90")] > values[names.index("vv_median")]
