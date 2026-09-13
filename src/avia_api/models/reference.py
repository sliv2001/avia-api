from __future__ import annotations

from pydantic import Field

from .common import AviaBaseModel


class Coordinates(AviaBaseModel):
    lon: float
    lat: float


class Country(AviaBaseModel):
    code: str
    name: str
    currency: str | None = None
    name_translations: dict[str, str] = Field(default_factory=dict)


class City(AviaBaseModel):
    code: str
    name: str
    coordinates: Coordinates | None = None
    time_zone: str | None = None
    name_translations: dict[str, str] = Field(default_factory=dict)
    country_code: str | None = None


class Airport(AviaBaseModel):
    code: str
    name: str
    coordinates: Coordinates | None = None
    time_zone: str | None = None
    name_translations: dict[str, str] = Field(default_factory=dict)
    country_code: str | None = None
    city_code: str | None = None


class Airline(AviaBaseModel):
    name: str
    alias: str | None = None
    iata: str | None = None
    icao: str | None = None
    callsign: str | None = None
    country: str | None = None
    is_active: bool = True


class AirlineAlliance(AviaBaseModel):
    name: str
    airlines: list[str] = Field(default_factory=list)


class Plane(AviaBaseModel):
    code: str
    name: str


class Route(AviaBaseModel):
    airline_iata: str | None = None
    airline_icao: str | None = None
    departure_airport_iata: str | None = None
    departure_airport_icao: str | None = None
    arrival_airport_iata: str | None = None
    arrival_airport_icao: str | None = None
    codeshare: bool = False
    transfers: int = 0
    planes: list[str] = Field(default_factory=list)
