"""
Retry-with-backoff decorator. For transient failures against the SAME provider.
"""

import time
from functools import wraps
from typing import Callable, TypeVar

from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator: retries the wrapped function on failure, with exponential backoff.

    Why exponential backoff instead of fixed-interval retry: retrying instantly
    in a loop can worsen rate-limiting by hammering an already-struggling API.
    Waiting progressively longer between attempts gives the service room to recover.

    Args:
        max_attempts: total attempts including the first (not just retries)
        base_delay_seconds: wait time before the 2nd attempt
        backoff_multiplier: how much the delay grows each retry (2.0 = doubles)
        retryable_exceptions: only these exception types trigger a retry;
            anything else propagates immediately (e.g. a bug shouldn't be retried)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = base_delay_seconds
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_multiplier

            raise last_exception  # unreachable in practice, satisfies type checkers

        return wrapper

    return decorator