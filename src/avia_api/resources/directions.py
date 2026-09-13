from __future__ import annotations

from pydantic import TypeAdapter

from .._params import clean_params
from ..models.common import Envelope
from ..models.directions import CityDirectionPrice
from ._base import BaseResource

_AIRLINE_ADAPTER = TypeAdapter(Envelope[dict[str, int]])
_CITY_ADAPTER = TypeAdapter(Envelope[dict[str, CityDirectionPrice]])


class DirectionsResource(BaseResource):
    """Popular routes: ``/v1/airline-directions`` and ``/v1/city-directions``."""

    async def airline(
        self,
        airline_code: str,
        *,
        limit: int | None = None,
    ) -> dict[str, int]:
        """Popular routes for one airline, mapped to their cheapest price.

        ``GET /v1/airline-directions``
        """
        params = clean_params(dict(airline_code=airline_code, limit=limit))
        envelope = await self._get("/v1/airline-directions", params, _AIRLINE_ADAPTER)
        return envelope.data

    async def city(
        self,
        origin: str,
        *,
        currency: str | None = None,
    ) -> dict[str, CityDirectionPrice]:
        """Popular destinations from one city, with the cheapest ticket found.

        ``GET /v1/city-directions``
        """
        params = clean_params(dict(origin=origin, currency=currency))
        envelope = await self._get("/v1/city-directions", params, _CITY_ADAPTER)
        return envelope.data
