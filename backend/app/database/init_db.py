"""Schema creation and optional PostGIS geometry columns."""

from pathlib import Path

from sqlalchemy import text

from app.database import session as database
from app.models.entities import Base

POINT_TABLES = ("sightings", "clusters", "sensitive_regions")
LAT_COLUMNS = {
    "sightings": ("latitude", "longitude"),
    "clusters": ("center_latitude", "center_longitude"),
    "sensitive_regions": ("center_latitude", "center_longitude"),
}


def init_db(upload_dir: str) -> None:
    current = database.current_engine()
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=current)
    if current.dialect.name == "postgresql":
        ensure_postgis()


def ensure_postgis() -> None:
    current = database.engine
    if current is None or current.dialect.name != "postgresql":
        return
    with current.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        for table in POINT_TABLES:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326)")
            )
            connection.execute(
                text(f"CREATE INDEX IF NOT EXISTS idx_{table}_geom ON {table} USING GIST (geom)")
            )
            lat_col, lng_col = LAT_COLUMNS[table]
            connection.execute(
                text(
                    f"""
                    UPDATE {table}
                    SET geom = ST_SetSRID(ST_MakePoint({lng_col}, {lat_col}), 4326)
                    WHERE geom IS NULL
                    """
                )
            )


def assign_geom(db, table: str, row_id: int, latitude: float, longitude: float) -> None:
    current = database.engine
    if current is None or current.dialect.name != "postgresql":
        return
    if table not in POINT_TABLES:
        raise ValueError("Unsupported spatial table.")
    db.execute(
        text(
            f"UPDATE {table} SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"
        ),
        {"lng": longitude, "lat": latitude, "id": row_id},
    )


def postgis_enabled() -> bool:
    current = database.engine
    if current is None or current.dialect.name != "postgresql":
        return False
    try:
        with current.connect() as connection:
            row = connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
            ).scalar()
        return bool(row)
    except Exception:
        return False
