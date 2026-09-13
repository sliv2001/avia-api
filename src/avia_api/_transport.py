from __future__ import annotations

from pathlib import Path
from typing import Union

import hishel
import httpx
import tenacity
from hishel.httpx import AsyncCacheTransport
from pyrate_limiter import Duration, Limiter, Rate

from ._utils import parse_retry_after

#: Conservative default: Travelpayouts does not publish a single documented
#: number for the Data API, so this stays well under the limits mentioned for
#: other methods rather than assume the account's actual quota.
DEFAULT_RATE = Rate(5, Duration.SECOND)

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_EXPONENTIAL_WAIT = tenacity.wait_exponential_jitter(initial=0.5, max=8.0)


class _RetryableStatusError(Exception):
    """Internal signal: the response's status code should trigger a retry."""

    def __init__(self, retry_after: float | None) -> None:
        self.retry_after = retry_after


def _wait(retry_state: tenacity.RetryCallState) -> float:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, _RetryableStatusError) and exc.retry_after is not None:
        return exc.retry_after
    return _EXPONENTIAL_WAIT(retry_state)


class _ResilientTransport(httpx.AsyncBaseTransport):
    """Applies client-side rate limiting and retries transient failures.

    Sits directly on top of the network transport, underneath the cache
    transport, so cache hits never touch the limiter or the retry loop.
    """

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport,
        *,
        rate: Union[Rate, list[Rate]],
        max_retries: int,
    ) -> None:
        self._transport = transport
        self._limiter = Limiter(rate)
        self._retrying = tenacity.AsyncRetrying(
            stop=tenacity.stop_after_attempt(max(max_retries, 1)),
            wait=_wait,
            retry=tenacity.retry_if_exception_type((httpx.TransportError, _RetryableStatusError)),
            reraise=True,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response: httpx.Response
        try:
            async for attempt in self._retrying:
                with attempt:
                    await self._limiter.try_acquire_async("avia-api")
                    response = await self._transport.handle_async_request(request)
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        # Read the body before closing so the caller can still
                        # inspect status/headers/content once retries run out.
                        await response.aread()
                        retry_after = parse_retry_after(response.headers.get("retry-after"))
                        await response.aclose()
                        raise _RetryableStatusError(retry_after)
        except _RetryableStatusError:
            # Retry budget exhausted on a bad status: hand the last response
            # back to the caller instead of leaking this internal signal.
            return response
        return response

    async def aclose(self) -> None:
        await self._transport.aclose()


def build_transport(
    *,
    rate: Union[Rate, list[Rate], None],
    max_retries: int,
    cache_ttl: float | None,
    cache_path: Union[str, Path],
) -> httpx.AsyncBaseTransport:
    """Build the layered transport: cache -> rate limit/retry -> network.

    ``cache_ttl=None`` disables caching entirely, leaving just the resilient
    transport in place.
    """
    network = httpx.AsyncHTTPTransport(retries=0)
    resilient: httpx.AsyncBaseTransport = _ResilientTransport(
        network, rate=rate or DEFAULT_RATE, max_retries=max_retries
    )
    if cache_ttl is None:
        return resilient

    # Travelpayouts responses carry no Cache-Control/ETag headers, so a
    # spec-compliant (RFC 9111) cache policy would never store anything.
    # FilterPolicy with no filters caches every response unconditionally,
    # and the storage's own default_ttl governs expiry instead.
    storage = hishel.AsyncSqliteStorage(database_path=cache_path, default_ttl=cache_ttl)
    return AsyncCacheTransport(next_transport=resilient, storage=storage, policy=hishel.FilterPolicy())
