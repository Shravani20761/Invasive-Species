"""Load a clearly labelled synthetic demonstration dataset.

Nothing in this script is a field observation. Images are colour signatures used to
exercise the demo classifier, and every sighting is stored with is_demonstration=True.
"""

from __future__ import annotations

import hashlib
import io
import math
from datetime import timedelta
from pathlib import Path

import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from app.ai.catalog import CATALOG, by_slug
from app.ai.demo_model import load_bundle
from app.ai.rendering import render_signature
from app.core.config import get_settings
from app.core.security import hash_password
from app.database.init_db import assign_geom, init_db
from app.database import session as database
from app.models.entities import (
    Base,
    ModelMetadata,
    Prediction,
    SensitiveRegion,
    Sighting,
    Species,
    User,
    VerificationRecord,
    utcnow,
)
from app.services.clustering_service import analyze_clusters
from app.services.settings_service import ensure_default_settings, get_app_settings
from app.services.ai_service import identify_image

DEMO_NOTE = "Synthetic demonstration record. Not a field observation."
DEMO_USERS = (
    ("admin@example.com", "DemoAdmin#2026", "Demo Administrator", "admin"),
    ("researcher@example.com", "DemoResearch#2026", "Demo Researcher", "researcher"),
    ("citizen@example.com", "DemoCitizen#2026", "Demo Field Observer", "citizen"),
)


def seed_if_empty() -> None:
    if database.SessionLocal is None:
        return
    db = database.SessionLocal()
    try:
        if db.query(User).count() == 0:
            run_seed(db)
    finally:
        db.close()


def run_seed(db: Session) -> None:
    bundle = load_bundle()
    meta = bundle["metadata"]
    existing_model = db.query(ModelMetadata).filter_by(name=meta["name"], version=meta["version"]).one_or_none()
    if existing_model is None:
        db.add(
            ModelMetadata(
                name=meta["name"],
                version=meta["version"],
                inference_mode="demo",
                description=meta["limitation"],
                metrics=meta["metrics"],
            )
        )
    users: dict[str, User] = {}
    for email, password, name, role in DEMO_USERS:
        users[role] = _ensure_user(db, email, password, name, role)
    ensure_default_settings(db)
    if db.query(Sighting).count():
        db.commit()
        return
    species = _ensure_species(db)
    region = SensitiveRegion(
        name="DEMO Sensitive Region — Hebbal wetland sample",
        description="Synthetic protected-area boundary used to exercise the sensitive-region alert rule.",
        center_latitude=13.046,
        center_longitude=77.592,
        radius_km=6,
        is_demonstration=True,
    )
    db.add(region)
    db.flush()
    assign_geom(db, "sensitive_regions", region.id, region.center_latitude, region.center_longitude)
    _insert_sightings(db, species, users)
    db.commit()
    analyze_clusters(db)
    _assert_demo_story(db)


