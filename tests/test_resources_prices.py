from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from avia_api import AviaApiClient
from avia_api.models.prices import (
    CalendarPrice,
    LatestPriceEntry,
    MatrixPriceEntry,
    MonthlyPrice,
    NearestPlacesMatrixResponse,
    SimplePrice,
)

from .helpers import envelope, json_response

SIMPLE_PRICE = {
    "price": 4500,
    "airline": "SU",
    "flight_number": 1234,
    "departure_at": "2024-06-01T08:00:00Z",
    "expires_at": "2024-06-01T20:00:00Z",
}

CALENDAR_PRICE = {**SIMPLE_PRICE, "origin": "MOW", "destination": "LED", "transfers": 0}

LATEST_ENTRY = {
    "show_to_affiliates": True,
    "trip_class": 0,
    "origin": "MOW",
    "destination": "LED",
    "depart_date": "2024-06-01",
    "return_date": "",
    "number_of_changes": 0,
    "value": 4500.0,
    "found_at": "2024-05-01T00:00:00Z",
    "actual": True,
}


def _capture_request(
    response: httpx.Response,
) -> tuple[Callable[[httpx.Request], httpx.Response], dict[str, Any]]:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        captured["method"] = request.method
        return response

    return handler, captured


async def test_cheap(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope({"LED": {"0": SIMPLE_PRICE}})
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.cheap("MOW", "LED", currency="usd", page=2)

    assert captured["method"] == "GET"
    assert captured["path"] == "/v1/prices/cheap"
    assert captured["params"] == {"origin": "MOW", "destination": "LED", "currency": "usd", "page": "2"}
    assert isinstance(result["LED"]["0"], SimplePrice)
    assert result["LED"]["0"].price == 4500


async def test_direct(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope({"LED": {"0": SIMPLE_PRICE}})
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.direct("MOW", "LED")

    assert captured["path"] == "/v1/prices/direct"
    assert isinstance(result["LED"]["0"], SimplePrice)


async def test_calendar_uses_default_calendar_type(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope({"2024-06-01": CALENDAR_PRICE})
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.calendar("MOW", "LED", "2024-06-01")

    assert captured["path"] == "/v1/prices/calendar"
    assert captured["params"]["calendar_type"] == "departure_date"
    assert isinstance(result["2024-06-01"], CalendarPrice)


async def test_calendar_allows_overriding_calendar_type(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope({})
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    await client.prices.calendar("MOW", "LED", "2024-06-01", calendar_type="return_date")

    assert captured["params"]["calendar_type"] == "return_date"


async def test_monthly(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope({"2024-06": CALENDAR_PRICE})
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.monthly("MOW", "LED")

    assert captured["path"] == "/v1/prices/monthly"
    assert isinstance(result["2024-06"], MonthlyPrice)


async def test_latest(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope([LATEST_ENTRY])
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.latest(origin="MOW", one_way=True, limit=10)

    assert captured["path"] == "/v2/prices/latest"
    assert captured["params"]["one_way"] == "true"
    assert captured["params"]["limit"] == "10"
    assert len(result) == 1
    entry = result[0]
    assert isinstance(entry, LatestPriceEntry)
    assert entry.return_date is None  # "" -> None via OptionalDate


async def test_month_matrix(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope([LATEST_ENTRY])
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.month_matrix("MOW", "LED", month="2024-06-01")

    assert captured["path"] == "/v2/prices/month-matrix"
    assert isinstance(result[0], MatrixPriceEntry)


async def test_week_matrix(client_factory: Callable[..., AviaApiClient]) -> None:
    body = envelope([LATEST_ENTRY])
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.week_matrix("MOW", "LED")

    assert captured["path"] == "/v2/prices/week-matrix"
    assert isinstance(result[0], MatrixPriceEntry)


async def test_nearest_places_matrix_is_not_envelope_wrapped(client_factory: Callable[..., AviaApiClient]) -> None:
    body = {
        "prices": [
            {
                "value": 4500.0,
                "trip_class": 0,
                "show_to_affiliates": True,
                "origin": "MOW",
                "destination": "LED",
                "number_of_changes": 0,
                "found_at": "2024-05-01T00:00:00Z",
                "actual": True,
            }
        ],
        "origins": ["MOW"],
        "destinations": ["LED"],
    }
    handler, captured = _capture_request(json_response(body))
    client = client_factory(handler)

    result = await client.prices.nearest_places_matrix("MOW", "LED", flexibility=2)

    assert captured["path"] == "/v2/prices/nearest-places-matrix"
    assert captured["params"]["flexibility"] == "2"
    assert isinstance(result, NearestPlacesMatrixResponse)
    assert result.origins == ["MOW"]
    assert result.errors == {}
