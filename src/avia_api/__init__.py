"""Async Python client for the Travelpayouts / Aviasales Data API."""

from ._client import AviaApiClient
from .exceptions import (
    AviaApiAuthenticationError,
    AviaApiConnectionError,
    AviaApiError,
    AviaApiHTTPStatusError,
    AviaApiRateLimitError,
    AviaApiResponseError,
    AviaApiServerError,
    AviaApiValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "AviaApiClient",
    "AviaApiError",
    "AviaApiConnectionError",
    "AviaApiHTTPStatusError",
    "AviaApiAuthenticationError",
    "AviaApiRateLimitError",
    "AviaApiServerError",
    "AviaApiResponseError",
    "AviaApiValidationError",
]