def _ensure_user(db: Session, email: str, password: str, name: str, role: str) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is not None:
        return user
    user = User(email=email, full_name=name, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.flush()
    return user


def _ensure_species(db: Session) -> dict[str, Species]:
    upload = Path(get_settings().upload_dir) / "samples"
    upload.mkdir(parents=True, exist_ok=True)
    stored: dict[str, Species] = {}
    for index, entry in enumerate(CATALOG):
        rendered = render_signature(entry, np.random.default_rng(1000 + index))
        data = _jpeg_bytes(rendered)
        filename = upload / f"{entry['slug']}.jpg"
        filename.write_bytes(data)
        species = db.query(Species).filter(Species.scientific_name == entry["scientific_name"]).one_or_none()
        if species is None:
            species = Species(
                common_name=entry["common_name"],
                scientific_name=entry["scientific_name"],
                category=entry["category"],
                classification=entry["classification"],
                description=entry["description"],
                risk_level=entry["risk_level"],
                characteristics=entry["characteristics"],
                distribution=entry["distribution"],
                reference_image=f"/uploads/samples/{entry['slug']}.jpg",
                is_demonstration=True,
            )
            db.add(species)
            db.flush()
        else:
            species.reference_image = f"/uploads/samples/{entry['slug']}.jpg"
            species.is_demonstration = True
        stored[entry["slug"]] = species
    return stored


def _insert_sightings(db: Session, species: dict[str, Species], users: dict[str, User]) -> None:
    groups = [
        ("lantana", 11.410, 76.690, [160, 140, 120, 40, 28, 18, 9, 3], "verified", "DEMO: Nilgiri block A", 2.0),
        ("water-hyacinth", 12.960, 77.590, [150, 130, 110, 55, 35, 18], "verified", "DEMO: south Bengaluru water sample", 2.0),
        ("giant-african-snail", 13.220, 77.400, [100, 80, 20, 8, 2], "verified", "DEMO: north Bengaluru verge sample", 1.8),
        ("parthenium", 11.560, 76.820, [140, 110, 90, 40, 15], "verified", "DEMO: Nilgiri roadside sample", 1.8),
        ("mozambique-tilapia", 12.780, 77.720, [100, 75, 45, 15], "verified", "DEMO: east reservoir sample", 1.6),
        ("sailfin-catfish", 10.900, 76.950, [18, 12, 6, 2], "verified", "DEMO: southern canal sample", 1.4),
        ("mesquite", 26.912, 75.787, [60], "verified", "DEMO: Jaipur arid block", 0.4),
        ("neem", 15.400, 73.850, [80], "verified", "DEMO: coastal plain sample", 0.3),
        ("neem", 19.050, 72.870, [50], "verified", "DEMO: western city grove sample", 0.3),
        ("neem", 8.720, 77.050, [30], "verified", "DEMO: far southern grove sample", 0.3),
        ("peacock", 11.800, 78.200, [70], "verified", "DEMO: eastern scrub sample", 0.3),
        ("peacock", 14.450, 75.920, [25], "verified", "DEMO: central plateau sample", 0.3),
        ("chital", 21.500, 78.900, [90], "verified", "DEMO: central forest sample", 0.3),
        ("chital", 22.600, 75.300, [40], "verified", "DEMO: western forest sample", 0.3),
        ("tulsi", 23.030, 72.570, [35], "verified", "DEMO: cultivated margin sample", 0.3),
        ("tulsi", 28.450, 77.100, [12], "verified", "DEMO: northern garden sample", 0.3),
    ]
    sequence = 0
    for slug, lat, lng, days, status, location, spread in groups:
        for point, day in zip(_ring(lat, lng, len(days), spread), days):
            _add_rendered_sighting(db, species[slug], users, point, day, status, location, sequence)
            sequence += 1
    _add_rendered_sighting(
        db,
        species["water-hyacinth"],
        users,
        (13.046, 77.592),
        12,
        "verified",
        "DEMO: Hebbal wetland sample",
        sequence,
    )
    sequence += 1
    _add_rendered_sighting(db, species["lantana"], users, (11.425, 76.705), 6, "pending", "DEMO: Nilgiri block A", sequence)
    sequence += 1
    _add_rendered_sighting(db, species["peacock"], users, (11.790, 78.190), 4, "pending", "DEMO: eastern scrub sample", sequence)
    sequence += 1
    _add_noise_sighting(db, users, (12.500, 77.200), 2, sequence)
    sequence += 1
    _add_rendered_sighting(db, species["lantana"], users, (11.430, 76.680), 5, "rejected", "DEMO: Nilgiri block A", sequence)
    sequence += 1
    _add_rendered_sighting(db, species["parthenium"], users, (11.548, 76.810), 9, "rejected", "DEMO: Nilgiri roadside sample", sequence)


def _add_rendered_sighting(db, species: Species, users, point, days_ago, status, location, sequence: int) -> None:
    entry = by_slug()[next(item["slug"] for item in CATALOG if item["scientific_name"] == species.scientific_name)]
    image = Image.fromarray(render_signature(entry, np.random.default_rng(7000 + sequence)))
    threshold = float(get_app_settings(db)["low_confidence_threshold"])
    result = identify_image(image, species.category, threshold)
    if result["insufficient_confidence"] or result["scientific_name"] != species.scientific_name:
        raise RuntimeError(
            "The demo classifier did not recognise its own synthetic signature for "
            f"{species.scientific_name}. Got {result['scientific_name']} at {result['confidence']}."
        )
    _store_sighting(db, users, image, result, point, days_ago, status, location, species, sequence)


def _add_noise_sighting(db, users, point, days_ago, sequence: int) -> None:
    rng = np.random.default_rng(3)
    image = Image.fromarray(rng.integers(0, 256, size=(180, 180, 3), dtype=np.uint8))
    threshold = float(get_app_settings(db)["low_confidence_threshold"])
    result = identify_image(image, "plant", threshold)
    _store_sighting(db, users, image, result, point, days_ago, "pending", "DEMO: unclear photograph sample", None, sequence)


def _store_sighting(db, users, image, result, point, days_ago, status, location, species, sequence) -> None:
    data = _jpeg_bytes(np.asarray(image))
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(get_settings().upload_dir) / "demo"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"demo-{sequence:03d}.jpg"
    (folder / filename).write_bytes(data)
    observer = users["citizen"] if sequence % 5 else users["researcher"]
    linked = None
    if species is not None and not result["insufficient_confidence"]:
        linked = species
    sighting = Sighting(
        user_id=observer.id,
        species_id=linked.id if linked is not None else None,
        image_path=f"/uploads/demo/{filename}",
        image_sha256=digest,
        latitude=point[0],
        longitude=point[1],
        location_name=location,
        observed_at=utcnow() - timedelta(days=days_ago),
        confidence=result["confidence"],
        verification_status=status,
        risk_level=None if result["insufficient_confidence"] else result["risk_level"],
        category=result["category"],
        submitted_name="" if species is None else species.common_name,
        notes=DEMO_NOTE,
        is_demonstration=True,
        insufficient_confidence=result["insufficient_confidence"],
    )
    db.add(sighting)
    db.flush()
    assign_geom(db, "sightings", sighting.id, sighting.latitude, sighting.longitude)
    db.add(
        Prediction(
            sighting_id=sighting.id,
            model_name=result["model_name"],
            model_version=result["model_version"],
            inference_mode=result["inference_mode"],
            pipeline=result.get("pipeline") or sighting.category or "",
            predicted_label=result["predicted_common_name"],
            scientific_name=result["scientific_name"],
            category=result["category"],
            classification=result["classification"],
            confidence=result["confidence"],
            insufficient_confidence=result["insufficient_confidence"],
            raw_scores=result["raw_scores"],
        )
    )
    if status != "pending":
        reviewer = users["researcher"]
        db.add(
            VerificationRecord(
                sighting_id=sighting.id,
                reviewer_id=reviewer.id,
                action="approve" if status == "verified" else "reject",
                comment="Demonstration review of a synthetic record. Not a field inspection.",
                previous_status="pending",
                new_status=status,
            )
        )


def _assert_demo_story(db: Session) -> None:
    from app.models.entities import Alert, Cluster

    clusters = db.query(Cluster).all()
    alerts = db.query(Alert).all()
    types = {alert.alert_type for alert in alerts}
    required = {"concentration", "cluster_expansion", "new_area", "sensitive_region"}
    if not required.issubset(types):
        summary = [(cluster.species_id, cluster.sighting_count, cluster.growth_indicator, round(cluster.growth_ratio, 2)) for cluster in clusters]
        raise RuntimeError(f"Demonstration alerts missing {required - types}. Clusters: {summary}. Alerts: {sorted(types)}.")
    if not any(cluster.growth_indicator == "emerging" for cluster in clusters):
        raise RuntimeError("Demonstration data did not produce an emerging cluster.")
    stable_small = [
        cluster
        for cluster in clusters
        if cluster.growth_indicator in {"stable", "declining"} and cluster.sighting_count < 6
    ]
    if not stable_small:
        raise RuntimeError("Expected a small stable cluster that does not meet the alert-size rule.")


def _ring(lat: float, lng: float, count: int, spread_km: float) -> list[tuple[float, float]]:
    if count == 1:
        return [(lat, lng)]
    points = []
    for index in range(count):
        angle = (index / count) * math.tau
        distance = spread_km
        dlat = (distance / 111.0) * math.cos(angle)
        dlng = (distance / (111.0 * max(math.cos(math.radians(lat)), 0.2))) * math.sin(angle)
        points.append((round(lat + dlat, 6), round(lng + dlng, 6)))
    return points


def _jpeg_bytes(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(array.astype(np.uint8)).save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Seed synthetic demonstration data.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the database before seeding.")
    args = parser.parse_args()
    settings = get_settings()
    configure_engine = database.configure_engine
    configure_engine(settings.database_url)
    if args.reset and database.engine is not None:
        Base.metadata.drop_all(bind=database.engine)
    init_db(settings.upload_dir)
    db = database.SessionLocal()
    try:
        if args.reset or db.query(User).count() == 0:
            run_seed(db)
            print("Synthetic demonstration data is ready.")
            print("Administrator: admin@example.com / DemoAdmin#2026")
            print("Researcher:    researcher@example.com / DemoResearch#2026")
            print("Citizen:       citizen@example.com / DemoCitizen#2026")
        else:
            print("Users already exist. Run with --reset to rebuild the demonstration database.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
