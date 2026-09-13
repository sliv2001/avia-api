from __future__ import annotations

from datetime import datetime

from .common import AviaBaseModel, OptionalDateTime


class CityDirectionPrice(AviaBaseModel):
    """An entry from ``/v1/city-directions``.
    """

    origin: str
    destination: str
    price: int
    transfers: int
    airline: str
    flight_number: int
    departure_at: datetime
    return_at: OptionalDateTime = None
    expires_at: datetime
