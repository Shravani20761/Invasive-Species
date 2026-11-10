from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.database.session import get_db
from app.models.entities import Sighting, Species, User, utcnow
from app.services.audit_service import write_audit
from app.services.serializers import species_out

router = APIRouter(prefix="/species", tags=["species"])


class SpeciesIn(BaseModel):
    common_name: str = Field(min_length=2, max_length=160)
    scientific_name: str = Field(min_length=2, max_length=200)
    category: str
    classification: str
    description: str = ""
    risk_level: str = "low"
    characteristics: str = ""
    reference_image: str | None = None
    distribution: str = ""


def _validate_species(payload: SpeciesIn) -> None:
    if payload.category not in {"plant", "animal"}:
        raise HTTPException(status_code=400, detail="Category must be plant or animal.")
    if payload.classification not in {"invasive", "native", "unknown"}:
        raise HTTPException(status_code=400, detail="Classification must be invasive, native, or unknown.")
    if payload.risk_level not in {"low", "medium", "high", "critical"}:
        raise HTTPException(status_code=400, detail="Risk level must be low, medium, high, or critical.")


@router.get("")
def list_species(
    q: str | None = None,
    category: str | None = None,
    classification: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Species)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((Species.common_name.ilike(like)) | (Species.scientific_name.ilike(like)))
    if category:
        query = query.filter(Species.category == category)
    if classification:
        query = query.filter(Species.classification == classification)
    rows = query.order_by(Species.common_name).all()
    result = []
    for species in rows:
        count = db.query(Sighting).filter(Sighting.species_id == species.id).count()
        result.append(species_out(species, count))
    return {"items": result, "total": len(result)}


@router.get("/{species_id}")
def get_species(species_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    species = db.get(Species, species_id)
    if species is None:
        raise HTTPException(status_code=404, detail="Species not found.")
    count = db.query(Sighting).filter(Sighting.species_id == species.id).count()
    return species_out(species, count)


@router.post("", status_code=201)
def create_species(payload: SpeciesIn, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    _validate_species(payload)
    if db.query(Species).filter(Species.scientific_name == payload.scientific_name.strip()).first():
        raise HTTPException(status_code=409, detail="A species with this scientific name already exists.")
    species = Species(**payload.model_dump(), is_demonstration=False)
    species.common_name = payload.common_name.strip()
    species.scientific_name = payload.scientific_name.strip()
    db.add(species)
    db.flush()
    write_audit(db, user.id, "species_created", "species", species.id, {"scientific_name": species.scientific_name})
    db.commit()
    db.refresh(species)
    return species_out(species, 0)


@router.put("/{species_id}")
def update_species(species_id: int, payload: SpeciesIn, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    _validate_species(payload)
    species = db.get(Species, species_id)
    if species is None:
        raise HTTPException(status_code=404, detail="Species not found.")
    duplicate = db.query(Species).filter(Species.scientific_name == payload.scientific_name.strip(), Species.id != species.id).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A species with this scientific name already exists.")
    for key, value in payload.model_dump().items():
        setattr(species, key, value.strip() if isinstance(value, str) else value)
    species.updated_at = utcnow()
    write_audit(db, user.id, "species_updated", "species", species.id, {"classification": species.classification, "risk_level": species.risk_level})
    db.commit()
    db.refresh(species)
    count = db.query(Sighting).filter(Sighting.species_id == species.id).count()
    return species_out(species, count)


@router.delete("/{species_id}")
def delete_species(species_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    species = db.get(Species, species_id)
    if species is None:
        raise HTTPException(status_code=404, detail="Species not found.")
    if db.query(Sighting).filter(Sighting.species_id == species.id).count():
        raise HTTPException(status_code=409, detail="This species has sightings and cannot be deleted. Edit its status instead.")
    write_audit(db, user.id, "species_deleted", "species", species.id, {"scientific_name": species.scientific_name})
    db.delete(species)
    db.commit()
    return {"deleted": True, "id": species_id}
