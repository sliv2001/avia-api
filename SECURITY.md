# Security Policy

## Supported versions

The project is currently in Beta (`0.x`). Security patches
are only released for the latest published version on PyPI.

| Version      | Supported          |
| ------------ | ------------------ |
| 0.x (latest) | :white_check_mark: |
| < latest     | :x:                |

## How to report a vulnerability

Please **do not open a public issue** for vulnerabilities that
could affect users (e.g. a token leaking into logs, SSRF
via request parameters, incorrect API response validation, etc.).

Instead, use one of these channels:

- GitHub [Private vulnerability reporting](https://github.com/sliv2001/avia-api/security/advisories/new) for this repository (preferred);
- or email the author directly: ivan.sladkov@yandex.ru.

In your report, please include:

- the `avia-api` and Python version;
- steps to reproduce / a PoC;
- the potential impact (what exactly could go wrong).

## What happens next

- Acknowledgment of receipt - within a few days.
- Once the issue is confirmed, a patch will be prepared and a new release published; public disclosure of details - after the fix ships.
