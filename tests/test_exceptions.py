from __future__ import annotations

import httpx
import pytest

from avia_api.exceptions import (
    AviaApiAuthenticationError,
    AviaApiConnectionError,
    AviaApiError,
    AviaApiHTTPStatusError,
    AviaApiRateLimitError,
    AviaApiResponseError,
    AviaApiServerError,
    AviaApiValidationError,
)


def _response(status_code: int) -> httpx.Response:
    request = httpx.Request("GET", "https://api.travelpayouts.com/v1/prices/cheap")
    return httpx.Response(status_code, request=request)


@pytest.mark.parametrize(
    "exc_type",
    [
        AviaApiConnectionError,
        AviaApiHTTPStatusError,
        AviaApiAuthenticationError,
        AviaApiRateLimitError,
        AviaApiServerError,
        AviaApiResponseError,
        AviaApiValidationError,
    ],
)
def test_all_exceptions_derive_from_base_error(exc_type: type[Exception]) -> None:
    assert issubclass(exc_type, AviaApiError)


@pytest.mark.parametrize("exc_type", [AviaApiAuthenticationError, AviaApiRateLimitError, AviaApiServerError])
def test_status_subclasses_derive_from_http_status_error(exc_type: type[Exception]) -> None:
    assert issubclass(exc_type, AviaApiHTTPStatusError)


def test_http_status_error_message_and_attributes() -> None:
    response = _response(418)
    exc = AviaApiHTTPStatusError(response)
    assert exc.status_code == 418
    assert exc.response is response
    assert "418" in str(exc)
    assert "v1/prices/cheap" in str(exc)


def test_rate_limit_error_carries_retry_after() -> None:
    response = _response(429)
    exc = AviaApiRateLimitError(response, retry_after=12.5)
    assert exc.status_code == 429
    assert exc.retry_after == 12.5


def test_rate_limit_error_retry_after_can_be_none() -> None:
    exc = AviaApiRateLimitError(_response(429), retry_after=None)
    assert exc.retry_after is None


def test_response_error_carries_payload() -> None:
    payload = {"success": False, "error": "boom"}
    exc = AviaApiResponseError("boom", payload=payload)
    assert str(exc) == "boom"
    assert exc.payload is payload


def test_response_error_default_payload_is_none() -> None:
    exc = AviaApiResponseError("boom")
    assert exc.payload is None
