"""Bounded retry logic for transient failures (GAP-6 remediation).

Provides exponential backoff with jitter for HTTP 429, 502, 503, 504 errors
and connection failures. Never retries on success, client errors (4xx except 429),
or unrecoverable failures.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any, TypeVar

import httpx

from app.observability.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def retry_transient(
    func: Callable[[], Any],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    operation: str = "operation",
) -> T:
    """Retry a function on transient failures with exponential backoff.

    Args:
        func: Async function to retry (must be idempotent)
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 10.0)
        operation: Operation name for logging

    Returns:
        Result of successful function call

    Raises:
        Last exception if all attempts fail

    Retries on:
        - HTTP 429 (rate limit)
        - HTTP 502, 503, 504 (service unavailable)
        - httpx.ConnectError, httpx.ReadTimeout

    Does NOT retry:
        - HTTP 4xx (except 429) - client errors
        - HTTP 200-399 - success
        - httpx.InvalidURL, httpx.UnsupportedProtocol - configuration errors
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # Retry on rate limit and server errors
            if status in {429, 502, 503, 504}:
                last_exception = exc
                if attempt < max_attempts:
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
                    total_delay = delay + jitter
                    logger.warning(
                        "retry_transient_http_error",
                        operation=operation,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        status=status,
                        delay=round(total_delay, 2),
                    )
                    await asyncio.sleep(total_delay)
                    continue
            # Don't retry 4xx (except 429) or other status codes
            raise
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.PoolTimeout) as exc:
            last_exception = exc
            if attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter
                logger.warning(
                    "retry_transient_network_error",
                    operation=operation,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=type(exc).__name__,
                    delay=round(total_delay, 2),
                )
                await asyncio.sleep(total_delay)
                continue
            # All attempts exhausted
            break
        except (httpx.InvalidURL, httpx.UnsupportedProtocol):
            # Configuration errors - don't retry
            raise
        except Exception:
            # Unexpected error - don't retry
            raise

    # All retries exhausted
    logger.error(
        "retry_exhausted",
        operation=operation,
        attempts=max_attempts,
        error=str(last_exception),
    )
    raise last_exception  # type: ignore[misc]
