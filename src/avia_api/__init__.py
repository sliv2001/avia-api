"""Async Python client for the Travelpayouts / Aviasales Data API."""

import logging

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

# Libraries should never configure handlers themselves - this only silences
# the "No handlers could be found" warning until the application attaches
# its own. See https://docs.python.org/3/howto/logging.html#library-config
logging.getLogger(__name__).addHandler(logging.NullHandler())

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
