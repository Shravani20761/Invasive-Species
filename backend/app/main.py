import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.database.init_db import init_db, postgis_enabled
from app.database.session import configure_engine
from app.database import session as database

logger = logging.getLogger("invasive_species_radar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_engine(settings.database_url)
    init_db(settings.upload_dir)
    if settings.seed_on_startup:
        from app.database.seed import seed_if_empty

        seed_if_empty()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Early detection and spread monitoring for invasive species. "
            "The default identifier is a demo model trained on synthetic colour signatures, "
            "not a field-trained species detector."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "database": database.engine.dialect.name if database.engine is not None else "unconfigured",
            "postgis": postgis_enabled(),
            "inference_mode": get_settings().inference_mode,
        }

    return app


app = create_app()
