# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Ekte Mat Online is INFO212 Obligatory Assignment 4: a first version of an online catering and ordering system built with Flask using MVC. Customers browse a menu grouped by event, fill a cart, register or log in, submit orders, follow order and payment status, and ask questions. Admins manage food items and images, orders and questions.

- `docs/requirements.md` is the source of truth. Do not invent requirements. When it leaves something open, point that out and ask instead of deciding silently.
- The group did **not** complete Lab 7. `docs/requirements.md` is reconstructed from the assignment text and the Lab 7 instructions. Never describe any material as work done in Lab 7.
- Architecture, domain model, routes and the phase roadmap are in `docs/plans/00-architecture.md`.

## Commands

```
python -m venv .venv && .venv\Scripts\activate     # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt
flask --app app seed                               # reset DB (instance/ektemat.sqlite) + synthetic demo data
flask --app app init-db                            # reset DB to empty
flask --app app run --debug                        # http://127.0.0.1:5000
pytest                                             # all tests (pytest.ini puts the repo root on sys.path)
pytest tests/test_repositories.py::test_duplicate_email_is_rejected   # a single test
```

`seed` prints the demo logins (admin@example.test / admin123, customers kunde123); they're also in the README.

Tests build the app with `create_app(TestConfig)` and a fresh SQLite file under pytest's `tmp_path` (`:memory:` doesn't work because each request opens its own connection). Fixtures `app`, `client` and `repos` are in `tests/conftest.py`. `tests/test_repositories.py` uses only the repository interface, so it can be reused for a Neo4j backend.

## Architecture

MVC under `app/`:
- **Model, `app/models/`:** dataclass entities and status enums (`entities.py`), abstract repository interfaces (`repositories.py`), the storage-independent `init-db`/`seed` CLI commands (`seed.py`), and the SQLite implementation in `app/models/sqlite/` (`db.py` keeps one connection per request in `flask.g`; `schema.sql`; `repositories.py`). `init_storage(app)` in `app/models/__init__.py` picks the backend from `config.STORAGE`. Domain rules that combine repository calls go in `services.py` (e.g. `menu_by_event()`); controllers call these instead of repeating logic.
- **Controller, `app/controllers/`:** one Flask blueprint per area (auth, menu, cart, orders, admin_food, admin_orders, admin_questions), plus `login_required` and `admin_required` in `decorators.py`.
- **View, `app/views/`:** Jinja2 templates. Flask is configured with `template_folder="views"`. CSS, JavaScript and images are in `app/static/`, and uploaded images go to `app/static/uploads/` (gitignored). Reuse the `food_card(item)` macro (`views/menu/_food_card.html`, accepts a `{% call %}` block for extra buttons) and the `nok` filter (`{{ price | nok }}` → "1 250 kr", defined in `app/__init__.py`).

Storage must stay replaceable by Neo4j:
- Controllers and templates get data only through `get_repos()` and entities from `app.models`. They never import `sqlite3` or `app.models.sqlite`.
- Repositories return entity dataclasses, never `sqlite3.Row`s or SQL.
- Multi-step writes, such as an order together with its items, happen inside one repository method.
- Repository tests target the interface, so they can be reused for a Neo4j implementation.

The shopping cart is kept in the Flask session as `{food_item_id: quantity}` until checkout.

## Domain rules that are easy to get wrong

- Customers only ever see published food items.
- Cart and order quantities below a food item's `minimum_quantity` are rejected.
- `OrderItem` stores the unit price and name at the time of ordering, so old orders don't change when a food item is edited.
- Order status: submitted → approved → in_preparation → delivered, plus rejected and cancelled. Payment status: not_paid, deposit_paid, invoiced, paid. Use the enums and never free-text values.
- Customers can access only their own orders and questions. Look orders up by both order and customer, and return 404 for anything else.
- Every admin route requires the admin role. Admin accounts come from the seed data, not from public registration.

## Workflow

- Work in the small phases listed in `docs/plans/00-architecture.md`, one phase at a time and in that order.
- Before a larger feature: use Plan mode, have the group agree on the plan, and save it as `docs/plans/NN-name.md` (goal, requirement IDs, files, steps, verification, status). Then implement it.
- Reference requirement IDs (C1–C5, A1–A4) in plans and commit messages to keep requirements traceable.

## Security and data

- Synthetic test data only.
- Store passwords hashed with `werkzeug.security`, never as plain text.
- Read `SECRET_KEY` and other secrets from the environment. Never commit `.env` files, API keys or passwords.
