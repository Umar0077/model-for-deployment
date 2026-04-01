"""Middleware for adding unique request ID to each request"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Add to request state
        request.state.request_id = request_id
        
        # Add to logging context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
