"""Rate limiting middleware"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings


def get_rate_limit_string() -> str:
    """Get rate limit string from settings"""
    return f"{settings.rate_limit_requests}/{settings.rate_limit_period}second"


# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[get_rate_limit_string()] if settings.rate_limit_enabled else [],
    enabled=settings.rate_limit_enabled
)
