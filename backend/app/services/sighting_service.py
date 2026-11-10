"""Sighting queries and creation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from PIL import Image
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database.init_db import assign_geom
from app.geospatial.geo import validate_coordinates
from app.models.entities import Prediction, Sighting, Species, User, VerificationRecord, utcnow
from app.services.ai_service import identify_image
from app.services.audit_service import write_audit
from app.services.image_service import save_image, sha256_bytes
from app.services.settings_service import get_app_settings


def _base_query(db: Session):
    return db.query(Sighting).options(
        joinedload(Sighting.species),
        joinedload(Sighting.observer),
        selectinload(Sighting.predictions),
        selectinload(Sighting.verifications).joinedload(VerificationRecord.reviewer),
    )


def visible_query(db: Session, user: User):
    query = _base_query(db)
    if user.role == "citizen":
        query = query.filter(or_(Sighting.verification_status == "verified", Sighting.user_id == user.id))
    return query


def apply_filters(
    query,
    *,
    species_id: int | None = None,
    classification: str | None = None,
    verification_status: str | None = None,
    category: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lng: float | None = None,
    max_lng: float | None = None,
    location: str | None = None,
):
    if species_id is not None:
        query = query.filter(Sighting.species_id == species_id)
    if verification_status:
        query = query.filter(Sighting.verification_status == verification_status)
    if category:
        query = query.filter(Sighting.category == category)
    if start is not None:
        query = query.filter(Sighting.observed_at >= start)
    if end is not None:
        query = query.filter(Sighting.observed_at <= end)
    if min_lat is not None:
        query = query.filter(Sighting.latitude >= min_lat)
    if max_lat is not None:
        query = query.filter(Sighting.latitude <= max_lat)
    if min_lng is not None:
        query = query.filter(Sighting.longitude >= min_lng)
    if max_lng is not None:
        query = query.filter(Sighting.longitude <= max_lng)
    if location:
        query = query.filter(Sighting.location_name.ilike(f"%{location}%"))
    if classification:
        query = query.filter(Sighting.species.has(Species.classification == classification))
    return query


def parse_observed_at(value: str | None, *, allow_future: bool = False) -> datetime:
    if not value:
        return utcnow()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Observation time must be an ISO 8601 datetime.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if not allow_future and parsed > utcnow() + timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Observation time cannot be in the future.")
    return parsed


def create_sighting(
    db: Session,
    user: User,
    image: Image.Image,
    original_bytes: bytes,
    *,
    latitude: float,
    longitude: float,
    location_name: str,
    observed_at: datetime,
    category: str,
    submitted_name: str,
    notes: str,
    is_demonstration: bool = False,
) -> Sighting:
    if category not in {"plant", "animal"}:
        raise HTTPException(status_code=400, detail="Species category must be plant or animal.")
    validate_coordinates(latitude, longitude)
    if len(notes) > 2000:
        raise HTTPException(status_code=400, detail="Notes must be 2000 characters or fewer.")
    digest = sha256_bytes(original_bytes)
    existing = db.query(Sighting).filter(Sighting.image_sha256 == digest).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"This image was already submitted as sighting {existing.id}.")
    settings = get_app_settings(db)
    prediction = identify_image(image, category, float(settings["low_confidence_threshold"]))
    species = None
    if not prediction["insufficient_confidence"]:
        species = db.query(Species).filter(Species.scientific_name == prediction["scientific_name"]).first()
    image_path = save_image(image)
    sighting = Sighting(
        user_id=user.id,
        species_id=species.id if species is not None else None,
        image_path=image_path,
        image_sha256=digest,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name.strip(),
        observed_at=observed_at,
        confidence=prediction["confidence"],
        verification_status="pending",
        risk_level=prediction["risk_level"],
        category=category,
        submitted_name=submitted_name.strip(),
        notes=notes.strip(),
        is_demonstration=is_demonstration,
        insufficient_confidence=prediction["insufficient_confidence"],
    )
    db.add(sighting)
    db.flush()
    assign_geom(db, "sightings", sighting.id, latitude, longitude)
    db.add(
        Prediction(
            sighting_id=sighting.id,
            model_name=prediction["model_name"],
            model_version=prediction["model_version"],
            inference_mode=prediction["inference_mode"],
            pipeline=prediction.get("pipeline") or category,
            predicted_label=prediction["predicted_common_name"],
            scientific_name=prediction["scientific_name"],
            category=prediction["category"],
            classification=prediction["classification"],
            confidence=prediction["confidence"],
            insufficient_confidence=prediction["insufficient_confidence"],
            raw_scores=prediction["raw_scores"],
        )
    )
    write_audit(db, user.id, "sighting_submitted", "sighting", sighting.id, {"demonstration": is_demonstration})
    db.commit()
    db.refresh(sighting)
    return sighting
