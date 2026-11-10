"""Image validation and local storage."""

import hashlib
import io
import uuid
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def validate_image_bytes(data: bytes) -> Image.Image:
    settings = get_settings()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Images must be {settings.max_upload_mb} MB or smaller.")
    Image.MAX_IMAGE_PIXELS = 20_000_000
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="The file is not a valid JPEG, PNG, or WebP image.")
    if image.format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are accepted.")
    if image.width < 32 or image.height < 32:
        raise HTTPException(status_code=400, detail="The image is too small to analyse. Use at least 32 by 32 pixels.")
    if image.width > 8000 or image.height > 8000:
        raise HTTPException(status_code=400, detail="The image exceeds the 8000 pixel dimension limit.")
    return image.convert("RGB")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_image(image: Image.Image) -> str:
    """Store a validated RGB image as JPEG and return its public path."""
    settings = get_settings()
    directory = Path(settings.upload_dir)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    image.save(directory / filename, format="JPEG", quality=88)
    return f"/uploads/{filename}"
