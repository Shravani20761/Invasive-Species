from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_roles
from app.database.session import get_db
from app.models.entities import Alert, User, utcnow
from app.services.alert_service import refresh_alerts
from app.services.audit_service import write_audit
from app.services.serializers import alert_out

router = APIRouter(prefix="/alerts", tags=["alerts"])


class ReviewIn(BaseModel):
    comment: str = ""


@router.get("")
def list_alerts(
    risk_level: str | None = None,
    species_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Alert).options(joinedload(Alert.species))
    if risk_level:
        query = query.filter(Alert.risk_level == risk_level)
    if species_id is not None:
        query = query.filter(Alert.species_id == species_id)
    if status:
        query = query.filter(Alert.status == status)
    total = query.count()
    rows = query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [alert_out(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/generate")
def generate(db: Session = Depends(get_db), _: User = Depends(require_roles("researcher", "admin"))):
    refresh_alerts(db)
    rows = db.query(Alert).options(joinedload(Alert.species)).filter(Alert.status == "open").all()
    return {"total": len(rows), "items": [alert_out(row) for row in rows]}


@router.put("/{alert_id}/review")
def review_alert(
    alert_id: int,
    payload: ReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("researcher", "admin")),
):
    alert = db.query(Alert).options(joinedload(Alert.species)).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.status = "reviewed"
    alert.reviewed_at = utcnow()
    alert.reviewed_by_id = user.id
    alert.review_comment = payload.comment.strip()
    write_audit(db, user.id, "alert_reviewed", "alert", alert.id, {"comment": alert.review_comment})
    db.commit()
    db.refresh(alert)
    return alert_out(alert)
