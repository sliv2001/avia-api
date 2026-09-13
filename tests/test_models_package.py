from __future__ import annotations

import avia_api.models as models


def test_models_public_api_is_importable() -> None:
    for name in models.__all__:
        assert hasattr(models, name)
