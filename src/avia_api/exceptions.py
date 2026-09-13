from __future__ import annotations

from typing import Any

import httpx


class AviaApiError(Exception):
    """Base class for every error raised by this library."""


class AviaApiConnectionError(AviaApiError):
    """The request could not be sent, or no response was received.

    Raised after the underlying network error survived all retry attempts.
    """


class AviaApiHTTPStatusError(AviaApiError):
    """The server responded with an HTTP error status.

    This is only raised for statuses that are not retried automatically
    (or that survived every retry attempt).
    """

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        super().__init__(f"{response.status_code} {response.reason_phrase} for url {response.request.url}")


class AviaApiAuthenticationError(AviaApiHTTPStatusError):
    """Raised on HTTP 401/403 - the API token is missing or invalid."""


class AviaApiRateLimitError(AviaApiHTTPStatusError):
    """Raised on HTTP 429 after the retry budget was exhausted."""

    def __init__(self, response: httpx.Response, *, retry_after: float | None) -> None:
        super().__init__(response)
        self.retry_after = retry_after


class AviaApiServerError(AviaApiHTTPStatusError):
    """Raised on HTTP 5xx after the retry budget was exhausted."""


class AviaApiResponseError(AviaApiError):
    """The API responded with HTTP 200 but ``{"success": false}`` in the body."""

    def __init__(self, message: str, *, payload: Any = None) -> None:
        super().__init__(message)
        self.payload = payload


class AviaApiValidationError(AviaApiError):
    """The response body did not match the expected schema.

    This usually means the API changed shape; it is kept distinct from
    transport-level errors so callers can tell "we got a bad response" apart
    from "we couldn't reach the server".
    """
