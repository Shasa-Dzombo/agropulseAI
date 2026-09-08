# AgroPulse AI

FastAPI backend + Flutter mobile app for smallholder farm management in Kenya
(farms, drone survey pipeline, crop diagnosis, chama/social layer, marketplace).

## Layout

| Path | What |
|---|---|
| `main.py` | FastAPI app + uvicorn entrypoint (**not** `app/main.py`) |
| `app/api/` | Route modules — `drones.py`, `farms.py`, `chamas.py`, `diagnoses.py`, … |
| `app/models/`, `app/schemas/` | SQLAlchemy models and Pydantic schemas |
| `app/services/`, `app/ml/`, `app/drones/` | Business logic, ML, drone processing |
| `alembic/` | Database migrations (`alembic.ini` at root) |
| `tests_drones/` | The collectable test suite |
| `mobile/` | Flutter app, package `agropulse_mobile`, Dart SDK `^3.13.2` |
| `mobile/lib/features/` | Feature-per-directory: `drones`, `farms`, `chama`, `diagnosis`, … |

## Commands

Backend (venv is `avenv/`; on Windows use `avenv/Scripts/python.exe`):

```bash
avenv/Scripts/python.exe -m pytest          # run tests
avenv/Scripts/python.exe main.py            # run the API (uvicorn, reload when DEBUG)
avenv/Scripts/python.exe -m alembic upgrade head
```

Mobile (from `mobile/`):

```bash
flutter analyze     # lint/static analysis — config in analysis_options.yaml
flutter test
flutter run
```

## Gotchas

- **`pytest` only collects `tests_drones/`.** `pyproject.toml` sets `testpaths = ["tests_drones"]`
  because `tests/` imports modules that do not exist anywhere in the codebase
  (`app.database.base`, `app.api.main`, `app.core.config`, `app.core.security`) and dies at
  collection. Don't "fix" this by widening `testpaths`.
- **The repo is not pip-installed.** `import app` resolves only because `pyproject.toml` sets
  `pythonpath = ["."]`. Run pytest from the repo root.
- Pydantic v2 deprecation warnings from class-based `Config` in `app/schemas/` are known noise.

## Git

Feature work happens on `flutter-app`; `main` is the PR base. Conventional commit prefixes
(`feat:`, `fix:`, `refactor:`, `chore:`).

## Engineering standards

ECC rule packs, installed locally under `.claude/rules/ecc/` (gitignored — a fresh clone will
not have them, and these imports simply no-op if absent). Reinstall with
`/ecc:configure-ecc` or by copying from the ECC plugin's `rules/` directory.

@.claude/rules/ecc/common/coding-style.md
@.claude/rules/ecc/common/security.md
@.claude/rules/ecc/common/git-workflow.md
@.claude/rules/ecc/common/code-review.md
@.claude/rules/ecc/common/patterns.md
@.claude/rules/ecc/common/performance.md
@.claude/rules/ecc/common/development-workflow.md
@.claude/rules/ecc/common/agents.md
@.claude/rules/ecc/common/hooks.md
@.claude/rules/ecc/python/coding-style.md
@.claude/rules/ecc/python/fastapi.md
@.claude/rules/ecc/python/patterns.md
@.claude/rules/ecc/python/security.md
@.claude/rules/ecc/python/testing.md
@.claude/rules/ecc/python/hooks.md
@.claude/rules/ecc/dart/coding-style.md
@.claude/rules/ecc/dart/patterns.md
@.claude/rules/ecc/dart/security.md
@.claude/rules/ecc/dart/testing.md
@.claude/rules/ecc/dart/hooks.md
