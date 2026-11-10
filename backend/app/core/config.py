"""Runtime configuration. Secrets come from the environment or a root .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Invasive Species Radar"
    environment: str = "development"
    secret_key: str = "dev-only-change-me-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 12
    database_url: str = "sqlite:///" + (BACKEND_DIR / "invasive_species_radar.db").as_posix()
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_dir: str = str(BACKEND_DIR / "uploads")
    max_upload_mb: int = 8
    inference_mode: str = "demo"
    model_path: str = str(ROOT_DIR / "ml" / "models" / "species_demo.joblib")
    torch_weights_path: str = str(ROOT_DIR / "ml" / "models" / "torch_species.pt")
    yolo_weights: str = ""
    low_confidence_threshold: float = 0.45
    seed_on_startup: bool = True

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "production" and settings.secret_key.startswith("dev-"):
        raise RuntimeError("Set SECRET_KEY before running with ENVIRONMENT=production.")
    if settings.inference_mode not in {"demo", "weights"}:
        raise RuntimeError("INFERENCE_MODE must be 'demo' or 'weights'.")
    return settings
