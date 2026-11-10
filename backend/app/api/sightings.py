from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.entities import Sighting, User, utcnow
from app.services.audit_service import write_audit
from app.services.image_service import validate_image_bytes
from app.services.serializers import sighting_out
from app.services.sighting_service import apply_filters, create_sighting, parse_observed_at, visible_query

router = APIRouter(prefix="/sightings", tags=["sightings"])


class SightingUpdate(BaseModel):
    location_name: str | None = None
    notes: str | None = None
    submitted_name: str | None = None
    observed_at: str | None = None


@router.post("", status_code=201)
async def submit_sighting(
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(...),
    location_name: str = Form(""),
    observed_at: str | None = Form(None),
    submitted_name: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await image.read()
    loaded = validate_image_bytes(data)
    sighting = create_sighting(
        db,
        user,
        loaded,
        data,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        observed_at=parse_observed_at(observed_at),
        category=category,
        submitted_name=submitted_name,
        notes=notes,
    )
    stored = visible_query(db, user).filter(Sighting.id == sighting.id).first()
    return sighting_out(stored)


@router.get("")
def list_sightings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    species_id: int | None = None,
    classification: str | None = None,
    verification_status: str | None = None,
    category: str | None = None,
    start: str | None = None,
    end: str | None = None,
    location: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = visible_query(db, user)
    if mine:
        query = query.filter(Sighting.user_id == user.id)
    query = apply_filters(
        query,
        species_id=species_id,
        classification=classification,
        verification_status=verification_status,
        category=category,
        start=parse_observed_at(start, allow_future=True) if start else None,
        end=parse_observed_at(end, allow_future=True) if end else None,
        location=location,
    )
    total = query.count()
    rows = query.order_by(Sighting.observed_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [sighting_out(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/{sighting_id}")
def get_sighting(sighting_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sighting = visible_query(db, user).filter(Sighting.id == sighting_id).first()
    if sighting is None:
        raise HTTPException(status_code=404, detail="Sighting not found.")
    return sighting_out(sighting)


@router.put("/{sighting_id}")
def update_sighting(
    sighting_id: int,
    payload: SightingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sighting = visible_query(db, user).filter(Sighting.id == sighting_id).first()
    if sighting is None:
        raise HTTPException(status_code=404, detail="Sighting not found.")
    if user.role == "citizen" and (sighting.user_id != user.id or sighting.verification_status != "pending"):
        raise HTTPException(status_code=403, detail="You can only edit your own pending sightings.")
    if payload.location_name is not None:
        sighting.location_name = payload.location_name.strip()
    if payload.notes is not None:
        if len(payload.notes) > 2000:
            raise HTTPException(status_code=400, detail="Notes must be 2000 characters or fewer.")
        sighting.notes = payload.notes.strip()
    if payload.submitted_name is not None:
        sighting.submitted_name = payload.submitted_name.strip()
    if payload.observed_at is not None:
        sighting.observed_at = parse_observed_at(payload.observed_at)
    sighting.updated_at = utcnow()
    write_audit(db, user.id, "sighting_updated", "sighting", sighting.id, {})
    db.commit()
    refreshed = visible_query(db, user).filter(Sighting.id == sighting.id).first()
    return sighting_out(refreshed)
