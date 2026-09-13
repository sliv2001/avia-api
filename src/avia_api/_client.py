from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import TypeAdapter, ValidationError
from pyrate_limiter import Rate

from ._params import clean_params
from ._transport import build_transport
from ._utils import parse_retry_after
from .exceptions import (
    AviaApiAuthenticationError,
    AviaApiConnectionError,
    AviaApiHTTPStatusError,
    AviaApiRateLimitError,
    AviaApiResponseError,
    AviaApiServerError,
    AviaApiValidationError,
)
from .resources import DirectionsResource, PricesResource, ReferenceResource

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.travelpayouts.com"
TOKEN_ENV_VAR = "TRAVELPAYOUTS_TOKEN"

T = TypeVar("T")


class AviaApiClient:
    """Async client for the Travelpayouts / Aviasales Data API.

    Example:
        async with AviaApiClient(token="...") as client:
            prices = await client.prices.cheap(origin="MOW", destination="LED")

    Args:
        token: API token from the partner's Travelpayouts account. Falls
            back to the ``TRAVELPAYOUTS_TOKEN`` environment variable. Most
            endpoints work without one at a reduced quota, but reads always
            attach it when available.
        base_url: Overridable mainly for testing.
        timeout: Passed straight to ``httpx``.
        rate: A ``pyrate_limiter.Rate`` (or list of rates) capping outbound
            request throughput. Defaults to 5 requests/second.
        max_retries: Attempts for requests that fail with a connection error
            or a 429/5xx status, with exponential backoff (honoring
            ``Retry-After`` when present).
        cache_ttl: How long a successful GET response is reused for, in
            seconds. ``None`` disables the cache.
        cache_path: SQLite file backing the cache (relative paths land under
            ``.cache/hishel/``, matching hishel's own convention).
        transport: Escape hatch for tests or advanced setups - supplying this
            bypasses rate limiting/retries/caching entirely.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx.Timeout = 10.0,
        rate: Rate | list[Rate] | None = None,
        max_retries: int = 3,
        cache_ttl: float | None = 1800.0,
        cache_path: str | Path = "avia_api.db",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        token = token or os.environ.get(TOKEN_ENV_VAR)
        headers = {"X-Access-Token": token} if token else {}
        if transport is None:
            transport = build_transport(
                rate=rate,
                max_retries=max_retries,
                cache_ttl=cache_ttl,
                cache_path=cache_path,
            )
        self._http = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=timeout, transport=transport)

        self.prices = PricesResource(self)
        self.directions = DirectionsResource(self)
        self.reference = ReferenceResource(self)

    async def __aenter__(self) -> AviaApiClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get_json(self, path: str, *, params: dict[str, Any], adapter: TypeAdapter[T]) -> T:
        cleaned_params = clean_params(params)
        logger.debug("GET %s params=%r", path, cleaned_params)
        try:
            response = await self._http.get(path, params=cleaned_params)
        except httpx.TransportError as exc:
            logger.error("GET %s failed: %s", path, exc)
            raise AviaApiConnectionError(str(exc)) from exc

        self._raise_for_status(response)

        payload = response.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            logger.warning("GET %s returned success=false: %s", path, payload.get("error"))
            raise AviaApiResponseError(payload.get("error") or "Aviasales API returned an error", payload=payload)

        try:
            result = adapter.validate_python(payload)
        except ValidationError as exc:
            logger.error("GET %s response failed schema validation: %s", path, exc)
            raise AviaApiValidationError(str(exc)) from exc

        logger.debug("GET %s -> %d", path, response.status_code)
        return result

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code in (401, 403):
            logger.warning("%s -> %d (authentication error)", response.request.url, response.status_code)
            raise AviaApiAuthenticationError(response)
        if response.status_code == 429:
            retry_after = parse_retry_after(response.headers.get("retry-after"))
            logger.warning("%s -> 429 (rate limited); retry_after=%s", response.request.url, retry_after)
            raise AviaApiRateLimitError(response, retry_after=retry_after)
        if response.status_code >= 500:
            logger.error("%s -> %d (server error)", response.request.url, response.status_code)
            raise AviaApiServerError(response)
        logger.warning("%s -> %d", response.request.url, response.status_code)
        raise AviaApiHTTPStatusError(response)
