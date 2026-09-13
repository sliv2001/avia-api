from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from avia_api import AviaApiClient


def _make_client(handler: Callable[[httpx.Request], httpx.Response], **client_kwargs: Any) -> AviaApiClient:
    """Build an AviaApiClient backed by ``httpx.MockTransport(handler)``.

    Per the client's own docstring, supplying ``transport=`` bypasses rate
    limiting/retries/caching entirely, which keeps resource/client tests
    fast and deterministic.
    """
    return AviaApiClient(transport=httpx.MockTransport(handler), **client_kwargs)


@pytest.fixture
def client_factory() -> Callable[..., AviaApiClient]:
    return _make_client
