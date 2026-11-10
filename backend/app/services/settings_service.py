"""Application settings stored in the database, with code defaults underneath."""

import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Setting, utcnow

DEFAULT_SETTINGS = {
    "cluster_eps_km": 15.0,
    "cluster_min_samples": 4,
    "alert_min_cluster_size": 6,
    "alert_growth_ratio": 1.5,
    "alert_new_area_km": 40.0,
    "low_confidence_threshold": 0.45,
    "official_analytics_verified_only": True,
}

SETTING_BOUNDS = {
    "cluster_eps_km": (1, 200),
    "cluster_min_samples": (2, 50),
    "alert_min_cluster_size": (2, 100),
    "alert_growth_ratio": (1, 10),
    "alert_new_area_km": (1, 500),
    "low_confidence_threshold": (0.05, 0.95),
    "official_analytics_verified_only": (None, None),
}


def ensure_default_settings(db: Session) -> None:
    defaults = dict(DEFAULT_SETTINGS)
    defaults["low_confidence_threshold"] = get_settings().low_confidence_threshold
    existing = {row.key for row in db.query(Setting).all()}
    for key, value in defaults.items():
        if key not in existing:
            db.add(Setting(key=key, value=json.dumps(value)))
    db.commit()


def get_app_settings(db: Session) -> dict:
    values = dict(DEFAULT_SETTINGS)
    values["low_confidence_threshold"] = get_settings().low_confidence_threshold
    for row in db.query(Setting).all():
        try:
            values[row.key] = json.loads(row.value)
        except json.JSONDecodeError:
            continue
    return values


def update_settings(db: Session, changes: dict) -> dict:
    unknown = [key for key in changes if key not in DEFAULT_SETTINGS]
    if unknown:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"Unknown settings: {', '.join(unknown)}.")
    for key, value in changes.items():
        low, high = SETTING_BOUNDS[key]
        if key == "official_analytics_verified_only":
            if not isinstance(value, bool):
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail=f"{key} must be true or false.")
        else:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail=f"{key} must be a number.")
            if value < low or value > high:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail=f"{key} must be between {low} and {high}.")
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=json.dumps(value))
            db.add(row)
        else:
            row.value = json.dumps(value)
            row.updated_at = utcnow()
    db.commit()
    return get_app_settings(db)
