from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class AnalysisCreate(BaseModel):
    latitude: float
    longitude: float
    radius_km: int = Field(description="One of 1, 2, or 5 kilometres")

    @field_validator("latitude", "longitude")
    @classmethod
    def finite(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("must be a finite number")
        return value

    @field_validator("latitude")
    @classmethod
    def latitude_range(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def longitude_range(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("must be between -180 and 180")
        return value

    @field_validator("radius_km")
    @classmethod
    def radius_allowed(cls, value: int) -> int:
        if value not in {1, 2, 5}:
            raise ValueError("must be exactly 1, 2, or 5")
        return value


class AnalysisResponse(BaseModel):
    id: UUID
    latitude: float
    longitude: float
    radius_km: int
    status: str
    progress: int
    message: str
    error_code: str | None = None
    basin_context: dict[str, Any] | None = None
    terrain_assessment: dict[str, Any] | None = None
    rainfall_context: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class BasinContextResponse(BaseModel):
    status: str
    message: str
    basin_id: int | None = None
    basin_level: int | None = None
    coverage: str | None = None
    pfaf_id: int | None = None
    local_area_km2: float | None = None
    upstream_area_km2: float | None = None
    upstream_subbasin_count: int | None = None
    containing_geometry: dict[str, Any] | None = None
    upstream_geometry: dict[str, Any] | None = None
    nearby_river: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    missing_datasets: list[str] = Field(default_factory=list)
    limitations: list[str]


class DatasetCoverageItem(BaseModel):
    dataset_name: str
    version: str
    level: int | None = None
    coverage: str
    source_url: str
    licence: str
    sha256: str
    feature_count: int
    status: str
    detail: str | None = None
    imported_at: datetime


class DatasetCoverageResponse(BaseModel):
    status: str
    message: str
    datasets: list[DatasetCoverageItem]
    missing_required: list[str] = Field(default_factory=list)
    limitations: list[str]
