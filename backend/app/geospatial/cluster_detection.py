"""DBSCAN clustering of sightings, run separately for each species.

Coordinates are converted to radians and compared with the haversine metric.
eps is configured in kilometres and divided by the Earth radius.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.cluster import DBSCAN

from app.geospatial.geo import EARTH_RADIUS_KM, as_utc, geographic_centroid, haversine_km


def cluster_coordinates(
    points: list[dict],
    eps_km: float,
    min_samples: int,
    now: datetime | None = None,
    growth_ratio_threshold: float = 1.5,
) -> list[dict]:
    """Cluster one species. `points` items need lat, lng, sighting_id, observed_at."""
    if len(points) < min_samples:
        return []
    coords = np.array([[point["latitude"], point["longitude"]] for point in points], dtype=float)
    labels = DBSCAN(
        eps=eps_km / EARTH_RADIUS_KM,
        min_samples=min_samples,
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(np.radians(coords))
    now = as_utc(now or datetime.now(timezone.utc))
    clusters = []
    for label in sorted(set(labels)):
        if int(label) < 0:
            continue
        members = [point for point, assigned in zip(points, labels) if int(assigned) == int(label)]
        if len(members) < min_samples:
            continue
        latitudes = [member["latitude"] for member in members]
        longitudes = [member["longitude"] for member in members]
        center_lat, center_lng = geographic_centroid(latitudes, longitudes)
        radius = max(haversine_km(center_lat, center_lng, lat, lng) for lat, lng in zip(latitudes, longitudes))
        times = sorted(as_utc(member["observed_at"]) for member in members)
        first, last = times[0], times[-1]
        midpoint = first + (last - first) / 2
        older = sum(stamp <= midpoint for stamp in times)
        recent = len(times) - older
        if older == 0:
            growth = "emerging"
            ratio = float(recent)
        else:
            ratio = recent / older
            if ratio >= growth_ratio_threshold:
                growth = "growing"
            elif recent == 0 or older / max(recent, 1) >= growth_ratio_threshold:
                growth = "declining"
            else:
                growth = "stable"
        if growth != "declining" and (now - first) <= timedelta(days=30):
            growth = "emerging"
        clusters.append(
            {
                "member_ids": [member["sighting_id"] for member in members],
                "center_latitude": center_lat,
                "center_longitude": center_lng,
                "radius_km": radius,
                "sighting_count": len(members),
                "first_detected": first,
                "last_detected": last,
                "growth_indicator": growth,
                "growth_ratio": ratio,
                "older_count": older,
                "recent_count": recent,
            }
        )
    return clusters
