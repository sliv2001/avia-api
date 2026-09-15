# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-09-15

Initial release.

### Added

- Async client `AviaApiClient` for the Travelpayouts / Aviasales Data API:
  `prices`, `directions` (popular routes), and `reference` (reference data -
  countries, cities, airports, airlines, routes) resources.
- Layered transport: client-side rate limiting (`pyrate-limiter`), retries with
  exponential backoff and jitter (`tenacity`) that honor the `Retry-After`
  header capped at 60 seconds per attempt, and an optional response cache
  (`hishel`) on top of sqlite.
- Response validation via pydantic models (`frozen=True`, `extra="allow"`) and
  a typed exception hierarchy (`AviaApiError` and subclasses) for network
  errors, HTTP statuses, API business errors (`success: false`), and response
  schema drift.
- Structured logging (`avia_api._client`, `avia_api._transport`) of the
  request lifecycle, retries, and rate limiting - without leaking the token
  into the logs.
- CI on GitHub Actions: tests on Python 3.11-3.13 with a 99% coverage
  threshold, the `ruff` linter/formatter, and strict `mypy` type checking.
- Package metadata for publishing: MIT license, `py.typed` marker,
  classifiers, repository links.
- `CONTRIBUTING.md`, `SECURITY.md`, GitHub issue/PR templates.
- CI/coverage/Python/license badges in the README.
- `dependabot.yml` for automated dependency and GitHub Actions updates.

[Unreleased]: https://github.com/sliv2001/avia-api/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sliv2001/avia-api/releases/tag/v0.1.0
