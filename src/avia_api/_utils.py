from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime


def parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header into a number of seconds.

    Supports both the delay-seconds and HTTP-date forms defined by RFC 9110.
    Returns ``None`` if the header is missing or unparsable.
    """
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        return None
    return max((retry_at - datetime.now(retry_at.tzinfo)).total_seconds(), 0.0)
