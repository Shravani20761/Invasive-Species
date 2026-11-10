"""Rebuild species clusters from verified sightings and refresh alert rules."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete
from sqlalchemy.orm import Session, joinedload

from app.database.init_db import assign_geom
from app.geospatial.cluster_detection import cluster_coordinates
from app.models.entities import Cluster, Sighting, Species, cluster_sightings, utcnow
from app.services.alert_service import refresh_alerts
from app.services.settings_service import get_app_settings


def cluster_risk(species: Species, item: dict, settings: dict) -> str:
    if species.classification != "invasive":
        return "low"
    count = item["sighting_count"]
    growth = item["growth_indicator"]
    minimum = int(settings["alert_min_cluster_size"])
    if growth == "growing" and count >= minimum:
        return "critical"
    if count >= minimum or growth == "growing":
        return "high"
    return "medium"


def analyze_clusters(db: Session) -> list[Cluster]:
    settings = get_app_settings(db)
    db.execute(delete(cluster_sightings))
    db.query(Cluster).delete()
    db.flush()
    sightings = (
        db.query(Sighting)
        .filter(Sighting.verification_status == "verified", Sighting.species_id.isnot(None))
        .all()
    )
    grouped: dict[int, list[dict]] = defaultdict(list)
    for sighting in sightings:
        grouped[sighting.species_id].append(
            {
                "sighting_id": sighting.id,
                "latitude": sighting.latitude,
                "longitude": sighting.longitude,
                "observed_at": sighting.observed_at,
            }
        )
    for species_id, points in grouped.items():
        species = db.get(Species, species_id)
        if species is None:
            continue
        found = cluster_coordinates(
            points,
            eps_km=float(settings["cluster_eps_km"]),
            min_samples=int(settings["cluster_min_samples"]),
            now=utcnow(),
            growth_ratio_threshold=float(settings["alert_growth_ratio"]),
        )
        for item in found:
            cluster = Cluster(
                species_id=species_id,
                sighting_count=item["sighting_count"],
                center_latitude=item["center_latitude"],
                center_longitude=item["center_longitude"],
                radius_km=item["radius_km"],
                first_detected=item["first_detected"],
                last_detected=item["last_detected"],
                growth_indicator=item["growth_indicator"],
                growth_ratio=item["growth_ratio"],
                risk_level=cluster_risk(species, item, settings),
            )
            db.add(cluster)
            db.flush()
            assign_geom(db, "clusters", cluster.id, cluster.center_latitude, cluster.center_longitude)
            if item["member_ids"]:
                db.execute(
                    cluster_sightings.insert(),
                    [{"cluster_id": cluster.id, "sighting_id": sighting_id} for sighting_id in item["member_ids"]],
                )
    db.commit()
    refresh_alerts(db)
    return db.query(Cluster).options(joinedload(Cluster.species)).all()


def run_analyze_job() -> None:
    from app.database.session import SessionLocal

    if SessionLocal is None:
        return
    db = SessionLocal()
    try:
        analyze_clusters(db)
    finally:
        db.close()
