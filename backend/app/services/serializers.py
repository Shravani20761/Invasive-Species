"""Serialize ORM rows into API dictionaries."""

from __future__ import annotations

from app.models.entities import Alert, Cluster, Sighting, Species, User, VerificationRecord


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


def species_out(species: Species, sighting_count: int = 0) -> dict:
    return {
        "id": species.id,
        "common_name": species.common_name,
        "scientific_name": species.scientific_name,
        "category": species.category,
        "classification": species.classification,
        "description": species.description,
        "risk_level": species.risk_level,
        "characteristics": species.characteristics,
        "reference_image": species.reference_image,
        "distribution": species.distribution,
        "is_demonstration": species.is_demonstration,
        "sighting_count": sighting_count,
        "updated_at": species.updated_at,
    }


def prediction_out(prediction) -> dict | None:
    if prediction is None:
        return None
    return {
        "id": prediction.id,
        "model_name": prediction.model_name,
        "model_version": prediction.model_version,
        "inference_mode": prediction.inference_mode,
        "pipeline": prediction.pipeline,
        "predicted_label": prediction.predicted_label,
        "scientific_name": prediction.scientific_name,
        "category": prediction.category,
        "classification": prediction.classification,
        "confidence": prediction.confidence,
        "insufficient_confidence": prediction.insufficient_confidence,
        "raw_scores": prediction.raw_scores,
        "created_at": prediction.created_at,
    }


def verification_out(record: VerificationRecord) -> dict:
    reviewer = record.reviewer.full_name if record.reviewer is not None else ""
    return {
        "id": record.id,
        "action": record.action,
        "comment": record.comment,
        "previous_status": record.previous_status,
        "new_status": record.new_status,
        "reviewer_name": reviewer,
        "created_at": record.created_at,
    }


def sighting_out(sighting: Sighting) -> dict:
    species = sighting.species
    latest = None
    if sighting.predictions:
        latest = max(sighting.predictions, key=lambda item: item.id or 0)
    return {
        "id": sighting.id,
        "user_id": sighting.user_id,
        "observer_name": sighting.observer.full_name if sighting.observer is not None else "",
        "species_id": sighting.species_id,
        "common_name": species.common_name if species is not None else (sighting.submitted_name or "Unidentified"),
        "scientific_name": species.scientific_name if species is not None else (latest.scientific_name if latest else None),
        "classification": species.classification if species is not None else "unknown",
        "category": species.category if species is not None else sighting.category,
        "image_url": sighting.image_path,
        "latitude": sighting.latitude,
        "longitude": sighting.longitude,
        "location_name": sighting.location_name,
        "observed_at": sighting.observed_at,
        "created_at": sighting.created_at,
        "confidence": sighting.confidence,
        "verification_status": sighting.verification_status,
        "risk_level": sighting.risk_level,
        "submitted_name": sighting.submitted_name,
        "notes": sighting.notes,
        "is_demonstration": sighting.is_demonstration,
        "insufficient_confidence": sighting.insufficient_confidence,
        "prediction": prediction_out(latest),
        "verification_history": [verification_out(item) for item in (sighting.verifications or [])],
    }


def cluster_out(cluster: Cluster) -> dict:
    species = cluster.species
    return {
        "id": cluster.id,
        "species_id": cluster.species_id,
        "common_name": species.common_name if species is not None else "Unknown",
        "scientific_name": species.scientific_name if species is not None else None,
        "classification": species.classification if species is not None else "unknown",
        "category": species.category if species is not None else None,
        "sighting_count": cluster.sighting_count,
        "center_latitude": cluster.center_latitude,
        "center_longitude": cluster.center_longitude,
        "radius_km": cluster.radius_km,
        "first_detected": cluster.first_detected,
        "last_detected": cluster.last_detected,
        "growth_indicator": cluster.growth_indicator,
        "growth_ratio": cluster.growth_ratio,
        "risk_level": cluster.risk_level,
        "sighting_ids": [sighting.id for sighting in cluster.sightings] if cluster.sightings is not None else [],
    }


def alert_out(alert: Alert) -> dict:
    species = alert.species
    return {
        "id": alert.id,
        "species_id": alert.species_id,
        "common_name": species.common_name if species is not None else None,
        "scientific_name": species.scientific_name if species is not None else None,
        "cluster_id": alert.cluster_id,
        "alert_type": alert.alert_type,
        "risk_level": alert.risk_level,
        "title": alert.title,
        "description": alert.description,
        "reason": alert.reason,
        "location_name": alert.location_name,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "status": alert.status,
        "created_at": alert.created_at,
        "reviewed_at": alert.reviewed_at,
        "review_comment": alert.review_comment,
    }
