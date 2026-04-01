"""
Retry utility with exponential backoff
"""

import asyncio
from typing import TypeVar, Callable, Any
from functools import wraps
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            "retry_failed",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                            error=str(e)
                        )
                        raise
                    
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e)
                    )
                    
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            
            raise last_exception
        
        return wrapper
    return decorator
