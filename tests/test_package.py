from __future__ import annotations

import logging

import avia_api


def test_public_api_is_importable() -> None:
    assert hasattr(avia_api, "AviaApiClient")
    for name in avia_api.__all__:
        assert hasattr(avia_api, name)


def test_version_is_set() -> None:
    assert isinstance(avia_api.__version__, str)
    assert avia_api.__version__


def test_package_logger_has_null_handler_by_default() -> None:
    # Per Python's logging howto, a library must never emit "no handlers
    # could be found" warnings to a consuming application that hasn't
    # configured logging itself.
    handlers = logging.getLogger("avia_api").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)
