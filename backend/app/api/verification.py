from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from app.core.deps import require_roles
from app.database.session import get_db
from app.models.entities import Sighting, User, VerificationRecord, utcnow
from app.services.audit_service import write_audit
from app.services.clustering_service import run_analyze_job
from app.services.serializers import sighting_out
from app.services.sighting_service import _base_query

router = APIRouter(prefix="/verification", tags=["verification"])


class DecisionIn(BaseModel):
    comment: str = ""


def _decide(db: Session, user: User, sighting_id: int, new_status: str, comment: str, background: BackgroundTasks):
    sighting = (
        _base_query(db)
        .options(selectinload(Sighting.verifications))
        .filter(Sighting.id == sighting_id)
        .first()
    )
    if sighting is None:
        raise HTTPException(status_code=404, detail="Sighting not found.")
    if sighting.verification_status != "pending" and user.role != "admin":
        raise HTTPException(status_code=409, detail="Only a pending sighting can be reviewed. An administrator can override a closed review.")
    if sighting.verification_status == new_status:
        raise HTTPException(status_code=409, detail=f"This sighting is already {new_status}.")
    previous = sighting.verification_status
    sighting.verification_status = new_status
    sighting.updated_at = utcnow()
    db.add(
        VerificationRecord(
            sighting_id=sighting.id,
            reviewer_id=user.id,
            action="approve" if new_status == "verified" else "reject",
            comment=comment.strip(),
            previous_status=previous,
            new_status=new_status,
        )
    )
    write_audit(
        db,
        user.id,
        "sighting_verified" if new_status == "verified" else "sighting_rejected",
        "sighting",
        sighting.id,
        {"comment": comment.strip()},
    )
    db.commit()
    background.add_task(run_analyze_job)
    refreshed = _base_query(db).filter(Sighting.id == sighting.id).first()
    return sighting_out(refreshed)


@router.get("/pending")
def pending(db: Session = Depends(get_db), _: User = Depends(require_roles("researcher", "admin"))):
    rows = (
        _base_query(db)
        .filter(Sighting.verification_status == "pending")
        .order_by(Sighting.created_at.asc())
        .all()
    )
    return {"items": [sighting_out(row) for row in rows], "total": len(rows)}


@router.put("/{sighting_id}/approve")
def approve(
    sighting_id: int,
    payload: DecisionIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("researcher", "admin")),
):
    return _decide(db, user, sighting_id, "verified", payload.comment, background)


@router.put("/{sighting_id}/reject")
def reject(
    sighting_id: int,
    payload: DecisionIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("researcher", "admin")),
):
    return _decide(db, user, sighting_id, "rejected", payload.comment, background)
