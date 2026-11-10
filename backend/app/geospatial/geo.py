import math
from datetime import datetime, timezone

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def geographic_centroid(latitudes: list[float], longitudes: list[float]) -> tuple[float, float]:
    if not latitudes:
        raise ValueError("At least one coordinate is required.")
    x = y = z = 0.0
    for lat, lng in zip(latitudes, longitudes):
        phi, lam = math.radians(lat), math.radians(lng)
        x += math.cos(phi) * math.cos(lam)
        y += math.cos(phi) * math.sin(lam)
        z += math.sin(phi)
    count = len(latitudes)
    x /= count
    y /= count
    z /= count
    hyp = math.sqrt(x * x + y * y)
    return math.degrees(math.atan2(z, hyp)), math.degrees(math.atan2(y, x))


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_coordinates(latitude: float, longitude: float) -> None:
    from fastapi import HTTPException

    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Coordinates are outside the valid latitude and longitude ranges.")
    if abs(latitude) < 1e-8 and abs(longitude) < 1e-8:
        raise HTTPException(status_code=400, detail="The coordinate 0, 0 is not accepted as an observation location.")
