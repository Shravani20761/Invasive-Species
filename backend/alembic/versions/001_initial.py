"""Create tables and, on PostgreSQL, PostGIS geometry columns."""

from alembic import op
from sqlalchemy import text

from app.models.entities import Base

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name != "postgresql":
        return
    op.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    for table in ("sightings", "clusters", "sensitive_regions"):
        op.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326)"))
        op.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_geom ON {table} USING GIST (geom)"))


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
