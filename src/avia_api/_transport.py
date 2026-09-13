from __future__ import annotations

import logging
import time
from pathlib import Path

import hishel
import httpx
import tenacity
from hishel.httpx import AsyncCacheTransport
from pyrate_limiter import Duration, Limiter, Rate

from ._utils import parse_retry_after

logger = logging.getLogger(__name__)

#: Conservative default: Travelpayouts does not publish a single documented
#: number for the Data API, so this stays well under the limits mentioned for
#: other methods rather than assume the account's actual quota.
DEFAULT_RATE = Rate(5, Duration.SECOND)

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_EXPONENTIAL_WAIT = tenacity.wait_exponential_jitter(initial=0.5, max=8.0)

#: Only logged when the rate limiter actually delayed a request by more than
#: this many seconds - avoids a debug line on every single request.
_RATE_LIMIT_LOG_THRESHOLD = 0.01


class _RetryableStatusError(Exception):
    """Internal signal: the response's status code should trigger a retry."""

    def __init__(self, retry_after: float | None, *, status_code: int | None = None) -> None:
        self.retry_after = retry_after
        self.status_code = status_code


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
        rate: Rate | list[Rate],
        max_retries: int,
    ) -> None:
        self._transport = transport
        self._limiter = Limiter(rate)
        self._max_retries = max(max_retries, 1)

    def _before_sleep(self, request: httpx.Request, retry_state: tenacity.RetryCallState) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        wait = retry_state.next_action.sleep if retry_state.next_action else 0.0
        reason = f"HTTP {exc.status_code}" if isinstance(exc, _RetryableStatusError) else repr(exc)
        logger.warning(
            "%s %s failed on attempt %d/%d (%s); retrying in %.2fs",
            request.method,
            request.url,
            retry_state.attempt_number,
            self._max_retries,
            reason,
            wait,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response: httpx.Response
        retrying = tenacity.AsyncRetrying(
            stop=tenacity.stop_after_attempt(self._max_retries),
            wait=_wait,
            retry=tenacity.retry_if_exception_type((httpx.TransportError, _RetryableStatusError)),
            reraise=True,
            before_sleep=lambda retry_state: self._before_sleep(request, retry_state),
        )
        try:
            async for attempt in retrying:
                with attempt:
                    start = time.monotonic()
                    await self._limiter.try_acquire_async("avia-api")
                    delay = time.monotonic() - start
                    if delay > _RATE_LIMIT_LOG_THRESHOLD:
                        logger.debug("Rate limiter delayed %s %s by %.3fs", request.method, request.url, delay)
                    response = await self._transport.handle_async_request(request)
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        # Read the body before closing so the caller can still
                        # inspect status/headers/content once retries run out.
                        await response.aread()
                        retry_after = parse_retry_after(response.headers.get("retry-after"))
                        await response.aclose()
                        raise _RetryableStatusError(retry_after, status_code=response.status_code)
        except _RetryableStatusError as exc:
            # Retry budget exhausted on a bad status: hand the last response
            # back to the caller instead of leaking this internal signal.
            logger.warning(
                "%s %s exhausted retry budget (%d attempt(s)); giving up with status %d",
                request.method,
                request.url,
                self._max_retries,
                exc.status_code,
            )
            return response
        except httpx.TransportError:
            logger.warning(
                "%s %s exhausted retry budget (%d attempt(s)); giving up",
                request.method,
                request.url,
                self._max_retries,
            )
            raise
        logger.debug("%s %s -> %d", request.method, request.url, response.status_code)
        return response

    async def aclose(self) -> None:
        await self._transport.aclose()


def build_transport(
    *,
    rate: Rate | list[Rate] | None,
    max_retries: int,
    cache_ttl: float | None,
    cache_path: str | Path,
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
