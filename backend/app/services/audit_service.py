from sqlalchemy.orm import Session

from app.models.entities import AuditLog


def write_audit(db: Session, user_id: int | None, action: str, entity_type: str, entity_id: str | int, details: dict | None = None) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details or {},
        )
    )
