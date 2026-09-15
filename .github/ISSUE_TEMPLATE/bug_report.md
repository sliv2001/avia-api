---
name: Bug report
about: Сообщить о некорректном поведении библиотеки
title: ""
labels: bug
assignees: ""
---

## Описание проблемы

Что происходит и что ожидалось вместо этого.

## Как воспроизвести

Минимальный пример кода (по возможности - без реального токена):

```python
import asyncio
from avia_api import AviaApiClient

async def main() -> None:
    async with AviaApiClient(token="...") as client:
        ...

asyncio.run(main())
```

## Окружение

- `avia-api`: <!-- версия пакета -->
- Python: <!-- python --version -->
- ОС:

## Логи / traceback

<!-- Если уместно, включите логи с DEBUG-уровнем логгера avia_api
     (см. раздел "Логирование" в README) - но проверьте, что в них
     нет токена или других секретов перед публикацией. -->

```
вставьте сюда
```
