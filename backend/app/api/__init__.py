"""API routes for EcoEcho AI."""

from fastapi import APIRouter

from app.api.routes import auth, projects, recordings, classifications, species, reports, batch

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(recordings.router, prefix="/recordings", tags=["Recordings"])
router.include_router(classifications.router, prefix="/classifications", tags=["Classifications"])
router.include_router(species.router, prefix="/species", tags=["Species"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
router.include_router(batch.router, prefix="/batch", tags=["Batch Processing"])
