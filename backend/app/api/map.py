from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.deps import get_current_user
from app.database.init_db import postgis_enabled
from app.database.session import get_db
from app.models.entities import Cluster, Sighting, User
from app.services.serializers import cluster_out, sighting_out
from app.services.sighting_service import apply_filters, parse_observed_at, visible_query

router = APIRouter(prefix="/map", tags=["map"])


def _filtered(db: Session, user: User, **filters):
    start_raw = filters.pop("start", None)
    end_raw = filters.pop("end", None)
    start = parse_observed_at(start_raw, allow_future=True) if start_raw else None
    end = parse_observed_at(end_raw, allow_future=True) if end_raw else None
    return apply_filters(visible_query(db, user), start=start, end=end, **filters)


@router.get("/sightings")
def map_sightings(
    species_id: int | None = None,
    classification: str | None = None,
    verification_status: str | None = None,
    category: str | None = None,
    start: str | None = None,
    end: str | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lng: float | None = None,
    max_lng: float | None = None,
    location: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        _filtered(
            db,
            user,
            species_id=species_id,
            classification=classification,
            verification_status=verification_status,
            category=category,
            start=start,
            end=end,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
            location=location,
        )
        .order_by(Sighting.observed_at.desc())
        .limit(2000)
        .all()
    )
    return {"items": [sighting_out(row) for row in rows], "total": len(rows)}


@router.get("/clusters")
def map_clusters(
    species_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Cluster).options(joinedload(Cluster.species), selectinload(Cluster.sightings))
    if species_id is not None:
        query = query.filter(Cluster.species_id == species_id)
    rows = query.all()
    return {"items": [cluster_out(row) for row in rows], "total": len(rows)}


@router.get("/heatmap")
def heatmap(
    species_id: int | None = None,
    verification_status: str | None = None,
    classification: str | None = None,
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = _filtered(
        db,
        user,
        species_id=species_id,
        verification_status=verification_status,
        classification=classification,
        start=start,
        end=end,
    ).all()
    ids = [row.id for row in rows]
    if postgis_enabled() and ids:
        result = db.execute(
            text(
                """
                SELECT ST_Y(ST_Centroid(ST_Collect(geom))) AS lat,
                       ST_X(ST_Centroid(ST_Collect(geom))) AS lng,
                       COUNT(*) AS weight
                FROM sightings
                WHERE id = ANY(:ids) AND geom IS NOT NULL
                GROUP BY ST_SnapToGrid(geom, 0.08)
                """
            ),
            {"ids": ids},
        ).fetchall()
        return {
            "source": "postgis",
            "items": [{"latitude": row.lat, "longitude": row.lng, "weight": row.weight} for row in result],
        }
    cell = 0.08
    buckets: dict[tuple[float, float], int] = {}
    for row in rows:
        key = (round(row.latitude / cell) * cell, round(row.longitude / cell) * cell)
        buckets[key] = buckets.get(key, 0) + 1
    return {
        "source": "coordinate_grid",
        "items": [{"latitude": lat, "longitude": lng, "weight": weight} for (lat, lng), weight in buckets.items()],
    }
