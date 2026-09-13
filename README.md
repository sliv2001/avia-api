# avia-api

Асинхронный Python-клиент для [Data API Aviasales / Travelpayouts](https://support.travelpayouts.com/hc/ru/sections/201008338-Aviasales-flight-data-API) - исторических/кэшированных цен на авиабилеты, календарей цен и справочных данных (страны, города, аэропорты, авиакомпании, маршруты).

Не покрывает: real-time поиск (`Aviasales Flights Search API`) и GraphQL API - это отдельные продукты с иной моделью взаимодействия.

## Установка

Пакет доступен через любой стандартный менеджер пакетов:

```bash
pip install avia-api
# или
uv add avia-api
# или
poetry add avia-api
```

Требуется Python 3.11+.

## Быстрый старт

```python
import asyncio
from avia_api import AviaApiClient

async def main() -> None:
    async with AviaApiClient(token="ВАШ_ТОКЕН") as client:
        prices = await client.prices.cheap(origin="MOW", destination="LED")
        for destination, by_index in prices.items():
            for entry in by_index.values():
                print(destination, entry.price, entry.airline, entry.departure_at)

asyncio.run(main())
```

Токен также можно не передавать явно, а положить в переменную окружения `TRAVELPAYOUTS_TOKEN` - клиент подхватит её автоматически. Токен получают в личном кабинете: https://www.travelpayouts.com/programs/100/tools/api

## Ресурсы и эндпоинты

Все методы возвращают модели, провалидированные [pydantic](https://docs.pydantic.dev/)

### `client.prices` - цены

| Метод                                             | Эндпоинт                               | Описание                                     |
| ------------------------------------------------- | -------------------------------------- | -------------------------------------------- |
| `cheap(origin, destination, ...)`                 | `GET /v1/prices/cheap`                 | Самые дешёвые билеты по направлению          |
| `direct(origin, destination, ...)`                | `GET /v1/prices/direct`                | То же, только прямые рейсы                   |
| `calendar(origin, destination, depart_date, ...)` | `GET /v1/prices/calendar`              | Календарь цен на каждый день месяца          |
| `monthly(origin, destination, ...)`               | `GET /v1/prices/monthly`               | Самая низкая цена по месяцам                 |
| `latest(...)`                                     | `GET /v2/prices/latest`                | Последние найденные цены по всей базе поиска |
| `month_matrix(origin, destination, ...)`          | `GET /v2/prices/month-matrix`          | Календарь цен за месяц (v2)                  |
| `week_matrix(origin, destination, ...)`           | `GET /v2/prices/week-matrix`           | Календарь цен за неделю                      |
| `nearest_places_matrix(origin, destination, ...)` | `GET /v2/prices/nearest-places-matrix` | Цены по соседним аэропортам/городам          |

### `client.directions` - популярные направления

| Метод                        | Эндпоинт                     | Описание                         |
| ---------------------------- | ---------------------------- | -------------------------------- |
| `airline(airline_code, ...)` | `GET /v1/airline-directions` | Популярные маршруты авиакомпании |
| `city(origin, ...)`          | `GET /v1/city-directions`    | Популярные направления из города |

### `client.reference` - справочные данные

Публичные, редко меняющиеся JSON-файлы:

| Метод                              | Эндпоинт                                       |
| ---------------------------------- | ---------------------------------------------- |
| `countries(language="en")`         | `GET /data/{language}/countries.json`          |
| `cities(language="en")`            | `GET /data/{language}/cities.json`             |
| `airports(language="en")`          | `GET /data/{language}/airports.json`           |
| `airlines(language="en")`          | `GET /data/{language}/airlines.json`           |
| `airline_alliances(language="en")` | `GET /data/{language}/airlines_alliances.json` |
| `planes()`                         | `GET /data/planes.json`                        |
| `routes()`                         | `GET /data/routes.json`                        |

## Конфигурация клиента

```python
from avia_api import AviaApiClient
from pyrate_limiter import Rate, Duration

client = AviaApiClient(
    token="...",
    rate=Rate(5, Duration.SECOND),   # ограничение исходящих запросов (pyrate-limiter)
    max_retries=3,                   # повторы при 429/5xx и обрывах соединения
    cache_ttl=1800,                  # секунд; None - отключить кэш ответов
    cache_path="avia_api.db",        # sqlite-файл кэша (hishel), относительный путь
                                      # уходит под .cache/hishel/
    timeout=10.0,
)
```

- **Rate limiting** - [pyrate-limiter](https://github.com/vutran1710/PyrateLimiter), единый bucket на клиент. Ограничивает скорость исходящих запросов ещё до отправки, чтобы не словить `429` от API.
- **Retries** - [tenacity](https://github.com/jd/tenacity) с экспоненциальным backoff и джиттером; при `429` учитывается заголовок `Retry-After`, если он присутствует.
- **Кэш** - [hishel](https://hishel.com) поверх sqlite. Ответы Travelpayouts не присылают `Cache-Control`, поэтому используется `FilterPolicy` (кэшируется любой успешный `GET`, а срок жизни записи определяется `cache_ttl`), а не RFC 9111.

Для тестов или нестандартных сценариев можно передать `transport=...` - собственный `httpx.AsyncBaseTransport`, тогда rate limiting/retry/кэш полностью отключаются, и запросы идут напрямую через него (см. `respx` или `httpx.MockTransport`).

## Обработка ошибок

Все исключения наследуются от `avia_api.AviaApiError`:

| Исключение                   | Когда возникает                                           |
| ---------------------------- | --------------------------------------------------------- |
| `AviaApiConnectionError`     | Сеть недоступна / таймаут - после исчерпания retry        |
| `AviaApiAuthenticationError` | HTTP 401/403 - токен отсутствует или невалиден            |
| `AviaApiRateLimitError`      | HTTP 429 - после исчерпания retry; есть `.retry_after`    |
| `AviaApiServerError`         | HTTP 5xx - после исчерпания retry                         |
| `AviaApiHTTPStatusError`     | Прочие HTTP-ошибки                                        |
| `AviaApiResponseError`       | HTTP 200, но `{"success": false}` в теле; есть `.payload` |
| `AviaApiValidationError`     | Ответ не соответствует ожидаемой схеме (API изменился)    |
