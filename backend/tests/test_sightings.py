import io
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image

from app.ai.catalog import by_slug
from app.ai.rendering import render_signature
from app.core.security import hash_password
from app.database import session as database
from app.models.entities import Species, User
from tests.helpers import auth_header, register


def jpeg_of(slug: str, seed: int) -> bytes:
    array = render_signature(by_slug()[slug], np.random.default_rng(seed))
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def test_invalid_coordinates_and_duplicate_image(client):
    token = register(client)["access_token"]
    headers = auth_header(token)
    image = jpeg_of("neem", 3)
    data = {
        "latitude": "95",
        "longitude": "77",
        "category": "plant",
        "location_name": "Bad",
        "notes": "test",
    }
    rejected = client.post("/api/sightings", headers=headers, files={"image": ("n.jpg", image, "image/jpeg")}, data=data)
    assert rejected.status_code == 400
    zero = dict(data, latitude="0", longitude="0")
    rejected_zero = client.post("/api/sightings", headers=headers, files={"image": ("n.jpg", image, "image/jpeg")}, data=zero)
    assert rejected_zero.status_code == 400
    ok = client.post(
        "/api/sightings",
        headers=headers,
        files={"image": ("n.jpg", image, "image/jpeg")},
        data=dict(data, latitude="12.97", longitude="77.59", location_name="Sample block"),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["verification_status"] == "pending"
    assert ok.json()["is_demonstration"] is False
    duplicate = client.post(
        "/api/sightings",
        headers=headers,
        files={"image": ("n.jpg", image, "image/jpeg")},
        data=dict(data, latitude="12.98", longitude="77.60", location_name="Sample block"),
    )
    assert duplicate.status_code == 409


def test_rejected_sightings_stay_out_of_analytics_and_roles_are_enforced(client):
    citizen = register(client)
    db = database.SessionLocal()
    researcher = User(email="researcher@example.com", full_name="Researcher", hashed_password=hash_password("password123"), role="researcher")
    admin = User(email="admin@example.com", full_name="Admin", hashed_password=hash_password("password123"), role="admin")
    species = Species(
        common_name="Neem",
        scientific_name="Azadirachta indica",
        category="plant",
        classification="native",
        risk_level="low",
        is_demonstration=False,
    )
    db.add_all([researcher, admin, species])
    db.commit()
    db.close()
    researcher_token = client.post("/api/auth/login", json={"email": "researcher@example.com", "password": "password123"}).json()["access_token"]
    headers = auth_header(citizen["access_token"])
    observed = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    created = client.post(
        "/api/sightings",
        headers=headers,
        files={"image": ("n.jpg", jpeg_of("neem", 9), "image/jpeg")},
        data={"latitude": "12.5", "longitude": "77.2", "category": "plant", "location_name": "Block", "observed_at": observed},
    )
    assert created.status_code == 201, created.text
    sighting_id = created.json()["id"]
    forbidden = client.put(f"/api/verification/{sighting_id}/reject", headers=headers, json={"comment": "no"})
    assert forbidden.status_code == 403
    rejected = client.put(
        f"/api/verification/{sighting_id}/reject",
        headers=auth_header(researcher_token),
        json={"comment": "Image does not support the report."},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["verification_status"] == "rejected"
    overview = client.get("/api/analytics/overview", headers=auth_header(researcher_token))
    assert overview.status_code == 200
    assert overview.json()["total_sightings"] == 0
    empty = client.get("/api/analytics/trends", headers=auth_header(researcher_token))
    assert empty.status_code == 200
    assert empty.json()["daily"] == []
