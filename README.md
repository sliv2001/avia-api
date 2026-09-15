# avia-api

[![CI](https://github.com/sliv2001/avia-api/actions/workflows/ci.yml/badge.svg)](https://github.com/sliv2001/avia-api/actions/workflows/ci.yml)
[![coverage](https://img.shields.io/badge/coverage-99%25%2B-brightgreen)](https://github.com/sliv2001/avia-api/blob/master/pyproject.toml)
[![python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/sliv2001/avia-api)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Async Python client for the [Aviasales / Travelpayouts Data API](https://support.travelpayouts.com/hc/ru/sections/201008338-Aviasales-flight-data-API) - historical/cached ticket prices, price calendars, and reference data (countries, cities, airports, airlines, routes).

Not covered: real-time search (`Aviasales Flights Search API`) and the GraphQL API - these are separate products with a different interaction model.

## Installation

The package is available through any standard package manager:

```bash
pip install avia-api
# or
uv add avia-api
# or
poetry add avia-api
```

Requires Python 3.11+.

## Quick start

```python
import asyncio
from avia_api import AviaApiClient

async def main() -> None:
    async with AviaApiClient(token="YOUR_TOKEN") as client:
        prices = await client.prices.cheap(origin="MOW", destination="LED")
        for destination, by_index in prices.items():
            for entry in by_index.values():
                print(destination, entry.price, entry.airline, entry.departure_at)

asyncio.run(main())
```

You can also skip passing the token explicitly and put it in the `TRAVELPAYOUTS_TOKEN` environment variable - the client will pick it up automatically. Get a token in your personal dashboard: https://www.travelpayouts.com/programs/100/tools/api

## Resources and endpoints

All methods return models validated by [pydantic](https://docs.pydantic.dev/)

### `client.prices` - prices

| Method                                            | Endpoint                               | Description                                      |
| ------------------------------------------------- | -------------------------------------- | ------------------------------------------------ |
| `cheap(origin, destination, ...)`                 | `GET /v1/prices/cheap`                 | Cheapest tickets for a route                     |
| `direct(origin, destination, ...)`                | `GET /v1/prices/direct`                | Same, but direct flights only                    |
| `calendar(origin, destination, depart_date, ...)` | `GET /v1/prices/calendar`              | Price calendar for every day of the month        |
| `monthly(origin, destination, ...)`               | `GET /v1/prices/monthly`               | Lowest price by month                            |
| `latest(...)`                                     | `GET /v2/prices/latest`                | Latest found prices across the whole search base |
| `month_matrix(origin, destination, ...)`          | `GET /v2/prices/month-matrix`          | Price calendar for a month (v2)                  |
| `week_matrix(origin, destination, ...)`           | `GET /v2/prices/week-matrix`           | Price calendar for a week                        |
| `nearest_places_matrix(origin, destination, ...)` | `GET /v2/prices/nearest-places-matrix` | Prices for nearby airports/cities                |

### `client.directions` - popular routes

| Method                       | Endpoint                     | Description                      |
| ---------------------------- | ---------------------------- | -------------------------------- |
| `airline(airline_code, ...)` | `GET /v1/airline-directions` | Popular routes for an airline    |
| `city(origin, ...)`          | `GET /v1/city-directions`    | Popular destinations from a city |

### `client.reference` - reference data

Public, rarely changing JSON files:

| Method                             | Endpoint                                       |
| ---------------------------------- | ---------------------------------------------- |
| `countries(language="en")`         | `GET /data/{language}/countries.json`          |
| `cities(language="en")`            | `GET /data/{language}/cities.json`             |
| `airports(language="en")`          | `GET /data/{language}/airports.json`           |
| `airlines(language="en")`          | `GET /data/{language}/airlines.json`           |
| `airline_alliances(language="en")` | `GET /data/{language}/airlines_alliances.json` |
| `planes()`                         | `GET /data/planes.json`                        |
| `routes()`                         | `GET /data/routes.json`                        |

## Client configuration

```python
from avia_api import AviaApiClient
from pyrate_limiter import Rate, Duration

client = AviaApiClient(
    token="...",
    rate=Rate(5, Duration.SECOND),   # outgoing request rate limit (pyrate-limiter)
    max_retries=3,                   # retries on 429/5xx and connection drops
    cache_ttl=1800,                  # seconds; None disables the response cache
    cache_path="avia_api.db",        # sqlite cache file (hishel), relative path
                                      # goes under .cache/hishel/
    timeout=10.0,
)
```

- **Rate limiting** - [pyrate-limiter](https://github.com/vutran1710/PyrateLimiter), a single bucket per client. Limits the rate of outgoing requests before they're sent, to avoid getting a `429` from the API.
- **Retries** - [tenacity](https://github.com/jd/tenacity) with exponential backoff and jitter; on `429` the `Retry-After` header is honored if present, but capped at 60 seconds per attempt - an unusually large value from the server (e.g. during an incident on its side) can't stall a request indefinitely.
- **Cache** - [hishel](https://hishel.com) on top of sqlite. Travelpayouts responses don't send `Cache-Control`, so `FilterPolicy` is used (any successful `GET` is cached, with entry lifetime governed by `cache_ttl`) instead of RFC 9111.

For tests or non-standard scenarios you can pass `transport=...` - your own `httpx.AsyncBaseTransport`, which fully disables rate limiting/retry/cache, and requests go straight through it (see `respx` or `httpx.MockTransport`).

## Error handling

All exceptions derive from `avia_api.AviaApiError`:

| Exception                    | When it occurs                                                 |
| ---------------------------- | -------------------------------------------------------------- |
| `AviaApiConnectionError`     | Network unavailable / timeout - after retries are exhausted    |
| `AviaApiAuthenticationError` | HTTP 401/403 - token missing or invalid                        |
| `AviaApiRateLimitError`      | HTTP 429 - after retries are exhausted; has `.retry_after`     |
| `AviaApiServerError`         | HTTP 5xx - after retries are exhausted                         |
| `AviaApiHTTPStatusError`     | Other HTTP errors                                              |
| `AviaApiResponseError`       | HTTP 200, but `{"success": false}` in the body; has `.payload` |
| `AviaApiValidationError`     | Response doesn't match the expected schema (API changed)       |

## Logging

The library uses standard `logging`. To see logs, enable the desired level for the `avia_api` logger:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("avia_api").setLevel(logging.DEBUG)
```

What is logged and at what level:

| Logger                | Level     | Event                                                                      |
| --------------------- | --------- | -------------------------------------------------------------------------- |
| `avia_api._transport` | `DEBUG`   | Delay in the rate limiter; successful request and its status               |
| `avia_api._transport` | `WARNING` | Retry after a transient error/status; retry budget exhausted               |
| `avia_api._client`    | `DEBUG`   | Outgoing request (path + query parameters) and response status             |
| `avia_api._client`    | `WARNING` | HTTP 401/403/429/4xx; `{"success": false}` in the response body            |
| `avia_api._client`    | `ERROR`   | HTTP 5xx; network error after retries; response failed the pydantic schema |
