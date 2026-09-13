from __future__ import annotations

from pydantic import TypeAdapter

from .._params import clean_params
from ..models.common import Envelope
from ..models.prices import (
    CalendarPrice,
    LatestPriceEntry,
    MatrixPriceEntry,
    MonthlyPrice,
    NearestPlacesMatrixResponse,
    SimplePrice,
)
from ._base import BaseResource

_CHEAP_ADAPTER = TypeAdapter(Envelope[dict[str, dict[str, SimplePrice]]])
_CALENDAR_ADAPTER = TypeAdapter(Envelope[dict[str, CalendarPrice]])
_MONTHLY_ADAPTER = TypeAdapter(Envelope[dict[str, MonthlyPrice]])
_LATEST_ADAPTER = TypeAdapter(Envelope[list[LatestPriceEntry]])
_MATRIX_ADAPTER = TypeAdapter(Envelope[list[MatrixPriceEntry]])
_NEAREST_PLACES_ADAPTER = TypeAdapter(NearestPlacesMatrixResponse)


class PricesResource(BaseResource):
    """Cached ticket prices: ``/v1/prices/*`` and ``/v2/prices/*``.

    Date-like parameters are plain strings - the API accepts either
    ``"YYYY-MM-DD"`` or, on some endpoints, a month-only ``"YYYY-MM"``, and
    :class:`datetime.date` can't represent the latter, so the choice of
    format is left to the caller instead of guessing at a conversion.
    """

    async def cheap(
        self,
        origin: str,
        destination: str,
        *,
        depart_date: str | None = None,
        return_date: str | None = None,
        currency: str | None = None,
        page: int | None = None,
    ) -> dict[str, dict[str, SimplePrice]]:
        """The cheapest tickets found for each destination, grouped by index.

        ``GET /v1/prices/cheap``. ``depart_date``/``return_date``: ``"YYYY-MM"`` or ``"YYYY-MM-DD"``.
        """
        params = clean_params(
            dict(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                return_date=return_date,
                currency=currency,
                page=page,
            )
        )
        envelope = await self._get("/v1/prices/cheap", params, _CHEAP_ADAPTER)
        return envelope.data

    async def direct(
        self,
        origin: str,
        destination: str,
        *,
        depart_date: str | None = None,
        return_date: str | None = None,
        currency: str | None = None,
        page: int | None = None,
    ) -> dict[str, dict[str, SimplePrice]]:
        """The cheapest non-stop tickets found for each destination.

        ``GET /v1/prices/direct``. ``depart_date``/``return_date``: ``"YYYY-MM"`` or ``"YYYY-MM-DD"``.
        """
        params = clean_params(
            dict(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                return_date=return_date,
                currency=currency,
                page=page,
            )
        )
        envelope = await self._get("/v1/prices/direct", params, _CHEAP_ADAPTER)
        return envelope.data

    async def calendar(
        self,
        origin: str,
        destination: str,
        depart_date: str,
        *,
        calendar_type: str = "departure_date",
        return_date: str | None = None,
        length: int | None = None,
        currency: str | None = None,
    ) -> dict[str, CalendarPrice]:
        """The cheapest ticket for each day of the month around ``depart_date``.

        ``GET /v1/prices/calendar``. ``depart_date``/``return_date``: ``"YYYY-MM"`` or ``"YYYY-MM-DD"``.
        """
        params = clean_params(
            dict(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                calendar_type=calendar_type,
                return_date=return_date,
                length=length,
                currency=currency,
            )
        )
        envelope = await self._get("/v1/prices/calendar", params, _CALENDAR_ADAPTER)
        return envelope.data

    async def monthly(
        self,
        origin: str,
        destination: str,
        *,
        currency: str | None = None,
    ) -> dict[str, MonthlyPrice]:
        """The cheapest ticket for each of the next several months.

        ``GET /v1/prices/monthly``
        """
        params = clean_params(dict(origin=origin, destination=destination, currency=currency))
        envelope = await self._get("/v1/prices/monthly", params, _MONTHLY_ADAPTER)
        return envelope.data

    async def latest(
        self,
        *,
        currency: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        beginning_of_period: str | None = None,
        period_type: str | None = None,
        one_way: bool | None = None,
        page: int | None = None,
        limit: int | None = None,
        show_to_affiliates: bool | None = None,
        sorting: str | None = None,
    ) -> list[LatestPriceEntry]:
        """The most recently found prices across all of Aviasales' search history.

        ``GET /v2/prices/latest``. ``beginning_of_period``: ``"YYYY-MM-DD"``.
        """
        params = clean_params(
            dict(
                currency=currency,
                origin=origin,
                destination=destination,
                beginning_of_period=beginning_of_period,
                period_type=period_type,
                one_way=one_way,
                page=page,
                limit=limit,
                show_to_affiliates=show_to_affiliates,
                sorting=sorting,
            )
        )
        envelope = await self._get("/v2/prices/latest", params, _LATEST_ADAPTER)
        return envelope.data

    async def month_matrix(
        self,
        origin: str,
        destination: str,
        *,
        currency: str | None = None,
        month: str | None = None,
        show_to_affiliates: bool | None = None,
    ) -> list[MatrixPriceEntry]:
        """A price calendar for every day of one month.

        ``GET /v2/prices/month-matrix``. ``month``: ``"YYYY-MM-DD"``.
        """
        params = clean_params(
            dict(
                origin=origin,
                destination=destination,
                currency=currency,
                month=month,
                show_to_affiliates=show_to_affiliates,
            )
        )
        envelope = await self._get("/v2/prices/month-matrix", params, _MATRIX_ADAPTER)
        return envelope.data

    async def week_matrix(
        self,
        origin: str,
        destination: str,
        *,
        currency: str | None = None,
        depart_date: str | None = None,
        return_date: str | None = None,
        show_to_affiliates: bool | None = None,
    ) -> list[MatrixPriceEntry]:
        """A price calendar for the week around ``depart_date``.

        ``GET /v2/prices/week-matrix``. ``depart_date``/``return_date``: ``"YYYY-MM"`` or ``"YYYY-MM-DD"``.
        """
        params = clean_params(
            dict(
                origin=origin,
                destination=destination,
                currency=currency,
                depart_date=depart_date,
                return_date=return_date,
                show_to_affiliates=show_to_affiliates,
            )
        )
        envelope = await self._get("/v2/prices/week-matrix", params, _MATRIX_ADAPTER)
        return envelope.data

    async def nearest_places_matrix(
        self,
        origin: str,
        destination: str,
        *,
        currency: str | None = None,
        limit: int | None = None,
        show_to_affiliates: bool | None = None,
        depart_date: str | None = None,
        return_date: str | None = None,
        flexibility: int | None = None,
        distance: int | None = None,
    ) -> NearestPlacesMatrixResponse:
        """Prices for nearby origin/destination airports, when the exact route is expensive.

        ``GET /v2/prices/nearest-places-matrix``. ``depart_date``/``return_date``: ``"YYYY-MM"`` or ``"YYYY-MM-DD"``.
        """
        params = clean_params(
            dict(
                origin=origin,
                destination=destination,
                currency=currency,
                limit=limit,
                show_to_affiliates=show_to_affiliates,
                depart_date=depart_date,
                return_date=return_date,
                flexibility=flexibility,
                distance=distance,
            )
        )
        return await self._get("/v2/prices/nearest-places-matrix", params, _NEAREST_PLACES_ADAPTER)
