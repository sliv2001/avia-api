from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from avia_api._utils import parse_retry_after


@pytest.mark.parametrize("value", [None, ""])
def test_parse_retry_after_missing(value: str | None) -> None:
    assert parse_retry_after(value) is None


def test_parse_retry_after_delay_seconds() -> None:
    assert parse_retry_after("120") == 120.0


def test_parse_retry_after_strips_whitespace() -> None:
    assert parse_retry_after("  30  ") == 30.0


def test_parse_retry_after_zero() -> None:
    assert parse_retry_after("0") == 0.0


def test_parse_retry_after_rejects_negative_or_non_digit() -> None:
    # "-5" is not `str.isdigit()`, so it falls through to HTTP-date parsing
    # and fails there too.
    assert parse_retry_after("-5") is None


def test_parse_retry_after_garbage() -> None:
    assert parse_retry_after("not a date") is None


def test_parse_retry_after_http_date_in_future() -> None:
    target = datetime.now(timezone.utc) + timedelta(seconds=60)
    header = target.strftime("%a, %d %b %Y %H:%M:%S GMT")
    result = parse_retry_after(header)
    assert result is not None
    # Allow a little slack for the time elapsed while running the test.
    assert 55.0 <= result <= 60.5


def test_parse_retry_after_http_date_in_past_is_clamped_to_zero() -> None:
    target = datetime.now(timezone.utc) - timedelta(seconds=60)
    header = target.strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert parse_retry_after(header) == 0.0


def test_parse_retry_after_naive_http_date_returns_none() -> None:
    # No timezone/offset information at all: parsedate_to_datetime can still
    # return a naive datetime, which is treated as unusable.
    assert parse_retry_after("Mon, 01 Jan 2024 00:00:00") is None
