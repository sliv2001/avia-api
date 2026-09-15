# Changelog

Все заметные изменения в этом проекте документируются в этом файле.

Формат соответствует [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), версионирование - [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Added

- `CONTRIBUTING.md`, `SECURITY.md`, шаблоны issue/PR для GitHub.
- Бейджи CI/coverage/Python/license в README.

### Changed

- Classifier пакета поднят с `Alpha` до `Beta`.

## [0.1.0] - 2026-09-13

Первый релиз.

### Added

- Асинхронный клиент `AviaApiClient` для Data API Travelpayouts / Aviasales:
  ресурсы `prices` (цены), `directions` (популярные направления) и
  `reference` (справочные данные - страны, города, аэропорты, авиакомпании,
  маршруты).
- Слоистый transport: клиентский rate limiting (`pyrate-limiter`), повторы с
  экспоненциальным backoff и джиттером (`tenacity`), учитывающие заголовок
  `Retry-After` с потолком в 60 секунд на одну попытку, и опциональный кэш
  ответов (`hishel`) поверх sqlite.
- Валидация ответов через pydantic-модели (`frozen=True`, `extra="allow"`) и
  типизированная иерархия исключений (`AviaApiError` и подклассы) для
  сетевых ошибок, HTTP-статусов, бизнес-ошибок API (`success: false`) и
  расхождения схемы ответа.
- Структурированное логирование (`avia_api._client`, `avia_api._transport`)
  жизненного цикла запроса, повторов и rate limiting - без утечки токена в
  логи.
- CI на GitHub Actions: тесты на Python 3.11-3.13 с порогом покрытия 99%,
  линтер и форматтер `ruff`, строгая проверка типов `mypy`.
- Пакетные метаданные для публикации: лицензия MIT, маркер `py.typed`,
  classifiers, ссылки на репозиторий.

[Unreleased]: https://github.com/sliv2001/avia-api/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sliv2001/avia-api/releases/tag/v0.1.0
