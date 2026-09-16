import pytest
from pydantic import ValidationError
from app.schemas import AnalysisCreate


@pytest.mark.parametrize("payload", [
    {"latitude": 91, "longitude": 0, "radius_km": 1},
    {"latitude": 0, "longitude": -181, "radius_km": 1},
    {"latitude": float("nan"), "longitude": 0, "radius_km": 1},
    {"latitude": 0, "longitude": 0, "radius_km": 3},
])
def test_invalid_analysis_input_is_rejected(payload):
    with pytest.raises(ValidationError):
        AnalysisCreate(**payload)


def test_valid_analysis_input():
    assert AnalysisCreate(latitude=13.0827, longitude=80.2707, radius_km=2).radius_km == 2
