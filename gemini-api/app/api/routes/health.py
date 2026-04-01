"""Health check routes"""

from fastapi import APIRouter, Request
from datetime import datetime
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint
    Returns server status and configuration
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
        "request_id": request.state.request_id
    }


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "health": "GET /health",
            "docs": "GET /docs",
            "generate": "POST /api/v1/generate",
            "summarize": "POST /api/v1/summarize",
            "extract": "POST /api/v1/extract",
            "analyze_emotions": "POST /api/v1/analyze-emotions"
        }
    }
