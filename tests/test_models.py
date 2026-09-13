from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from avia_api.models.common import AviaBaseModel, Envelope, OptionalDate, OptionalDateTime
from avia_api.models.prices import NearestPlacesMatrixResponse, SimplePrice
from avia_api.models.reference import Airline, City, Coordinates


class _OptionalDateHolder(AviaBaseModel):
    value: OptionalDate = None


class _OptionalDateTimeHolder(AviaBaseModel):
    value: OptionalDateTime = None


def test_optional_date_empty_string_becomes_none() -> None:
    holder = _OptionalDateHolder.model_validate({"value": ""})
    assert holder.value is None


def test_optional_date_parses_iso_date() -> None:
    holder = _OptionalDateHolder.model_validate({"value": "2024-05-01"})
    assert holder.value == date(2024, 5, 1)


def test_optional_date_none_stays_none() -> None:
    holder = _OptionalDateHolder.model_validate({"value": None})
    assert holder.value is None


def test_optional_datetime_empty_string_becomes_none() -> None:
    holder = _OptionalDateTimeHolder.model_validate({"value": ""})
    assert holder.value is None


def test_optional_datetime_parses_iso_datetime() -> None:
    holder = _OptionalDateTimeHolder.model_validate({"value": "2024-05-01T10:30:00"})
    assert holder.value == datetime(2024, 5, 1, 10, 30, 0)


def test_avia_base_model_allows_extra_fields() -> None:
    holder = _OptionalDateHolder.model_validate({"value": "2024-01-01", "unknown_future_field": 42})
    assert holder.model_extra == {"unknown_future_field": 42}


def test_avia_base_model_is_frozen() -> None:
    holder = _OptionalDateHolder.model_validate({"value": "2024-01-01"})
    with pytest.raises(ValidationError):
        holder.value = None  # type: ignore[misc]


def test_envelope_generic_parses_typed_data() -> None:
    adapter = TypeAdapter(Envelope[dict[str, int]])
    envelope = adapter.validate_python({"success": True, "data": {"MOW": 100}, "error": None, "currency": "usd"})
    assert envelope.success is True
    assert envelope.data == {"MOW": 100}
    assert envelope.currency == "usd"


def test_envelope_error_and_currency_default_to_none() -> None:
    adapter = TypeAdapter(Envelope[dict[str, int]])
    envelope = adapter.validate_python({"success": True, "data": {}})
    assert envelope.error is None
    assert envelope.currency is None


def test_nearest_places_matrix_response_defaults_when_fields_missing() -> None:
    response = NearestPlacesMatrixResponse.model_validate({})
    assert response.prices == []
    assert response.origins == []
    assert response.destinations == []
    assert response.errors == {}


def test_simple_price_parses_expected_fields_and_optional_return_at() -> None:
    price = SimplePrice.model_validate(
        {
            "price": 5000,
            "airline": "SU",
            "flight_number": 123,
            "departure_at": "2024-05-01T10:00:00Z",
            "return_at": "",
            "expires_at": "2024-05-01T12:00:00Z",
        }
    )
    assert price.price == 5000
    assert price.return_at is None


def test_city_parses_nested_coordinates_and_defaults() -> None:
    city = City.model_validate({"code": "MOW", "name": "Moscow", "coordinates": {"lon": 37.6, "lat": 55.7}})
    assert isinstance(city.coordinates, Coordinates)
    assert city.coordinates.lat == 55.7
    assert city.name_translations == {}
    assert city.country_code is None


def test_airline_defaults_is_active_true() -> None:
    airline = Airline.model_validate({"name": "Aeroflot"})
    assert airline.is_active is True
    assert airline.iata is None
