---
name: add-tests
description: Add or extend pytest tests for avia-api (the async Travelpayouts/Aviasales client) following this repo's established conventions - respx for transport-layer behavior, httpx.MockTransport for resource/client logic, pydantic model validation checks. Use whenever adding a new resource method, model, transport behavior, or a regression test for a bug fix in src/avia_api.
user-invocable: true
---

# Adding tests to avia-api

This repo's test suite (`tests/`) covers `src/avia_api` at ~99% line coverage using
`pytest` + `pytest-asyncio` (auto mode) + `respx` + `httpx.MockTransport`. Follow the
patterns below instead of inventing new ones, so the suite stays consistent.

## Layout

- One test file per source module: `tests/test_<module>.py` (e.g. `_utils.py` ->
  `test_utils.py`, `resources/prices.py` -> `test_resources_prices.py`).
- `tests/conftest.py` - shared fixtures (`client_factory`).
- `tests/helpers.py` - shared response builders (`json_response`, `envelope`).
- No `pytest.mark.asyncio` needed: `asyncio_mode = "auto"` is set in `pyproject.toml`,
  so any `async def test_...` just works.

## Two testing strategies - pick the right one

**A. Resource / client logic (params sent, response parsed, errors mapped)**
Use the `client_factory` fixture. It builds an `AviaApiClient` with
`transport=httpx.MockTransport(handler)`, which - per the client's own docstring -
bypasses rate limiting/retry/caching entirely. This keeps these tests fast and
deterministic; you're only testing *this* library's logic, not httpx/hishel/tenacity.

```python
async def test_some_new_method(client_factory: Callable[..., AviaApiClient]) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return json_response(envelope({...}))

    client = client_factory(handler)
    result = await client.some_resource.some_method(...)

    assert captured["path"] == "/v1/expected/path"
    assert captured["params"] == {"origin": "MOW"}  # None-valued kwargs must be absent
    assert isinstance(result, ExpectedModel)
```

Use this for: new resource methods (assert path + query params + parsed return type),
`_client.py` error-mapping (status code -> exception, `success: false` ->
`AviaApiResponseError`, schema mismatch -> `AviaApiValidationError`, transport error ->
`AviaApiConnectionError`), token/header wiring, lifecycle (`aclose`/context manager).

**B. Transport-layer behavior itself (`_transport.py`: cache, retry, rate limit)**
`MockTransport` bypasses this layer entirely, so it can't test it. Instead use `respx`
(installed as a pytest plugin - `respx_mock` fixture is auto-available) to intercept at
the underlying network transport. respx patches `httpx.AsyncHTTPTransport` globally, so
it still intercepts even though `build_transport()` wraps it inside the resilient/cache
transports - meaning cache hits, retries, and rate limiting all run for real.

```python
async def test_new_transport_behavior(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get("/data").mock(return_value=httpx.Response(200, json={"ok": True}))
    transport = build_transport(rate=None, max_retries=3, cache_ttl=None, cache_path="unused.db")

    async with httpx.AsyncClient(transport=transport, base_url="https://example.avia-api.test") as client:
        response = await client.get("/data")

    assert response.status_code == 200
    assert route.call_count == 1
```

- Disable irrelevant layers to isolate what you're testing: `cache_ttl=None` when
  testing retries; `rate=None` (uses the fast `DEFAULT_RATE`) when not testing rate
  limiting.
- Cache tests: pass `cache_path=tmp_path / "cache.db"` (never a bare filename - it would
  write into the repo). Assert via `route.call_count`, not by inspecting internals.
- Retry tests: use `respx_mock...mock(side_effect=[...])` to return a sequence of
  responses/exceptions. Assert `route.call_count` for the number of attempts made.
- **Timing-sensitive assertions (rate limiting) must use a generous lower bound only**
  (e.g. `assert elapsed >= 0.3` for a 1 req/sec limit), never a tight upper bound - CI
  machines are slow and jittery, but a limiter that isn't limiting at all is a real bug
  worth catching.

## Model tests

- Validate via `Model.model_validate({...})` or `TypeAdapter(...).validate_python(...)`.
- Remember `AviaBaseModel` is `frozen=True, extra="allow"`: mutating an instance raises
  `pydantic.ValidationError` (not `TypeError`/`AttributeError`), and unknown fields land
  in `.model_extra` rather than raising.
- `OptionalDate`/`OptionalDateTime` turn `""` into `None` (the API's way of representing
  a missing one-way return date) - test that explicitly when a new field uses them.

## Exceptions

- Assert `issubclass(ExcType, AviaApiError)`.
- For `AviaApiHTTPStatusError` subclasses, assert `.status_code` and `.response`.
- For `AviaApiRateLimitError`, assert `.retry_after`.
- For `AviaApiResponseError`, assert `.payload`.

## Checklist for a new resource method

1. Add a test in the matching `tests/test_resources_<resource>.py` using strategy A.
2. Assert the request path, the query params sent (including that `None` kwargs are
   dropped and any documented defaults, e.g. `calendar_type`, appear).
3. Assert the returned value's type(s) - use `isinstance(x, ExpectedModel)`, not just
   equality on a dict.
4. If the endpoint isn't envelope-wrapped (like `nearest_places_matrix`), don't use the
   `envelope()` helper - build the raw body matching that endpoint's actual shape.

## Checklist for a bug fix

Write a regression test that fails against the old code and passes against the fix,
placed in the test file matching the module that changed. Prefer the narrowest strategy
(A vs B above) that actually exercises the bug.

## Running

```bash
poetry run pytest -q
poetry run pytest -q --cov=avia_api --cov-report=term-missing   # coverage report
poetry run pytest -q tests/test_transport.py -k rate_limiting    # one area
```

Coverage is expected to stay at ~99%+ (the only justified miss is the
`if TYPE_CHECKING:` import guard in `resources/_base.py`). If a change drops coverage,
add the missing test rather than accepting the gap.
