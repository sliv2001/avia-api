from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict

T = TypeVar("T")


def _empty_str_to_none(value: object) -> object:
    return None if value == "" else value


#: Several endpoints use ``""`` instead of omitting the field for a one-way
#: trip's missing return date/datetime.
OptionalDate = Annotated[date | None, BeforeValidator(_empty_str_to_none)]
OptionalDateTime = Annotated[datetime | None, BeforeValidator(_empty_str_to_none)]


class AviaBaseModel(BaseModel):
    """Base for all response models.

    ``extra="allow"`` means fields the API adds later show up on
    ``model_extra`` instead of raising, so a new, undocumented field never
    breaks parsing of the fields we do know about.
    """

    model_config = ConfigDict(extra="allow", frozen=True)


class Envelope(AviaBaseModel, Generic[T]):
    """The ``{"success", "data", "error"}`` shape shared by most v1/v2 endpoints."""

    success: bool
    data: T
    error: str | None = None
    currency: str | None = None
