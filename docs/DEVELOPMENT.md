# Development

Standardized on **Python 3.12** (pinned in `.python-version`; CI uses 3.12). A
`uv.lock` pins the full dependency set for reproducible installs.

## Setup (recommended: uv)

```bash
# install Python 3.12 + create the venv + install core & dev deps
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install -e ".[dev]"
```

Optional extras (install only what you need):

```bash
uv pip install -e ".[dev,postgres]"     # psycopg for real Postgres/TimescaleDB
uv pip install -e ".[dev,boost]"        # LightGBM/XGBoost
uv pip install -e ".[dev,research]"     # DuckDB research layer
```

Plain-venv fallback (no uv):

```bash
python3.12 -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

| Task | Command |
|---|---|
| Run tests | `pytest -q` |
| Unit only | `pytest tests/unit -q` |
| Integration/e2e | `pytest tests/integration tests/e2e -q` |
| Lint | `ruff check .` |
| Auto-fix lint | `ruff check --fix .` |
| Type-check | `mypy services apps` |
| DB migrate (create/upgrade schema) | `alembic upgrade head` |
| New migration (autogenerate) | `alembic revision --autogenerate -m "msg"` |
| Run terminal (demo) | `uvicorn apps.api.app.main:app --port 8000` |

> On Windows without an activated venv, prefix with the venv interpreter, e.g.
> `.venv\Scripts\python.exe -m pytest -q`.

## Modes

- `APP_MODE=demo` (default): synthetic universe + mock LLM. Safe, offline.
- `APP_MODE=real`: requires real datastores + market data + FreeLLMAPI in `.env`;
  the app **fails fast** at startup if any required value is blank, and never falls
  back to sample data.

Copy `.env.example` → `.env` and fill values. The real `.env` is git-ignored.

## Database

- Dev/test uses **SQLite** (no server needed); the persistence tests run against an
  in-memory SQLite DB and exercise the Alembic baseline migration.
- Deployment uses **Postgres/TimescaleDB** via `DATABASE_URL`; run `alembic upgrade
  head` to create the schema. `migrations/env.py` reads the URL from `Settings`.

## CI

`.github/workflows/ci.yml` runs on Python 3.12: `ruff check` + `pytest` (plus a
non-blocking `pip-audit`). Keep it green before merging.
