from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import AviaBaseModel, OptionalDate, OptionalDateTime


class SimplePrice(AviaBaseModel):
    """An entry from ``/v1/prices/cheap`` or ``/v1/prices/direct``."""

    price: int
    airline: str
    flight_number: int
    departure_at: datetime
    return_at: OptionalDateTime = None
    expires_at: datetime


class CalendarPrice(AviaBaseModel):
    """An entry from ``/v1/prices/calendar`` (and reused for city-directions)."""

    origin: str
    destination: str
    price: int
    transfers: int
    airline: str
    flight_number: int
    departure_at: datetime
    return_at: OptionalDateTime = None
    expires_at: datetime


class MonthlyPrice(CalendarPrice):
    """An entry from ``/v1/prices/monthly``. Same shape as :class:`CalendarPrice`."""


class LatestPriceEntry(AviaBaseModel):
    """An entry from ``/v2/prices/latest``."""

    show_to_affiliates: bool
    trip_class: int
    origin: str
    destination: str
    depart_date: OptionalDate = None
    return_date: OptionalDate = None
    number_of_changes: int
    value: float
    found_at: datetime
    distance: int | None = None
    actual: bool


class MatrixPriceEntry(LatestPriceEntry):
    """An entry from ``/v2/prices/month-matrix`` or ``/v2/prices/week-matrix``.

    Same shape as :class:`LatestPriceEntry`.
    """


class NearestPlacesMatrixPrice(AviaBaseModel):
    """A price entry from ``/v2/prices/nearest-places-matrix``."""

    value: float
    trip_class: int
    show_to_affiliates: bool
    origin: str
    destination: str
    depart_date: OptionalDate = None
    return_date: OptionalDate = None
    number_of_changes: int
    gate: str | None = None
    found_at: datetime
    duration: int | None = None
    distance: int | None = None
    actual: bool


class NearestPlacesMatrixResponse(AviaBaseModel):
    """The body of ``/v2/prices/nearest-places-matrix``.

    Unlike the other v1/v2 endpoints, this one is not wrapped in an
    ``Envelope`` - it has its own top-level shape.
    """

    prices: list[NearestPlacesMatrixPrice] = Field(default_factory=list)
    origins: list[str] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    errors: dict[str, object] = Field(default_factory=dict)
