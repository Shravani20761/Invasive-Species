from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.metrics import analytics_query, overview, region_breakdown, species_breakdown, trends
from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.entities import User
from app.services.serializers import alert_out, cluster_out, sighting_out
from app.services.sighting_service import parse_observed_at

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _filters(
    start: str | None,
    end: str | None,
    species_id: int | None,
    location: str | None,
    include_unverified: bool,
):
    return {
        "start": parse_observed_at(start, allow_future=True) if start else None,
        "end": parse_observed_at(end, allow_future=True) if end else None,
        "species_id": species_id,
        "location": location,
        "include_unverified": include_unverified,
    }


@router.get("/overview")
def analytics_overview(
    start: str | None = None,
    end: str | None = None,
    species_id: int | None = None,
    location: str | None = None,
    include_unverified: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = overview(db, user, **_filters(start, end, species_id, location, include_unverified))
    payload["recent_sightings"] = [sighting_out(row) for row in payload["recent_sightings"]]
    payload["active_alerts"] = [alert_out(row) for row in payload["active_alerts"]]
    payload["emerging_clusters"] = [cluster_out(row) for row in payload["emerging_clusters"]]
    return payload


@router.get("/trends")
def analytics_trends(
    start: str | None = None,
    end: str | None = None,
    species_id: int | None = None,
    location: str | None = None,
    include_unverified: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = analytics_query(db, user, **_filters(start, end, species_id, location, include_unverified)).all()
    return trends(rows)


@router.get("/species")
def analytics_species(
    start: str | None = None,
    end: str | None = None,
    species_id: int | None = None,
    location: str | None = None,
    include_unverified: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = analytics_query(db, user, **_filters(start, end, species_id, location, include_unverified)).all()
    return species_breakdown(rows)


@router.get("/regions")
def analytics_regions(
    start: str | None = None,
    end: str | None = None,
    species_id: int | None = None,
    location: str | None = None,
    include_unverified: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = analytics_query(db, user, **_filters(start, end, species_id, location, include_unverified)).all()
    return region_breakdown(rows)
