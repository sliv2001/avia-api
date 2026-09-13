from __future__ import annotations

import avia_api


def test_public_api_is_importable() -> None:
    assert hasattr(avia_api, "AviaApiClient")
    for name in avia_api.__all__:
        assert hasattr(avia_api, name)


def test_version_is_set() -> None:
    assert isinstance(avia_api.__version__, str)
    assert avia_api.__version__
