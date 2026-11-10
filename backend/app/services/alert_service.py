"""Alert rules.

A DBSCAN cluster is not an alert by itself. Alerts are created only when a
configured size, growth, new-area, or sensitive-region rule is met.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.database.init_db import postgis_enabled
from app.database import session as database
from app.geospatial.geo import haversine_km
from app.models.entities import Alert, Cluster, SensitiveRegion, Sighting, utcnow
from app.services.settings_service import get_app_settings


def refresh_alerts(db: Session) -> list[Alert]:
    settings = get_app_settings(db)
    db.query(Alert).filter(Alert.status == "open").delete(synchronize_session=False)
    db.flush()
    clusters = db.query(Cluster).options(joinedload(Cluster.species)).all()
    for cluster in clusters:
        species = cluster.species
        if species is None or species.classification != "invasive":
            continue
        if cluster.sighting_count >= int(settings["alert_min_cluster_size"]):
            _add_alert(
                db,
                species_id=species.id,
                cluster_id=cluster.id,
                alert_type="concentration",
                risk_level=cluster.risk_level if cluster.risk_level in {"high", "critical"} else "high",
                title=f"Concentration of {species.common_name}",
                description=(
                    f"{cluster.sighting_count} verified sightings of {species.common_name} "
                    f"lie within about {cluster.radius_km:.1f} km."
                ),
                reason=(
                    f"Verified sighting count is {cluster.sighting_count}, which meets the concentration "
                    f"threshold of {int(settings['alert_min_cluster_size'])}. "
                    "A cluster from DBSCAN is not enough on its own to raise this alert."
                ),
                location_name=species.common_name,
                latitude=cluster.center_latitude,
                longitude=cluster.center_longitude,
                dedupe_key=f"concentration:{species.id}:{round(cluster.center_latitude, 2)}:{round(cluster.center_longitude, 2)}",
            )
        if cluster.growth_indicator == "growing" and cluster.growth_ratio >= float(settings["alert_growth_ratio"]):
            _add_alert(
                db,
                species_id=species.id,
                cluster_id=cluster.id,
                alert_type="cluster_expansion",
                risk_level="critical" if cluster.risk_level == "critical" else "high",
                title=f"{species.common_name} cluster is growing",
                description=(
                    f"More {species.common_name} sightings fall in the later half of this cluster's time span "
                    f"than in the earlier half."
                ),
                reason=(
                    f"The later-half to earlier-half sighting ratio is {cluster.growth_ratio:.2f}, "
                    f"at or above the growth threshold of {float(settings['alert_growth_ratio']):.2f}."
                ),
                location_name=species.common_name,
                latitude=cluster.center_latitude,
                longitude=cluster.center_longitude,
                dedupe_key=f"cluster_expansion:{species.id}:{round(cluster.center_latitude, 2)}:{round(cluster.center_longitude, 2)}",
            )
    verified = (
        db.query(Sighting)
        .options(joinedload(Sighting.species))
        .filter(Sighting.verification_status == "verified", Sighting.species_id.isnot(None))
        .all()
    )
    by_species: dict[int, list[Sighting]] = {}
    for sighting in verified:
        by_species.setdefault(sighting.species_id, []).append(sighting)
    new_area_km = float(settings["alert_new_area_km"])
    for species_id, group in by_species.items():
        species = group[0].species
        if species is None or species.classification != "invasive":
            continue
        for sighting in group:
            others = [other for other in group if other.id != sighting.id]
            nearest = min(
                (haversine_km(sighting.latitude, sighting.longitude, other.latitude, other.longitude) for other in others),
                default=10**9,
            )
            if nearest <= new_area_km:
                continue
            _add_alert(
                db,
                species_id=species.id,
                cluster_id=None,
                alert_type="new_area",
                risk_level="critical" if species.risk_level == "critical" else "high",
                title=f"{species.common_name} recorded in a new area",
                description=f"A verified {species.common_name} sighting has no nearby verified record of the same species.",
                reason=(
                    f"No other verified sighting of {species.scientific_name} lies within "
                    f"{new_area_km:.0f} km. Nearest recorded distance: "
                    + ("none" if nearest >= 10**8 else f"{nearest:.1f} km")
                    + "."
                ),
                location_name=sighting.location_name,
                latitude=sighting.latitude,
                longitude=sighting.longitude,
                dedupe_key=f"new_area:{species.id}:{round(sighting.latitude, 1)}:{round(sighting.longitude, 1)}",
            )
        for sighting in group:
            for region in _regions_containing(db, sighting.latitude, sighting.longitude):
                _add_alert(
                    db,
                    species_id=species.id,
                    cluster_id=None,
                    alert_type="sensitive_region",
                    risk_level="critical" if species.risk_level == "critical" else "high",
                    title=f"{species.common_name} near {region.name}",
                    description=f"A verified invasive sighting falls inside {region.name}.",
                    reason=(
                        f"The sighting is within the configured {region.radius_km:.1f} km radius of "
                        f"sensitive region '{region.name}'."
                    ),
                    location_name=region.name,
                    latitude=sighting.latitude,
                    longitude=sighting.longitude,
                    dedupe_key=f"sensitive_region:{species.id}:{region.id}:{sighting.id}",
                )
    db.commit()
    return db.query(Alert).filter(Alert.status == "open").all()


def _add_alert(db: Session, **fields) -> None:
    cutoff = utcnow() - timedelta(days=30)
    reviewed = (
        db.query(Alert)
        .filter(Alert.dedupe_key == fields["dedupe_key"], Alert.status == "reviewed", Alert.reviewed_at.isnot(None), Alert.reviewed_at >= cutoff)
        .first()
    )
    if reviewed is not None:
        return
    db.add(Alert(status="open", **fields))


def _regions_containing(db: Session, latitude: float, longitude: float) -> list[SensitiveRegion]:
    if postgis_enabled() and database.engine is not None:
        rows = db.execute(
            text(
                """
                SELECT id FROM sensitive_regions
                WHERE geom IS NOT NULL
                  AND ST_DWithin(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        radius_km * 1000
                      )
                """
            ),
            {"lat": latitude, "lng": longitude},
        ).fetchall()
        return [db.get(SensitiveRegion, row.id) for row in rows if db.get(SensitiveRegion, row.id) is not None]
    hits = []
    for region in db.query(SensitiveRegion).all():
        distance = haversine_km(latitude, longitude, region.center_latitude, region.center_longitude)
        if distance <= region.radius_km:
            hits.append(region)
    return hits
