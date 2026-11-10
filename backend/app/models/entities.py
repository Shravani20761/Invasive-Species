"""SQLAlchemy models for users, sightings, clusters, alerts, and audit records."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


cluster_sightings = Table(
    "cluster_sightings",
    Base.metadata,
    Column("cluster_id", ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True),
    Column("sighting_id", ForeignKey("sightings.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="citizen", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sightings: Mapped[list["Sighting"]] = relationship(back_populates="observer")


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    common_name: Mapped[str] = mapped_column(String(160), index=True)
    scientific_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    classification: Mapped[str] = mapped_column(String(32), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    characteristics: Mapped[str] = mapped_column(Text, default="")
    reference_image: Mapped[str | None] = mapped_column(String(400), nullable=True)
    distribution: Mapped[str] = mapped_column(Text, default="")
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sightings: Mapped[list["Sighting"]] = relationship(back_populates="species")


class Sighting(Base):
    __tablename__ = "sightings"
    __table_args__ = (
        Index("ix_sightings_lat_lng", "latitude", "longitude"),
        Index("ix_sightings_observed", "observed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id", ondelete="SET NULL"), nullable=True)
    image_path: Mapped[str] = mapped_column(String(400))
    image_sha256: Mapped[str] = mapped_column(String(64), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location_name: Mapped[str] = mapped_column(String(200), default="")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submitted_name: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    insufficient_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    observer: Mapped[User] = relationship(back_populates="sightings")
    species: Mapped[Species | None] = relationship(back_populates="sightings")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="sighting", cascade="all, delete-orphan")
    verifications: Mapped[list["VerificationRecord"]] = relationship(back_populates="sighting", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sighting_id: Mapped[int | None] = mapped_column(ForeignKey("sightings.id", ondelete="CASCADE"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(160))
    model_version: Mapped[str] = mapped_column(String(64))
    inference_mode: Mapped[str] = mapped_column(String(32))
    pipeline: Mapped[str] = mapped_column(String(32), default="")
    predicted_label: Mapped[str] = mapped_column(String(200), default="")
    scientific_name: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), default="unknown")
    confidence: Mapped[float] = mapped_column(Float)
    insufficient_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sighting: Mapped[Sighting | None] = relationship(back_populates="predictions")


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id", ondelete="SET NULL"), nullable=True)
    sighting_count: Mapped[int] = mapped_column(Integer, default=0)
    center_latitude: Mapped[float] = mapped_column(Float)
    center_longitude: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    first_detected: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_detected: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    growth_indicator: Mapped[str] = mapped_column(String(32), default="stable")
    growth_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    species: Mapped[Species | None] = relationship()
    sightings: Mapped[list[Sighting]] = relationship(secondary=cluster_sightings)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id", ondelete="SET NULL"), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    location_name: Mapped[str] = mapped_column(String(200), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(200), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_comment: Mapped[str] = mapped_column(Text, default="")

    species: Mapped[Species | None] = relationship()
    cluster: Mapped[Cluster | None] = relationship()


class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sighting_id: Mapped[int] = mapped_column(ForeignKey("sightings.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str] = mapped_column(Text, default="")
    previous_status: Mapped[str] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sighting: Mapped[Sighting] = relationship(back_populates="verifications")
    reviewer: Mapped[User] = relationship()


class SensitiveRegion(Base):
    __tablename__ = "sensitive_regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    center_latitude: Mapped[float] = mapped_column(Float)
    center_longitude: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_name_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[str] = mapped_column(String(64))
    inference_mode: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
