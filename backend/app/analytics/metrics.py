"""Analytics calculated from stored sightings."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.geospatial.geo import as_utc
from app.models.entities import Alert, Cluster, Sighting, User


def analytics_query(
    db: Session,
    user: User,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    species_id: int | None = None,
    location: str | None = None,
    include_unverified: bool = False,
):
    if include_unverified and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an administrator can include unverified records in analytics.")
    query = db.query(Sighting).options(joinedload(Sighting.species))
    query = query.filter(Sighting.verification_status != "rejected")
    if include_unverified:
        query = query.filter(Sighting.verification_status.in_(["verified", "pending"]))
    else:
        query = query.filter(Sighting.verification_status == "verified")
    if start is not None:
        query = query.filter(Sighting.observed_at >= start)
    if end is not None:
        query = query.filter(Sighting.observed_at <= end)
    if species_id is not None:
        query = query.filter(Sighting.species_id == species_id)
    if location:
        query = query.filter(Sighting.location_name.ilike(f"%{location}%"))
    return query


def overview(db: Session, user: User, **filters) -> dict:
    rows = analytics_query(db, user, **filters).all()
    invasive_ids = {
        row.species_id
        for row in rows
        if row.species is not None and row.species.classification == "invasive"
    }
    species_counts = Counter(row.species.common_name for row in rows if row.species is not None)
    category_counts = Counter((row.species.category if row.species is not None else row.category or "unknown") for row in rows)
    recent = sorted(rows, key=lambda row: row.observed_at, reverse=True)[:6]
    emerging = (
        db.query(Cluster)
        .options(joinedload(Cluster.species))
        .filter(Cluster.growth_indicator == "emerging")
        .all()
    )
    open_alerts = db.query(Alert).options(joinedload(Alert.species)).filter(Alert.status == "open").order_by(Alert.created_at.desc()).limit(5).all()
    pending = db.query(Sighting).filter(Sighting.verification_status == "pending").count()
    rejected = db.query(Sighting).filter(Sighting.verification_status == "rejected").count()
    if user.role == "citizen":
        pending = db.query(Sighting).filter(Sighting.verification_status == "pending", Sighting.user_id == user.id).count()
        rejected = db.query(Sighting).filter(Sighting.verification_status == "rejected", Sighting.user_id == user.id).count()
    demonstration = sum(1 for row in rows if row.is_demonstration)
    notice = None
    if demonstration:
        notice = (
            "Figures on this dashboard are calculated from stored records. "
            "The current database includes synthetic demonstration sightings, which are not field reports."
        )
    return {
        "total_sightings": len(rows),
        "invasive_species": len(invasive_ids),
        "verified_reports": sum(1 for row in rows if row.verification_status == "verified"),
        "active_clusters": db.query(Cluster).count(),
        "pending_reports": pending,
        "rejected_reports": rejected,
        "open_alerts": db.query(Alert).filter(Alert.status == "open").count(),
        "recent_sightings": recent,
        "species_distribution": [{"name": name, "count": count} for name, count in species_counts.most_common(8)],
        "category_distribution": [{"name": name.title(), "value": count} for name, count in category_counts.items()],
        "active_alerts": open_alerts,
        "emerging_clusters": emerging,
        "demonstration_records": demonstration,
        "data_notice": notice,
    }


def trends(rows: list[Sighting]) -> dict:
    daily: Counter[str] = Counter()
    weekly: Counter[str] = Counter()
    monthly: Counter[str] = Counter()
    for row in rows:
        stamp = as_utc(row.observed_at)
        daily[stamp.date().isoformat()] += 1
        weekly[f"{stamp.isocalendar().year}-W{stamp.isocalendar().week:02d}"] += 1
        monthly[stamp.strftime("%Y-%m")] += 1
    growth = []
    cumulative = 0
    for period in sorted(monthly):
        cumulative += monthly[period]
        growth.append({"period": period, "count": monthly[period], "cumulative": cumulative})
    return {
        "daily": [{"date": key, "count": daily[key]} for key in sorted(daily)],
        "weekly": [{"period": key, "count": weekly[key]} for key in sorted(weekly)],
        "monthly": [{"period": key, "count": monthly[key]} for key in sorted(monthly)],
        "growth": growth,
    }


def species_breakdown(rows: list[Sighting]) -> dict:
    invasive: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    classifications: Counter[str] = Counter()
    for row in rows:
        if row.species is None:
            categories[(row.category or "unknown").title()] += 1
            classifications["unknown"] += 1
            continue
        categories[row.species.category.title()] += 1
        classifications[row.species.classification] += 1
        if row.species.classification == "invasive":
            invasive[row.species.common_name] += 1
    return {
        "top_invasive": [{"name": name, "count": count} for name, count in invasive.most_common(8)],
        "category_distribution": [{"name": name, "value": count} for name, count in sorted(categories.items())],
        "classification_distribution": [{"name": name.title(), "value": count} for name, count in sorted(classifications.items())],
    }


def region_breakdown(rows: list[Sighting]) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        label = row.location_name.strip() or "Unnamed location"
        counts[label] += 1
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return {"regions": [{"region": name, "count": count} for name, count in ordered[:12]]}
