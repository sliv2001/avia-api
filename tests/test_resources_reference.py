from __future__ import annotations

from typing import Callable

import httpx
import pytest

from avia_api import AviaApiClient
from avia_api.models.reference import Airline, AirlineAlliance, Airport, City, Country, Plane, Route

from .helpers import json_response


def _path_capturing_client(client_factory: Callable[..., AviaApiClient], body) -> tuple[AviaApiClient, dict]:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return json_response(body)

    return client_factory(handler), captured


async def test_countries_default_language(client_factory: Callable[..., AviaApiClient]) -> None:
    body = [{"code": "RU", "name": "Russia", "currency": "rub"}]
    client, captured = _path_capturing_client(client_factory, body)

    result = await client.reference.countries()

    assert captured["path"] == "/data/en/countries.json"
    assert isinstance(result[0], Country)
    assert result[0].code == "RU"


async def test_countries_custom_language(client_factory: Callable[..., AviaApiClient]) -> None:
    client, captured = _path_capturing_client(client_factory, [])
    await client.reference.countries(language="ru")
    assert captured["path"] == "/data/ru/countries.json"


async def test_cities(client_factory: Callable[..., AviaApiClient]) -> None:
    body = [
        {
            "code": "MOW",
            "name": "Moscow",
            "coordinates": {"lon": 37.6, "lat": 55.7},
            "country_code": "RU",
        }
    ]
    client, captured = _path_capturing_client(client_factory, body)

    result = await client.reference.cities()

    assert captured["path"] == "/data/en/cities.json"
    assert isinstance(result[0], City)
    assert result[0].coordinates.lat == 55.7


async def test_airports(client_factory: Callable[..., AviaApiClient]) -> None:
    body = [{"code": "SVO", "name": "Sheremetyevo", "city_code": "MOW"}]
    client, captured = _path_capturing_client(client_factory, body)

    result = await client.reference.airports()

    assert captured["path"] == "/data/en/airports.json"
    assert isinstance(result[0], Airport)
    assert result[0].city_code == "MOW"


async def test_airlines(client_factory: Callable[..., AviaApiClient]) -> None:
    body = [{"name": "Aeroflot", "iata": "SU", "is_active": True}]
    client, captured = _path_capturing_client(client_factory, body)

    result = await client.reference.airlines()

    assert captured["path"] == "/data/en/airlines.json"
    assert isinstance(result[0], Airline)
    assert result[0].iata == "SU"


async def test_airline_alliances(client_factory: Callable[..., AviaApiClient]) -> None:
    body = [{"name": "SkyTeam", "airlines": ["SU", "AF"]}]
    client, captured = _path_capturing_client(client_factory, body)

    result = await client.reference.airline_alliances()

    assert captured["path"] == "/data/en/airlines_alliances.json"
    assert isinstance(result[0], AirlineAlliance)
    assert result[0].airlines == ["SU", "AF"]


async def test_planes_has_no_language_segment(client_factory: Callable[..., AviaApiClient]) -> None:
    body = [{"code": "733", "name": "Boeing 737-300"}]
    client, captured = _path_capturing_client(client_factory, body)

    result = await client.reference.planes()

    assert captured["path"] == "/data/planes.json"
    assert isinstance(result[0], Plane)


async def test_routes_has_no_language_segment(client_factory: Callable[..., AviaApiClient]) -> None:
    body = [{"airline_iata": "SU", "departure_airport_iata": "MOW", "arrival_airport_iata": "LED"}]
    client, captured = _path_capturing_client(client_factory, body)

    result = await client.reference.routes()

    assert captured["path"] == "/data/routes.json"
    assert isinstance(result[0], Route)
    assert result[0].transfers == 0
    assert result[0].codeshare is False
