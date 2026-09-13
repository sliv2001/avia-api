from __future__ import annotations

from pydantic import TypeAdapter

from ..models.reference import Airline, AirlineAlliance, Airport, City, Country, Plane, Route
from ._base import BaseResource

_COUNTRIES_ADAPTER = TypeAdapter(list[Country])
_CITIES_ADAPTER = TypeAdapter(list[City])
_AIRPORTS_ADAPTER = TypeAdapter(list[Airport])
_AIRLINES_ADAPTER = TypeAdapter(list[Airline])
_ALLIANCES_ADAPTER = TypeAdapter(list[AirlineAlliance])
_PLANES_ADAPTER = TypeAdapter(list[Plane])
_ROUTES_ADAPTER = TypeAdapter(list[Route])


class ReferenceResource(BaseResource):
    """Static reference data: ``/data/*.json``.

    These are plain, unauthenticated JSON files that change rarely, so they
    benefit the most from the client's response cache.
    """

    async def countries(self, *, language: str = "en") -> list[Country]:
        """``GET /data/{language}/countries.json``"""
        return await self._get(f"/data/{language}/countries.json", {}, _COUNTRIES_ADAPTER)

    async def cities(self, *, language: str = "en") -> list[City]:
        """``GET /data/{language}/cities.json``"""
        return await self._get(f"/data/{language}/cities.json", {}, _CITIES_ADAPTER)

    async def airports(self, *, language: str = "en") -> list[Airport]:
        """``GET /data/{language}/airports.json``"""
        return await self._get(f"/data/{language}/airports.json", {}, _AIRPORTS_ADAPTER)

    async def airlines(self, *, language: str = "en") -> list[Airline]:
        """``GET /data/{language}/airlines.json``"""
        return await self._get(f"/data/{language}/airlines.json", {}, _AIRLINES_ADAPTER)

    async def airline_alliances(self, *, language: str = "en") -> list[AirlineAlliance]:
        """``GET /data/{language}/airlines_alliances.json``"""
        return await self._get(f"/data/{language}/airlines_alliances.json", {}, _ALLIANCES_ADAPTER)

    async def planes(self) -> list[Plane]:
        """``GET /data/planes.json``"""
        return await self._get("/data/planes.json", {}, _PLANES_ADAPTER)

    async def routes(self) -> list[Route]:
        """``GET /data/routes.json``"""
        return await self._get("/data/routes.json", {}, _ROUTES_ADAPTER)
