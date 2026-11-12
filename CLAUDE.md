# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Ekte Mat Online is INFO212 Obligatory Assignments 4 and 5: an online catering and ordering system built with Flask using MVC. Oblig 4 (tag `v1.0`) stored data in SQLite; Oblig 5 moves all data to Neo4j (Aura). Customers browse a menu grouped by event, fill a cart, register or log in, submit orders, follow order and payment status, and ask questions. Admins manage food items and images, orders and questions.

- The assignment texts are the source of truth (requirement IDs C1–C5 for customers, A1–A4 for admins; Oblig 5 adds the Neo4j requirements). Do not invent requirements. When it leaves something open, point that out and ask instead of deciding silently.
- The group did **not** complete Lab 7. Never describe any material as work done in Lab 7.
- Architecture, domain model and design decisions are summarised in `docs/report.md`.

## Commands

```
python -m venv .venv && .venv\Scripts\activate     # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt
copy .env.example .env                             # then fill in NEO4J_* (app instance) and NEO4J_TEST_* (separate test instance)
flask --app app seed                               # reset the Neo4j instance + synthetic demo data
flask --app app init-db                            # reset DB to empty
flask --app app run --debug                        # http://127.0.0.1:5000
pytest                                             # all tests; database tests are skipped without NEO4J_TEST_*
pytest tests/test_repositories.py::test_duplicate_email_is_rejected   # a single test
```

`seed` prints the demo logins (admin@example.test / admin123, customers kunde123); they're also in the README.

Tests build the app with `create_app(TestConfig)` against a **separate** Neo4j instance from `NEO4J_TEST_*` (loaded from `.env` by `tests/conftest.py`); `reset()` deletes all its data before every test, so never point it at the app's instance (conftest refuses if the URIs are equal). Tests can't run in parallel. Fixtures `app`, `client`, `repos` and `users` (an admin plus customers Kari and Ola, password `secret123`) and the `login(client, email)` helper are in `tests/conftest.py`; `UPLOAD_FOLDER` also points into `tmp_path`. `tests/test_architecture.py` fails if a controller or template mentions `sqlite`, `neo4j` or Cypher, if anything outside `app/models/neo4j/` imports the driver, or if anything imports `legacy/`. `tests/test_repositories.py` uses only the repository interface.

## Architecture

MVC under `app/`:
- **Model, `app/models/`:** dataclass entities and status enums (`entities.py`), abstract repository interfaces (`repositories.py`), the storage-independent `init-db`/`seed` CLI commands (`seed.py`), and the Neo4j implementation in `app/models/neo4j/` (`db.py`: one driver per connection setting for the process, `read()`/`write()` run one managed transaction each; `repositories.py`: the Cypher; `__init__.py`: `reset()` and the constraints). `init_storage(app)` in `app/models/__init__.py` picks the backend from `config.STORAGE` (`"neo4j"`). The Oblig 4 SQLite code is in `legacy/sqlite/`, kept for reference and not imported. Domain rules and validation go in `services.py` (`menu_by_event`, `menu_filters`, `build_cart`, `check_quantity`, `register_customer`, `authenticate`, `place_order`, `save_food_item`, `delete_food_item`, `ask_question`, `answer_question`, `customers_by_id`); they return `(result, [error messages])` and controllers flash the errors instead of repeating logic. Picture files are handled by `images.py` (random filenames in `config.UPLOAD_FOLDER`). Seed photos live in `app/static/img/food/` with their Wikimedia Commons attribution in `credits.json` (shown at `/photo-credits`; keep it in sync when adding photos); `seed` copies them into the upload folder and `init-db`/`seed` empty that folder.
- **Controller, `app/controllers/`:** one Flask blueprint per area (auth, menu, cart, orders, admin_food, admin_orders, admin_questions), plus `login_required` and `admin_required` in `decorators.py` and `safe_next()`/`form_int()` in `helpers.py`. `auth.py` loads the logged-in user into `g.user` (or `None`) before every request from `session["user_id"]`; templates use `g.user` too.
- **View, `app/views/`:** Jinja2 templates. Flask is configured with `template_folder="views"`. CSS, JavaScript and images are in `app/static/`, and uploaded images go to `app/static/uploads/` (gitignored). Status badges and the order items/guest-groups tables are macros in `views/orders/_status.html`, shared by customer and admin pages; 400/403/404 use `views/errors/error.html` (handlers in `app/__init__.py`). Reuse the `food_card(item)` macro (`views/menu/_food_card.html`, accepts a `{% call %}` block for extra buttons) and the `nok` filter (`{{ price | nok }}` → "1 250 kr", defined in `app/__init__.py`).

