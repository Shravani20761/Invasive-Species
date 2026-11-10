from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.database.session import get_db
from app.models.entities import AuditLog, User
from app.services.audit_service import write_audit
from app.services.settings_service import get_app_settings, update_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    cluster_eps_km: float | None = None
    cluster_min_samples: int | None = None
    alert_min_cluster_size: int | None = None
    alert_growth_ratio: float | None = None
    alert_new_area_km: float | None = None
    low_confidence_threshold: float | None = None
    official_analytics_verified_only: bool | None = None


@router.get("")
def read_settings(db: Session = Depends(get_db), user: User = Depends(require_roles("researcher", "admin"))):
    audit = []
    if user.role == "admin":
        rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(20).all()
        audit = [
            {
                "id": row.id,
                "user_id": row.user_id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "details": row.details,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    return {"settings": get_app_settings(db), "audit_logs": audit}


@router.put("")
def write_settings(payload: SettingsUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    changes = {key: value for key, value in payload.model_dump().items() if value is not None}
    updated = update_settings(db, changes)
    write_audit(db, user.id, "settings_updated", "settings", "app", changes)
    db.commit()
    return {"settings": updated}
