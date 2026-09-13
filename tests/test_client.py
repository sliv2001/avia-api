from __future__ import annotations

import logging
from collections.abc import Callable
from unittest.mock import MagicMock

import httpx
import pytest
from pyrate_limiter import Duration, Rate

from avia_api import (
    AviaApiAuthenticationError,
    AviaApiClient,
    AviaApiConnectionError,
    AviaApiHTTPStatusError,
    AviaApiRateLimitError,
    AviaApiResponseError,
    AviaApiServerError,
    AviaApiValidationError,
)
from avia_api._client import TOKEN_ENV_VAR

from .helpers import envelope, json_response

LOGGER_NAME = "avia_api._client"

# --- token / header handling -------------------------------------------------


def test_token_param_sets_access_token_header() -> None:
    client = AviaApiClient(token="abc123", transport=httpx.MockTransport(lambda r: json_response({})))
    assert client._http.headers.get("x-access-token") == "abc123"


def test_token_from_env_var_when_no_param(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
    client = AviaApiClient(transport=httpx.MockTransport(lambda r: json_response({})))
    assert client._http.headers.get("x-access-token") == "env-token"


def test_explicit_token_overrides_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
    client = AviaApiClient(token="explicit", transport=httpx.MockTransport(lambda r: json_response({})))
    assert client._http.headers.get("x-access-token") == "explicit"


def test_no_token_means_no_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    client = AviaApiClient(transport=httpx.MockTransport(lambda r: json_response({})))
    assert "x-access-token" not in client._http.headers


# --- construction / transport wiring -----------------------------------------


def test_custom_transport_bypasses_build_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = MagicMock()
    monkeypatch.setattr("avia_api._client.build_transport", spy)
    AviaApiClient(transport=httpx.MockTransport(lambda r: json_response({})))
    spy.assert_not_called()


def test_default_construction_calls_build_transport_with_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = MagicMock(return_value=httpx.MockTransport(lambda r: json_response({})))
    monkeypatch.setattr("avia_api._client.build_transport", spy)
    rate = Rate(7, Duration.SECOND)
    AviaApiClient(rate=rate, max_retries=2, cache_ttl=42.0, cache_path="somewhere.db")
    spy.assert_called_once_with(rate=rate, max_retries=2, cache_ttl=42.0, cache_path="somewhere.db")


# --- lifecycle ----------------------------------------------------------------


async def test_context_manager_closes_underlying_http_client() -> None:
    async with AviaApiClient(transport=httpx.MockTransport(lambda r: json_response({}))) as client:
        assert not client._http.is_closed
    assert client._http.is_closed


async def test_aclose_closes_underlying_http_client() -> None:
    client = AviaApiClient(transport=httpx.MockTransport(lambda r: json_response({})))
    await client.aclose()
    assert client._http.is_closed


# --- _get_json / error mapping, exercised through a resource method ----------


async def test_get_json_returns_validated_data(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope(
        {
            "0": {
                "1": {
                    "price": 1000,
                    "airline": "SU",
                    "flight_number": 100,
                    "departure_at": "2024-05-01T10:00:00Z",
                    "expires_at": "2024-05-01T12:00:00Z",
                }
            }
        }
    )
    client = client_factory(lambda r: json_response(body))
    result = await client.prices.cheap("MOW", "LED")
    assert result["0"]["1"].price == 1000
    assert result["0"]["1"].airline == "SU"


async def test_get_json_raises_response_error_when_success_is_false(
    client_factory: Callable[..., AviaApiClient],
) -> None:
    body = envelope({}, success=False, error="invalid origin")
    client = client_factory(lambda r: json_response(body))
    with pytest.raises(AviaApiResponseError) as exc_info:
        await client.prices.cheap("XXX", "LED")
    assert "invalid origin" in str(exc_info.value)
    assert exc_info.value.payload == body


async def test_get_json_raises_validation_error_on_schema_mismatch(
    client_factory: Callable[..., AviaApiClient],
) -> None:
    # `data` here is a list, but the cheap-prices adapter expects a mapping.
    body = envelope([1, 2, 3])
    client = client_factory(lambda r: json_response(body))
    with pytest.raises(AviaApiValidationError):
        await client.prices.cheap("MOW", "LED")


async def test_get_json_raises_connection_error_on_transport_failure(
    client_factory: Callable[..., AviaApiClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = client_factory(handler)
    with pytest.raises(AviaApiConnectionError):
        await client.prices.cheap("MOW", "LED")


@pytest.mark.parametrize(
    "status_code,expected_exc",
    [
        (401, AviaApiAuthenticationError),
        (403, AviaApiAuthenticationError),
        (429, AviaApiRateLimitError),
        (500, AviaApiServerError),
        (502, AviaApiServerError),
        (418, AviaApiHTTPStatusError),
    ],
)
async def test_status_codes_map_to_expected_exceptions(
    client_factory: Callable[..., AviaApiClient],
    status_code: int,
    expected_exc: type[Exception],
) -> None:
    client = client_factory(lambda r: httpx.Response(status_code))
    with pytest.raises(expected_exc) as exc_info:
        await client.reference.planes()
    assert exc_info.value.status_code == status_code


async def test_rate_limit_error_parses_retry_after_header(client_factory: Callable[..., AviaApiClient]) -> None:
    client = client_factory(lambda r: httpx.Response(429, headers={"Retry-After": "5"}))
    with pytest.raises(AviaApiRateLimitError) as exc_info:
        await client.reference.planes()
    assert exc_info.value.retry_after == 5.0


async def test_success_below_400_does_not_raise(client_factory: Callable[..., AviaApiClient]) -> None:
    client = client_factory(lambda r: json_response([]))
    assert await client.reference.planes() == []


async def test_none_params_are_dropped_from_query(client_factory: Callable[..., AviaApiClient]) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return json_response(envelope({}))

    client = client_factory(handler)
    await client.prices.cheap("MOW", "LED", depart_date=None, currency="usd")
    assert "depart_date" not in captured
    assert captured["currency"] == "usd"
    assert captured["origin"] == "MOW"


# --- logging ------------------------------------------------------------------


async def test_request_debug_log_includes_path_and_params_but_not_token(
    client_factory: Callable[..., AviaApiClient], caplog: pytest.LogCaptureFixture
) -> None:
    client = client_factory(lambda r: json_response(envelope({})), token="super-secret-token")

    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        await client.prices.cheap("MOW", "LED")

    assert "/v1/prices/cheap" in caplog.text
    assert "MOW" in caplog.text
    assert "super-secret-token" not in caplog.text


async def test_successful_response_logs_debug_status(
    client_factory: Callable[..., AviaApiClient], caplog: pytest.LogCaptureFixture
) -> None:
    client = client_factory(lambda r: json_response([]))

    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        await client.reference.planes()

    assert "-> 200" in caplog.text


async def test_connection_error_logs_error(
    client_factory: Callable[..., AviaApiClient], caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = client_factory(handler)

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME), pytest.raises(AviaApiConnectionError):
        await client.prices.cheap("MOW", "LED")

    assert "failed" in caplog.text.lower()


async def test_response_error_logs_warning_with_api_error_message(
    client_factory: Callable[..., AviaApiClient], caplog: pytest.LogCaptureFixture
) -> None:
    client = client_factory(lambda r: json_response(envelope({}, success=False, error="invalid origin")))

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME), pytest.raises(AviaApiResponseError):
        await client.prices.cheap("XXX", "LED")

    assert "success=false" in caplog.text
    assert "invalid origin" in caplog.text


async def test_validation_error_logs_error(
    client_factory: Callable[..., AviaApiClient], caplog: pytest.LogCaptureFixture
) -> None:
    client = client_factory(lambda r: json_response(envelope([1, 2, 3])))

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME), pytest.raises(AviaApiValidationError):
        await client.prices.cheap("MOW", "LED")

    assert "schema validation" in caplog.text


@pytest.mark.parametrize(
    "status_code,expected_level,expected_text",
    [
        (401, logging.WARNING, "authentication error"),
        (429, logging.WARNING, "rate limited"),
        (500, logging.ERROR, "server error"),
        (418, logging.WARNING, "418"),
    ],
)
async def test_raise_for_status_logs_expected_level_and_text(
    client_factory: Callable[..., AviaApiClient],
    caplog: pytest.LogCaptureFixture,
    status_code: int,
    expected_level: int,
    expected_text: str,
) -> None:
    client = client_factory(lambda r: httpx.Response(status_code))

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME), pytest.raises(AviaApiHTTPStatusError):
        await client.reference.planes()

    matching = [r for r in caplog.records if r.levelno == expected_level]
    assert any(expected_text in r.getMessage() for r in matching)
