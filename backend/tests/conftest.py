import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="isr-tests-"))
os.environ["DATABASE_URL"] = "sqlite:///" + (_TMP / "test.db").as_posix()
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["MODEL_PATH"] = str(_TMP / "species_demo.joblib")
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["ENVIRONMENT"] = "test"
os.environ["INFERENCE_MODE"] = "demo"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database import session as database
from app.main import app
from app.models.entities import Base

get_settings.cache_clear()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        Base.metadata.drop_all(bind=database.engine)
        Base.metadata.create_all(bind=database.engine)
        yield test_client
