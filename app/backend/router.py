from fastapi import APIRouter

from app.backend.api.v1.analysis import router as analysis_router
from app.backend.api.v1.comparison import router as comparison_router
from app.backend.api.v1.sites import router as sites_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(analysis_router)
api_router.include_router(comparison_router)
api_router.include_router(sites_router)
