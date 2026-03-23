# triho-backend

FastAPI backend for the Association of Trichologists.

## Testing

Requirements: PostgreSQL database `triho_db_test` (same host/credentials as `DATABASE_URL`, database name `triho_db_test`). Schema is recreated on pytest startup.

```bash
cd backend
poetry install --with dev
poetry run pytest tests/ -v
```

- **Default run** excludes tests marked `@pytest.mark.integration` (real Moneta API). This is configured via `addopts` in `pyproject.toml`.
- **Integration (Moneta):** set `MONETA_USERNAME` and run  
  `poetry run pytest tests/test_moneta_integration.py -m integration -v`

### Coverage

```bash
poetry run pytest tests/ --cov=app/services --cov-report=term-missing
```

`[tool.coverage.report] fail_under` in `pyproject.toml` tracks the current baseline; the QA target is **70%** for `app/services` — increase `fail_under` as coverage grows.

**Note:** Event registration with a **zero-price** tariff is not covered by an E2E test: the service creates a `payments` row before `process_event_registration_payment` short-circuits, and the DB check `chk_payments_amount_positive` rejects `amount=0`. Add a dedicated path (skip payment row or relax constraint) before asserting a free-tariff flow.

### Parallel runs (pytest-xdist)

`pytest-xdist` is included for local use. **Do not use `pytest -n auto`** against the default shared `triho_db_test` and session-wide `drop_all`/`create_all` in `conftest.py` — workers will race. To parallelize, use separate databases per worker (e.g. `triho_db_test_gw0`) and adjust `TEST_DB_URL`; until then, run tests single-process in CI.

## Lint

```bash
poetry run ruff check app/
```
