# 01 – Foundation

**Status:** done (2026-10-28). The group approved moving to phase 1 on 2026-10-28.
**Requirements:** §2 (Flask, MVC, CLAUDE.md, no secrets), §12 priority 1.
**Builds on:** `00-architecture.md`.

## Goal
A minimal Flask application that runs, uses the agreed MVC folder structure, and has one passing test. No domain models, storage or features yet; those start in phase 2.

## Steps
1. Replace the placeholder files `app/controllers`, `app/documents`, `app/static` and `app/views` with directories. `documents` becomes `models`.
2. `app/__init__.py`: a `create_app(config_class)` factory with `template_folder="views"` that registers the blueprints.
3. `app/config.py`: `Config` (`SECRET_KEY` from the environment with a dev-only fallback, `DATABASE` path in `instance/` ready for phase 2) and `TestConfig`.
4. `app/models/__init__.py`: an empty package with a docstring, filled in phase 2.
5. `app/controllers/menu.py`: blueprint `menu` with `GET /` rendering a stub home page. It becomes the real menu in phase 3.
6. `app/views/base.html` (layout, nav, flash messages) and `app/views/menu/index.html`.
7. `app/static/css/style.css`: basic styling.
8. `requirements.txt` (Flask, pytest), a README draft (install, run, test), and the confirmed commands in `CLAUDE.md`.
9. `tests/conftest.py` (app and client fixtures using `TestConfig`) and `tests/test_app.py` (smoke test: `GET /` returns 200).

## Files
`app/__init__.py`, `app/config.py`, `app/models/__init__.py`, `app/controllers/__init__.py`, `app/controllers/menu.py`, `app/views/base.html`, `app/views/menu/index.html`, `app/static/css/style.css`, `tests/conftest.py`, `tests/test_app.py`, `pytest.ini` (added during implementation so `pytest` can import `app`), `requirements.txt`, `README.md`, `CLAUDE.md`.

## Verification
- `pytest` passes.
- `flask --app app run` serves the home page at http://127.0.0.1:5000 with the base layout and CSS.
