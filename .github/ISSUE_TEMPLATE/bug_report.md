---
name: Bug report
about: Report incorrect library behavior
title: ""
labels: bug
assignees: ""
---

## Problem description

What happens and what was expected instead.

## How to reproduce

Minimal code example (without a real token, if possible):

```python
import asyncio
from avia_api import AviaApiClient

async def main() -> None:
    async with AviaApiClient(token="...") as client:
        ...

asyncio.run(main())
```

## Environment

- `avia-api`: <!-- package version -->
- Python: <!-- python --version -->
- OS:

## Logs / traceback

<!-- If relevant, include logs with the avia_api logger's DEBUG level
     (see the "Logging" section in the README) - but check that they
     contain no token or other secrets before posting. -->

```
paste here
```
