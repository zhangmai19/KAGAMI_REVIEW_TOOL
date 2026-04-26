"""Retry utilities for API calls."""

from typing import Any, Callable, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


DEFAULT_RETRY_CONFIG = {
    "wait": wait_exponential(min=2, max=30),
    "stop": stop_after_attempt(5),
    "retry": retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    "reraise": True,
}


def fetch_with_retry(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 30,
    max_attempts: int = 5,
) -> dict:
    """Fetch a URL with retry and exponential backoff."""

    @retry(
        wait=wait_exponential(min=2, max=30),
        stop=stop_after_attempt(max_attempts),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        reraise=True,
    )
    def _fetch() -> dict:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    return _fetch()