Only the repositories talk to Neo4j:
- Controllers and templates get data only through `get_repos()` and entities from `app.models`. They never import `neo4j` or `app.models.neo4j`, and contain no Cypher.
- Repositories return entity dataclasses, never driver records. All Cypher uses `$parameters`, never string formatting of values.
- Multi-step writes, such as an order with its lines and guest groups or a food item with its relationships, happen inside one repository method and one `write()` transaction.
- Repository tests target the interface.

Graph model: `(:User)-[:PLACED]->(:Order)-[:HAS_LINE]->(:OrderLine)-[:OF_ITEM]->(:FoodItem)`, `(:Order)-[:HAS_GUEST_GROUP]->(:GuestGroup)`, `(:User)-[:ASKED]->(:Question)-[:ABOUT]->(:Order)`, `(:FoodItem)-[:IN_CATEGORY]->(:EventCategory)`, `(:FoodItem)-[:CONTAINS {position}]->(:Allergen)`, `(:FoodItem)-[:HAS_LABEL {position}]->(:DietaryLabel)`. Ids are integers from a `(:Counter {name: <label>})` node, increased in the creating transaction, so routes (`<int:order_id>`) and the cart keep integer ids. Emails are stored in lower case (the unique constraint is case-sensitive). The menu filter (C1) is the graph query: `list_published(category_id, exclude_allergens, require_labels)`.

The shopping cart is kept in the Flask session as `session["cart"] = {"<food_item_id>": quantity}` (string keys, because the session is JSON) until checkout. Only `app/controllers/cart.py` touches the session format (`_load()`/`_save()`). Pricing and rules live in `services.py`: `build_cart(raw)` returns a `Cart` with current prices and drops unpublished or deleted items, and `check_quantity(item, qty)` enforces the minimum order quantity (reuse it at checkout).

## Domain rules that are easy to get wrong

- Customers only ever see published food items.
- Cart and order quantities below a food item's `minimum_quantity` are rejected.
- `OrderItem` stores the unit price and name at the time of ordering, so old orders don't change when a food item is edited. Deleting a food item (`DETACH DELETE`) only removes the line's `OF_ITEM`, so `food_item_id` becomes `None`.
- Order status: submitted → approved → in_preparation → delivered, plus rejected and cancelled. Payment status: not_paid, deposit_paid, invoiced, paid. Use the enums and never free-text values.
- Customers can access only their own orders and questions. Look orders up by both order and customer, and return 404 for anything else.
- Every admin route requires the admin role. Admin accounts come from the seed data, not from public registration.

## Workflow

- Before a larger feature: use Plan mode and have the group agree on the plan before implementing it.
- Reference requirement IDs (C1–C5, A1–A4) in plans and commit messages to keep requirements traceable.
- Status (2026-11-12): Oblig 4 is done and tagged `v1.0` (`docs/report.md` has its report material). Oblig 5 (Neo4j Aura) is in progress on branch `Heine`; group decisions: Aura, menu filter on allergens/dietary labels as the graph query, SQLite moved to `legacy/`, tests on a separate Aura instance. Still to do: Oblig 5 report (graph diagram, rationale, comparison with the Oblig 4 class diagram) and the `oblig5` tag, created only when the group says so.

## Security and data

- Synthetic test data only.
- Store passwords hashed with `werkzeug.security`, never as plain text.
- Read `SECRET_KEY`, `NEO4J_*` and other secrets from the environment (a local `.env`, see `.env.example`). Never commit `.env` files, API keys or passwords.
