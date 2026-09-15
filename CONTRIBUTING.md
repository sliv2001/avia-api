# Contributing

Thanks for your interest in `avia-api`! Below is how to set up the
environment and what's checked before merging.

## Environment

You need Python 3.11+ and [Poetry](https://python-poetry.org/).

```bash
poetry install
```

The virtual environment is created in `.venv/` inside the repository (see `poetry.toml`).

## Before submitting a PR

```bash
poetry run ruff check .           # linter
poetry run ruff format --check .  # formatting
poetry run mypy                   # strict type checking
poetry run pytest -q --cov=avia_api --cov-report=term-missing --cov-fail-under=99
```

All four commands must pass without errors - this is exactly what CI runs (`.github/workflows/ci.yml`).

To automatically fix formatting:

```bash
poetry run ruff format .
```

## Tests

- Coverage must not drop below 99% (the only accepted exception is the `if TYPE_CHECKING:` block in `resources/_base.py`). If a PR drops coverage - add the missing test rather than lowering the threshold.
- One test file per source module (`tests/test_<module>.py`).
- For resource/client logic (request parameters, response parsing, error mapping) use the `client_factory` fixture (`tests/conftest.py`) - it builds a client with `httpx.MockTransport` and doesn't touch the real transport stack.
- For the transport layer's own behavior (cache/retry/rate-limit in `_transport.py`) use `respx` (the `respx_mock` fixture) - it patches `httpx.AsyncHTTPTransport` globally, so cache, retry, and rate limiting actually run.
- Timing-sensitive checks (rate limiting) should only check a lower bound with margin - never assert an exact/upper bound.

Detailed conventions - in `.claude/skills/add-tests/SKILL.md`.

Rule of Thumb: write the code yourself, and delegate testing to Claude or ChatGPT.
This provides cross-checking.

## Code style

- Formatting and import sorting - via `ruff format`/`ruff` (isort is enabled in `select`), don't align by hand.
- The public API is fully typed; `mypy --strict` must pass without `# type: ignore` wherever it can be avoided.
- Don't add abstractions/flags for the future without a concrete current need - use the existing code as a guide for the right amount of abstraction.

## Commits and PRs

- One PR - one logical task (feature, fix, refactor).
- In the PR description, state what changed and why, not just what.
- If public behavior changes - add an entry to `CHANGELOG.md` under `[Unreleased]`.

### Pre-commit checklist

- [ ] Commits are made on your own branch. Commits to `master` and `dev` are forbidden.
- [ ] README.md describes the changed logic
- [ ] CLAUDE.md describes the changed logic. SKILL.md files are updated if needed.
- [ ] CHANGELOG.md describes the changes.

### Pre-PR checklist

- [ ] The PR goes from your own branch into `dev`, or from `dev` into `master`. Other PRs are forbidden.
- [ ] README.md describes the changed logic
- [ ] CLAUDE.md describes the changed logic. SKILL.md files are updated if needed.
- [ ] CHANGELOG.md describes the changes.
- [ ] Logging is sufficient.
- [ ] Exception handling is sufficient.
- [ ] All tests pass locally.
- [ ] ruff passes locally.
- [ ] mypy passes locally.
- [ ] CI passes.

## Releasing

Publishing to PyPI is automated via `.github/workflows/publish.yml` using
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) -
no API token is stored anywhere.

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/avia_api/__init__.py`.
2. Move the `[Unreleased]` section in `CHANGELOG.md` under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading, and update the compare links at the
   bottom of the file.
3. Merge that into `master`, then tag it `vX.Y.Z` and push the tag.
4. Create a GitHub Release from that tag (this is what actually triggers
   the workflow - a bare tag push does not).
5. The `build` job re-runs the full test suite and builds the sdist/wheel;
   the `publish` job then uploads them to PyPI via the `pypi` GitHub
   Environment.

## Reporting a vulnerability

Don't open a public issue - see [SECURITY.md](SECURITY.md).
