from __future__ import annotations

from avia_api._params import clean_params


def test_clean_params_drops_none_values() -> None:
    result = clean_params({"a": 1, "b": None, "c": "x"})
    assert result == {"a": 1, "c": "x"}


def test_clean_params_keeps_falsy_non_none_values() -> None:
    result = clean_params({"zero": 0, "empty_str": "", "false": False})
    assert result == {"zero": 0, "empty_str": "", "false": False}


def test_clean_params_empty_input() -> None:
    assert clean_params({}) == {}


def test_clean_params_all_none() -> None:
    assert clean_params({"a": None, "b": None}) == {}


def test_clean_params_does_not_mutate_input() -> None:
    original = {"a": 1, "b": None}
    clean_params(original)
    assert original == {"a": 1, "b": None}
