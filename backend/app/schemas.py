from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class ApiEnvelope(BaseModel):
    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)


class IncidentCreate(BaseModel):
    incident_type: Literal["landslide", "flood", "road_disruption", "river_obstruction", "other"]
    description: str = Field(min_length=10, max_length=2000)
    latitude: float = Field(ge=30.0, le=35.0)
    longitude: float = Field(ge=74.0, le=80.0)
    incident_date: str | None = Field(default=None, max_length=32)
    source_url: HttpUrl | None = None


class IncidentResponse(BaseModel):
    id: int
    incident_type: str
    description: str
    latitude: float
    longitude: float
    incident_date: str | None
    verification_status: str
    submission_origin: str
    source_url: str | None
    created_at: datetime | None


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    rainfall_adjustment: float = Field(ge=-50, le=200, description="Percent adjustment applied to illustrative baseline rainfall")


class StudyAreaConfigure(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=1000)
    boundary: dict[str, Any]

