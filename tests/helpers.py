from __future__ import annotations

from typing import Any

import httpx


def json_response(
    payload: Any,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build an httpx.Response carrying a JSON body, for use in mock transports."""
    return httpx.Response(status_code, json=payload, headers=headers)


def envelope(data: Any, *, success: bool = True, error: str | None = None) -> dict[str, Any]:
    """Build a ``{"success", "data", "error"}`` envelope body as the API returns it."""
    return {"success": success, "data": data, "error": error}
