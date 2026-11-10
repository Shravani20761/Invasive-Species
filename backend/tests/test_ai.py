import io

import numpy as np
from PIL import Image

from app.ai.catalog import by_slug
from app.ai.rendering import render_signature
from tests.helpers import auth_header, register


def jpeg_bytes(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(array.astype(np.uint8)).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def signature_jpeg(slug: str, seed: int = 11) -> bytes:
    return jpeg_bytes(render_signature(by_slug()[slug], np.random.default_rng(seed)))


def test_signature_is_recognised_and_repeatable(client):
    headers = auth_header(register(client)["access_token"])
    payload = signature_jpeg("giant-african-snail", seed=21)
    first = client.post("/api/ai/identify", headers=headers, files={"image": ("snail.jpg", payload, "image/jpeg")}, data={"category": "animal"})
    second = client.post("/api/ai/identify", headers=headers, files={"image": ("snail.jpg", payload, "image/jpeg")}, data={"category": "animal"})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["inference_mode"] == "demo"
    assert body["scientific_name"] == "Lissachatina fulica"
    assert body["insufficient_confidence"] is False
    assert body["confidence"] == second.json()["confidence"]
    assert "not a field-trained" in body["demo_notice"].lower() or "not" in body["demo_notice"].lower()
    assert body["detections"]["detector"]


def test_noise_is_low_confidence(client):
    headers = auth_header(register(client)["access_token"])
    noise = jpeg_bytes(np.random.default_rng(4).integers(0, 256, size=(120, 120, 3), dtype=np.uint8))
    response = client.post("/api/ai/identify", headers=headers, files={"image": ("noise.jpg", noise, "image/jpeg")}, data={"category": "plant"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["insufficient_confidence"] is True
    assert body["classification"] == "unknown"


def test_plant_pipeline_rejects_animal_category_mix(client):
    headers = auth_header(register(client)["access_token"])
    payload = signature_jpeg("lantana", seed=8)
    response = client.post("/api/ai/identify", headers=headers, files={"image": ("plant.jpg", payload, "image/jpeg")}, data={"category": "plant"})
    assert response.status_code == 200, response.text
    assert response.json()["category"] == "plant"
    assert response.json()["scientific_name"] == "Lantana camara"


def test_invalid_image_is_rejected(client):
    headers = auth_header(register(client)["access_token"])
    response = client.post("/api/ai/identify", headers=headers, files={"image": ("notes.txt", b"not an image", "text/plain")})
    assert response.status_code == 400
    tiny = jpeg_bytes(np.zeros((8, 8, 3), dtype=np.uint8))
    small = client.post("/api/ai/identify", headers=headers, files={"image": ("tiny.jpg", tiny, "image/jpeg")})
    assert small.status_code == 400
