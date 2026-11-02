from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class StudyArea(Base):
    __tablename__ = "study_areas"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    boundary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    crs: Mapped[str] = mapped_column(String(64), default="EPSG:4326")
    classification: Mapped[str] = mapped_column(String(32), default="illustrative")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    incident_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(64), default="UNVERIFIED USER REPORT")
    submission_origin: Mapped[str] = mapped_column(String(64), default="user_submitted")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rainfall_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[str] = mapped_column(String(64), default="SIMULATED SCENARIO")
    results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

