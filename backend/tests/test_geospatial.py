from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.database import session as database
from app.geospatial.geo import haversine_km
from app.models.entities import Sighting, Species, User
from tests.helpers import auth_header, register


def _user(role: str, email: str) -> User:
    return User(email=email, full_name=role.title(), hashed_password=hash_password("password123"), role=role)


def test_haversine_degree_is_about_111_km():
    distance = haversine_km(0, 0, 1, 0)
    assert 110 < distance < 112


def test_clusters_are_split_by_species_and_small_sets_stay_empty(client):
    citizen = register(client, email="observer@example.com")
    db = database.SessionLocal()
    researcher = _user("researcher", "researcher@example.com")
    plant_a = Species(common_name="Lantana", scientific_name="Lantana camara", category="plant", classification="invasive", risk_level="high")
    plant_b = Species(common_name="Neem", scientific_name="Azadirachta indica", category="plant", classification="native", risk_level="low")
    db.add_all([researcher, plant_a, plant_b])
    db.flush()
    now = datetime.now(timezone.utc)
    points = {
        plant_a.id: [(12.00, 77.00), (12.01, 77.01), (12.015, 76.995), (11.995, 77.008), (12.008, 77.004)],
        plant_b.id: [(12.008, 77.002), (12.012, 77.006), (11.998, 76.998), (12.004, 77.012), (12.002, 77.001)],
    }
    for species_id, coords in points.items():
        for index, (lat, lng) in enumerate(coords):
            db.add(
                Sighting(
                    user_id=citizen["user"]["id"],
                    species_id=species_id,
                    image_path="/uploads/missing.jpg",
                    image_sha256=f"{species_id}-{index}",
                    latitude=lat,
                    longitude=lng,
                    location_name="Test block",
                    observed_at=now - timedelta(days=40 - index),
                    confidence=0.9,
                    verification_status="verified",
                    category="plant",
                    is_demonstration=False,
                    insufficient_confidence=False,
                )
            )
    db.add(
        Sighting(
            user_id=citizen["user"]["id"],
            species_id=plant_a.id,
            image_path="/uploads/missing.jpg",
            image_sha256="lonely",
            latitude=20,
            longitude=80,
            location_name="Far",
            observed_at=now,
            confidence=0.5,
            verification_status="verified",
            category="plant",
            is_demonstration=False,
            insufficient_confidence=False,
        )
    )
    db.commit()
    db.close()
    token = client.post("/api/auth/login", json={"email": "researcher@example.com", "password": "password123"}).json()["access_token"]
    analysed = client.post("/api/clusters/analyze", headers=auth_header(token))
    assert analysed.status_code == 200, analysed.text
    clusters = analysed.json()["items"]
    assert len(clusters) == 2
    assert {item["scientific_name"] for item in clusters} == {"Lantana camara", "Azadirachta indica"}
    lantana = next(item for item in clusters if item["scientific_name"] == "Lantana camara")
    assert lantana["sighting_count"] == 5

    db = database.SessionLocal()
    db.query(Sighting).delete()
    db.commit()
    db.close()
    again = client.post("/api/clusters/analyze", headers=auth_header(token))
    assert again.status_code == 200
    assert again.json()["items"] == []


def test_bbox_filter(client):
    created = register(client)
    db = database.SessionLocal()
    user_id = created["user"]["id"]
    for index, (lat, lng) in enumerate([(10.2, 10.2), (40.2, 40.2)]):
        db.add(
            Sighting(
                user_id=user_id,
                image_path="/uploads/missing.jpg",
                image_sha256=f"box-{index}",
                latitude=lat,
                longitude=lng,
                location_name="Box",
                observed_at=datetime.now(timezone.utc),
                verification_status="verified",
                category="plant",
                is_demonstration=False,
                insufficient_confidence=False,
            )
        )
    db.commit()
    db.close()
    response = client.get(
        "/api/map/sightings",
        headers=auth_header(created["access_token"]),
        params={"min_lat": 9, "max_lat": 11, "min_lng": 9, "max_lng": 11},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["latitude"] == 10.2
