from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.deps import get_current_user, require_roles
from app.database.session import get_db
from app.models.entities import Cluster, User
from app.services.clustering_service import analyze_clusters
from app.services.serializers import cluster_out

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.post("/analyze")
def analyze(db: Session = Depends(get_db), _: User = Depends(require_roles("researcher", "admin"))):
    rows = analyze_clusters(db)
    return {
        "total": len(rows),
        "items": [cluster_out(row) for row in rows],
        "notice": "Clusters are calculated only from verified sightings, and each species is clustered separately.",
    }


@router.get("")
def list_clusters(
    species_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Cluster).options(joinedload(Cluster.species), selectinload(Cluster.sightings))
    if species_id is not None:
        query = query.filter(Cluster.species_id == species_id)
    rows = query.order_by(Cluster.sighting_count.desc()).all()
    return {"items": [cluster_out(row) for row in rows], "total": len(rows)}


@router.get("/{cluster_id}")
def get_cluster(cluster_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    cluster = (
        db.query(Cluster)
        .options(joinedload(Cluster.species), selectinload(Cluster.sightings))
        .filter(Cluster.id == cluster_id)
        .first()
    )
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found.")
    return cluster_out(cluster)
