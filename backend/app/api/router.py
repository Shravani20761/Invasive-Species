from fastapi import APIRouter

from app.api import alerts, analytics, auth, clusters, map, settings, sightings, species, verification
from app.api import ai as ai_routes

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(auth.users_router)
api_router.include_router(species.router)
api_router.include_router(ai_routes.router)
api_router.include_router(sightings.router)
api_router.include_router(map.router)
api_router.include_router(analytics.router)
api_router.include_router(clusters.router)
api_router.include_router(alerts.router)
api_router.include_router(verification.router)
api_router.include_router(settings.router)
