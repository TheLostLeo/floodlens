import numpy as np

from floodlens_research.lstm_v2 import event_balanced_weights, rainfall_features


def test_rainfall_features_capture_accumulation_peaks_and_recency():
    rain = np.zeros((2, 60), dtype=np.float32)
    rain[0, -1] = 10
    rain[1, -4:] = [1, 2, 3, 4]

    features, names = rainfall_features(rain)

    assert features.shape == (2, len(names))
    assert features[0, names.index("rain_1d_mm")] == 10
    assert features[1, names.index("rain_3d_mm")] == 9
    assert features[1, names.index("max_3d_mm")] == 9
    assert features[0, names.index("days_since_peak")] == 0
    assert features[1, names.index("wet_days_7")] == 4


def test_event_balanced_weights_give_each_event_equal_total_weight():
    weights = event_balanced_weights(np.array(["a", "a", "a", "b"]))

    assert np.isclose(weights[:3].sum(), weights[3:].sum())
    assert np.isclose(weights.mean(), 1.0)
