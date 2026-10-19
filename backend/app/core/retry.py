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
    max_total_time: float = 120.0,
    operation: str = "operation",
) -> T:
    """Retry a function on transient failures with exponential backoff.

    Args:
        func: Async function to retry (must be idempotent)
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 10.0)
        max_total_time: Maximum total retry time in seconds (default: 120.0)
        operation: Operation name for logging

    Returns:
        Result of successful function call

    Raises:
        Last exception if all attempts fail

    Retries on:
        - HTTP 429 (rate limit) - respects Retry-After header
        - HTTP 502, 503, 504 (service unavailable)
        - httpx.ConnectError, httpx.ReadTimeout

    Does NOT retry:
        - HTTP 4xx (except 429) - client errors
        - HTTP 200-399 - success
        - httpx.InvalidURL, httpx.UnsupportedProtocol - configuration errors
    """
    import time

    last_exception = None
    start_time = time.monotonic()

    for attempt in range(1, max_attempts + 1):
        # Check if we've exceeded total retry time budget
        elapsed = time.monotonic() - start_time
        if elapsed >= max_total_time:
            logger.warning(
                "retry_total_time_exceeded",
                operation=operation,
                elapsed_seconds=round(elapsed, 2),
                max_total_time=max_total_time,
            )
            break

        try:
            return await func()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # Retry on rate limit and server errors
            if status in {429, 502, 503, 504}:
                last_exception = exc
                if attempt < max_attempts:
                    # Phase 7.3B: Respect Retry-After header for rate limiting
                    if status == 429:
                        retry_after = _parse_retry_after(exc.response.headers.get("retry-after"))
                        if retry_after:
                            delay = min(retry_after, max_delay)
                            logger.warning(
                                "retry_transient_http_429",
                                operation=operation,
                                attempt=attempt,
                                max_attempts=max_attempts,
                                status=status,
                                delay=round(delay, 2),
                                retry_after_header=retry_after,
                            )
                            await asyncio.sleep(delay)
                            continue
                    
                    # Standard exponential backoff with jitter
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
        except asyncio.CancelledError:
            # Propagate cancellation immediately
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


def _parse_retry_after(header_value: str | None) -> float | None:
    """Parse Retry-After header value to seconds.
    
    Supports both delay-seconds (integer) and HTTP-date formats.
    Returns None if header is missing or invalid.
    """
    if not header_value:
        return None
    
    try:
        # Try parsing as integer seconds
        return float(header_value)
    except ValueError:
        # Try parsing as HTTP-date
        try:
            import time
            from email.utils import parsedate_to_datetime
            retry_date = parsedate_to_datetime(header_value)
            delta = (retry_date - parsedate_to_datetime(time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))).total_seconds()
            return max(0, delta)
        except Exception:  # noqa: BLE001
            return None
