from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def clean_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values for use as query params.

    httpx serializes booleans as ``true``/``false`` on its own, but it has no
    special handling for ``None`` - it would be sent as an empty string
    otherwise - so that's filtered out here before the request is built.
    """
    return {key: value for key, value in params.items() if value is not None}
