# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`avia-api` is an async Python client for the Travelpayouts / Aviasales Data API
(historical/cached ticket prices, price calendars, and reference data: countries,
cities, airports, airlines, routes). It does **not** cover the real-time Flights
Search API or the GraphQL API — those are separate products.

Python 3.11+, managed with Poetry. In-project virtualenv (`.venv/`, per `poetry.toml`).

## Commands

```bash
poetry install                 # install deps into .venv

poetry run pytest -q                                              # run tests
poetry run pytest -q --cov=avia_api --cov-report=term-missing     # with coverage
poetry run pytest -q tests/test_transport.py -k rate_limiting     # one test/area
```

There is no configured linter/formatter/type-checker in `pyproject.toml` — don't
assume `ruff`/`mypy`/`black` are set up unless you check.

Test coverage is expected to stay at ~99%+ (the only accepted miss is the
`if TYPE_CHECKING:` guard in `resources/_base.py`). If a change drops coverage,
add the missing test instead of accepting the gap. See `.claude/skills/add-tests/SKILL.md`
(the `add-tests` skill) for this repo's detailed testing conventions before writing new tests.

## Architecture

**Layered transport (`_transport.py`)**, built bottom-up by `build_transport()`:

```
AsyncCacheTransport (hishel)   <- outermost, only if cache_ttl is not None
  -> _ResilientTransport        <- rate limiting (pyrate-limiter) + retries (tenacity)
    -> httpx.AsyncHTTPTransport <- raw network I/O
```

- Rate limiting and retries happen *underneath* the cache, so cache hits never touch
  the limiter or retry loop.
- Travelpayouts responses carry no `Cache-Control`/`ETag` headers, so the cache uses
  hishel's `FilterPolicy` (caches every successful GET unconditionally, TTL governed by
  `cache_ttl`) rather than RFC 9111 semantics, which would never store anything here.
- Retries cover `httpx.TransportError` and retryable status codes (429, 500, 502, 503,
  504), honoring `Retry-After` when present, otherwise exponential backoff with jitter.
- Passing `transport=...` to `AviaApiClient` bypasses this whole stack (no rate
  limiting/retry/cache) — this is the standard way to inject `httpx.MockTransport` or
  `respx` in tests.

**Client / Resource / Model layering:**

- `AviaApiClient` (`_client.py`) owns the `httpx.AsyncClient`, builds the transport
  stack, attaches `X-Access-Token` (from the `token` arg or `TRAVELPAYOUTS_TOKEN` env
  var), and exposes three resource namespaces: `.prices`, `.directions`, `.reference`.
  Its `_get_json()` is the single choke point for every request: it does transport-error
  mapping, HTTP-status-to-exception mapping (`_raise_for_status`), the
  `{"success": false}` → `AviaApiResponseError` check, and pydantic validation of the
  payload against a caller-supplied `TypeAdapter`.
- Resources (`resources/*.py`) subclass `BaseResource` (`resources/_base.py`), which just
  forwards to `client._get_json`. Each resource method builds `params` (via
  `clean_params()` to drop `None`s — httpx doesn't do this on its own), picks a
  module-level `TypeAdapter` constant, calls `self._get(path, params, adapter)`, and for
  envelope-wrapped endpoints returns `envelope.data` rather than the envelope itself.
- Most v1/v2 endpoints are wrapped in the `{"success", "data", "error"}` shape modeled by
  `Envelope[T]` (`models/common.py`). A few endpoints (e.g.
  `prices.nearest_places_matrix`, everything under `reference.*`) return a bare
  list/object instead — these use their own `TypeAdapter` built directly over the model,
  not `Envelope[...]`.
- All response models extend `AviaBaseModel` (`models/common.py`): `frozen=True`
  (mutating raises `pydantic.ValidationError`, not `AttributeError`) and `extra="allow"`
  (unknown fields the API adds later land in `.model_extra` instead of breaking
  validation). `OptionalDate`/`OptionalDateTime` are shared annotated types that turn the
  API's `""` (its way of marking a missing one-way return date) into `None`.
- Date-like parameters throughout the resources are plain `str`, not `datetime.date` —
  several endpoints accept both `"YYYY-MM-DD"` and a month-only `"YYYY-MM"`, which `date`
  can't represent, so format choice is left to the caller.

**Exceptions** (`exceptions.py`): everything derives from `AviaApiError`.
`AviaApiHTTPStatusError` (and its `AviaApiAuthenticationError` /
`AviaApiRateLimitError` / `AviaApiServerError` subclasses) carry `.response`/
`.status_code`; `AviaApiRateLimitError` additionally carries `.retry_after`.
`AviaApiResponseError` (HTTP 200 but `success: false`) carries `.payload`.
`AviaApiValidationError` means the response didn't match the expected pydantic schema
(signals the upstream API shape changed).

## Testing conventions (see `add-tests` skill for full detail)

Two strategies, matched to what's under test:

- **Resource/client logic** (params sent, response parsed, errors mapped): use the
  `client_factory` fixture (`tests/conftest.py`), which builds a client with
  `transport=httpx.MockTransport(handler)` — this bypasses the transport stack entirely,
  keeping these tests fast/deterministic and focused on this library's own logic.
- **Transport-layer behavior itself** (cache/retry/rate-limit in `_transport.py`): use
  `respx` (`respx_mock` fixture), which patches `httpx.AsyncHTTPTransport` globally and
  so still intercepts even underneath the resilient/cache wrapper layers — meaning cache
  hits, retries, and rate limiting all actually run.

One test file per source module (`tests/test_<module>.py`). Timing-sensitive assertions
(rate limiting) must use a generous lower bound only, never a tight upper bound.
