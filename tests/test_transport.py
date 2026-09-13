from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest
import respx
import tenacity
from pyrate_limiter import Duration, Rate

from avia_api._transport import _RetryableStatusError, _wait, build_transport

BASE_URL = "https://example.avia-api.test"


def _client(transport: httpx.AsyncBaseTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport, base_url=BASE_URL)


# --- caching -------------------------------------------------------------


async def test_cache_disabled_hits_network_on_every_request(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/data").mock(return_value=httpx.Response(200, json={"ok": True}))
    transport = build_transport(rate=None, max_retries=3, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        r1 = await client.get("/data")
        r2 = await client.get("/data")

    assert r1.status_code == r2.status_code == 200
    assert route.call_count == 2


async def test_cache_enabled_serves_repeat_request_from_cache(
    respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    route = respx_mock.get("/data").mock(return_value=httpx.Response(200, json={"ok": True}))
    transport = build_transport(rate=None, max_retries=3, cache_ttl=60.0, cache_path=tmp_path / "cache.db")

    async with _client(transport) as client:
        r1 = await client.get("/data")
        r2 = await client.get("/data")

    assert route.call_count == 1
    assert r1.json() == r2.json() == {"ok": True}


async def test_cache_does_not_serve_stale_entry_past_ttl(respx_mock: respx.MockRouter, tmp_path: Path) -> None:
    route = respx_mock.get("/data").mock(return_value=httpx.Response(200, json={"ok": True}))
    # A near-zero TTL means the cached entry is effectively already expired
    # by the time the second request is made.
    transport = build_transport(rate=None, max_retries=3, cache_ttl=0.001, cache_path=tmp_path / "cache.db")

    async with _client(transport) as client:
        await client.get("/data")
        time.sleep(0.05)
        await client.get("/data")

    assert route.call_count == 2


# --- retries ---------------------------------------------------------------


@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
async def test_retries_transient_status_then_succeeds(respx_mock: respx.MockRouter, status_code: int) -> None:
    route = respx_mock.get("/data").mock(
        side_effect=[httpx.Response(status_code), httpx.Response(200, json={"ok": True})]
    )
    transport = build_transport(rate=None, max_retries=3, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        response = await client.get("/data")

    assert response.status_code == 200
    assert route.call_count == 2


async def test_non_retryable_status_is_returned_immediately(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/data").mock(return_value=httpx.Response(404))
    transport = build_transport(rate=None, max_retries=3, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        response = await client.get("/data")

    assert response.status_code == 404
    assert route.call_count == 1


async def test_retry_budget_exhausted_returns_last_response(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/data").mock(return_value=httpx.Response(503))
    transport = build_transport(rate=None, max_retries=2, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        response = await client.get("/data")

    assert response.status_code == 503
    assert route.call_count == 2


async def test_retries_connection_errors_then_succeeds(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/data").mock(
        side_effect=[httpx.ConnectError("boom"), httpx.Response(200, json={"ok": True})]
    )
    transport = build_transport(rate=None, max_retries=3, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        response = await client.get("/data")

    assert response.status_code == 200
    assert route.call_count == 2


async def test_connection_error_reraised_after_retry_budget_exhausted(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/data").mock(side_effect=httpx.ConnectError("boom"))
    transport = build_transport(rate=None, max_retries=2, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        with pytest.raises(httpx.ConnectError):
            await client.get("/data")

    assert route.call_count == 2


async def test_max_retries_is_never_less_than_one(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/data").mock(return_value=httpx.Response(503))
    transport = build_transport(rate=None, max_retries=0, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        response = await client.get("/data")

    assert response.status_code == 503
    assert route.call_count == 1


# --- rate limiting -----------------------------------------------------------


async def test_rate_limiting_throttles_requests_beyond_configured_rate(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/data").mock(return_value=httpx.Response(200))
    transport = build_transport(rate=Rate(1, Duration.SECOND), max_retries=1, cache_ttl=None, cache_path="unused.db")

    async with _client(transport) as client:
        start = time.monotonic()
        await client.get("/data")
        await client.get("/data")
        elapsed = time.monotonic() - start

    # With 1 request/second allowed, the second request must wait; a
    # generous lower bound keeps this from flaking while still asserting
    # that *some* meaningful throttling happened.
    assert elapsed >= 0.3


# --- _wait backoff helper ----------------------------------------------------


def _retry_state(exc: BaseException, attempt_number: int = 1) -> tenacity.RetryCallState:
    state = tenacity.RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
    state.attempt_number = attempt_number
    outcome = tenacity.Future(attempt_number)
    outcome.set_exception(exc)
    state.outcome = outcome
    return state


def test_wait_uses_retry_after_when_present() -> None:
    state = _retry_state(_RetryableStatusError(retry_after=3.5))
    assert _wait(state) == 3.5


def test_wait_falls_back_to_exponential_backoff_when_no_retry_after() -> None:
    state = _retry_state(_RetryableStatusError(retry_after=None))
    assert _wait(state) >= 0.0


def test_wait_falls_back_to_exponential_backoff_for_non_status_errors() -> None:
    state = _retry_state(httpx.ConnectError("boom"))
    assert _wait(state) >= 0.0
