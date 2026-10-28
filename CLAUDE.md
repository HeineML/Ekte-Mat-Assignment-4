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
flask --app app run --debug                        # http://127.0.0.1:5000
pytest                                             # all tests (pytest.ini puts the repo root on sys.path)
pytest tests/test_app.py::test_home_page_renders   # a single test
```

Planned for phase 2, not implemented yet: `flask --app app init-db` (creates the SQLite database in `instance/`) and `flask --app app seed` (synthetic data, including an admin account).

Tests build the app with `create_app(TestConfig)`. Fixtures are in `tests/conftest.py`.

## Architecture

MVC under `app/`:
- **Model, `app/models/`:** dataclass entities and status enums (`entities.py`), abstract repository interfaces (`repositories.py`), domain rules (`services.py`), and the SQLite implementation in `app/models/sqlite/`.
- **Controller, `app/controllers/`:** one Flask blueprint per area (auth, menu, cart, orders, admin_food, admin_orders, admin_questions), plus `login_required` and `admin_required` in `decorators.py`.
- **View, `app/views/`:** Jinja2 templates. Flask is configured with `template_folder="views"`. CSS, JavaScript and images are in `app/static/`, and uploaded images go to `app/static/uploads/` (gitignored).

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
