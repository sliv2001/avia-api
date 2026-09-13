from __future__ import annotations

from collections.abc import Callable

import httpx

from avia_api import AviaApiClient
from avia_api.models.directions import CityDirectionPrice

from .helpers import envelope, json_response


async def test_airline_directions(client_factory: Callable[..., AviaApiClient]) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return json_response(envelope({"LED": 3500}))

    client = client_factory(handler)
    result = await client.directions.airline("SU", limit=50)

    assert captured["path"] == "/v1/airline-directions"
    assert captured["params"] == {"airline_code": "SU", "limit": "50"}
    assert result == {"LED": 3500}


async def test_city_directions(client_factory: Callable[..., AviaApiClient]) -> None:
    entry = {
        "origin": "MOW",
        "destination": "LED",
        "price": 3500,
        "transfers": 0,
        "airline": "SU",
        "flight_number": 100,
        "departure_at": "2024-06-01T08:00:00Z",
        "expires_at": "2024-06-01T20:00:00Z",
    }
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return json_response(envelope({"LED": entry}))

    client = client_factory(handler)
    result = await client.directions.city("MOW", currency="rub")

    assert captured["path"] == "/v1/city-directions"
    assert captured["params"] == {"origin": "MOW", "currency": "rub"}
    assert isinstance(result["LED"], CityDirectionPrice)
    assert result["LED"].price == 3500
    assert result["LED"].return_at is None
