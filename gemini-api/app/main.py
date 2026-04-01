"""Main FastAPI application"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
import structlog

from app.config import settings
from app.api.routes import health, gemini
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.rate_limiter import limiter
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered API using Google Gemini for text generation, summarization, and structured data extraction",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add rate limiter to app state
app.state.limiter = limiter


# Exception handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors"""
    logger.warning(
        "rate_limit_exceeded",
        request_id=getattr(request.state, "request_id", "unknown"),
        client=request.client.host if request.client else "unknown"
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Please try again later.",
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(
        "unhandled_exception",
        request_id=getattr(request.state, "request_id", "unknown"),
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )


# Add middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        primary_model=settings.gemini_model_id,
        fallback_model=settings.gemini_fallback_model_id,
        rate_limiting=settings.rate_limit_enabled,
        api_key_required=settings.api_key is not None
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information"""
    logger.info("application_shutdown")


# Include routers
app.include_router(health.router)
app.include_router(gemini.router)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    
    response = await call_next(request)
    
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code
    )
    
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
