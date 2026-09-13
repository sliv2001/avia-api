from __future__ import annotations

import typing as t

from pydantic import TypeAdapter

if t.TYPE_CHECKING:
    from .._client import AviaApiClient

T = t.TypeVar("T")


class BaseResource:
    def __init__(self, client: "AviaApiClient") -> None:
        self._client = client

    async def _get(self, path: str, params: dict[str, t.Any], adapter: TypeAdapter[T]) -> T:
        return await self._client._get_json(path, params=params, adapter=adapter)
