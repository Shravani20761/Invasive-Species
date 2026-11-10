from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.catalog import CATALOG
from app.ai.demo_model import load_bundle
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.database.session import get_db
from app.models.entities import ModelMetadata, Species, User
from app.services.ai_service import identify_image
from app.services.image_service import validate_image_bytes
from app.services.settings_service import get_app_settings

router = APIRouter(prefix="/ai", tags=["ai"])


def _attach_species(db: Session, result: dict) -> dict:
    species = None
    if not result["insufficient_confidence"]:
        species = db.query(Species).filter(Species.scientific_name == result["scientific_name"]).first()
        if species is not None:
            result["species_id"] = species.id
            result["predicted_common_name"] = species.common_name
            result["description"] = species.description
            result["risk_level"] = species.risk_level
            result["catalogue_classification"] = species.classification
            if result["classification"] != "unknown":
                result["classification"] = species.classification
    else:
        result["species_id"] = None
    if "species_id" not in result:
        result["species_id"] = species.id if species is not None else None
    return result


@router.post("/identify")
async def identify(
    image: UploadFile = File(...),
    category: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = await image.read()
    loaded = validate_image_bytes(data)
    if category in ("", "auto"):
        category = None
    settings = get_app_settings(db)
    result = identify_image(loaded, category, float(settings["low_confidence_threshold"]))
    return _attach_species(db, result)


@router.post("/detect")
async def detect(
    image: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    data = await image.read()
    loaded = validate_image_bytes(data)
    from app.ai.models.object_detector import ObjectDetector

    return ObjectDetector().detect(loaded)


@router.get("/model")
def model_status(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    settings = get_settings()
    record = db.query(ModelMetadata).order_by(ModelMetadata.created_at.desc()).first()
    metadata = record.metrics if record is not None else {}
    limitation = record.description if record is not None else ""
    name = record.name if record is not None else None
    version = record.version if record is not None else None
    if settings.inference_mode == "demo":
        bundle = load_bundle()
        meta = bundle["metadata"]
        name = meta["name"]
        version = meta["version"]
        limitation = meta["limitation"]
        metadata = meta["metrics"]
    return {
        "inference_mode": settings.inference_mode,
        "name": name,
        "version": version,
        "limitation": limitation,
        "trained_on": "Synthetic colour signatures" if settings.inference_mode == "demo" else "Configured checkpoint",
        "metrics": metadata,
        "weights_configured": __import__("pathlib").Path(settings.torch_weights_path).exists(),
        "yolo_configured": bool(settings.yolo_weights),
        "low_confidence_threshold": get_app_settings(db)["low_confidence_threshold"],
    }


@router.get("/samples")
def samples(_: User = Depends(get_current_user)):
    items = []
    for entry in CATALOG:
        items.append(
            {
                "slug": entry["slug"],
                "common_name": entry["common_name"],
                "scientific_name": entry["scientific_name"],
                "category": entry["category"],
                "classification": entry["classification"],
                "image_url": f"/uploads/samples/{entry['slug']}.jpg",
                "notice": "Synthetic colour signature for the demo classifier, not a photograph of the species.",
            }
        )
    return {"items": items}
