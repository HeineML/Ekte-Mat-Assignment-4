# 02 – Models and Storage

**Status:** done (2026-10-28). Agreed in Plan mode the same day. Implemented as planned, with two small additions: `User.is_admin` and `Question.is_answered` convenience properties, and the seed's order dates are relative to today so they stay in the future.

## Context

Phase 1 delivered an app that runs and uses the MVC folders, but `app/models/` is empty. Phase 2 builds the whole model layer from `docs/plans/00-architecture.md` §2–3: domain entities, repository interfaces, the SQLite implementation, `init-db` and `seed` commands with synthetic data, and tests. After this phase, phases 3–11 only add controllers, views and small domain rules on top. No routes or pages change in this phase.

**Requirements:** §5 (domain model and relationships), §2 (storage isolated so Neo4j can replace it), §8 (hashed passwords, synthetic data), §12 priority 2. The group decided on SQLite and on guest groups as a list on Order (00-architecture.md).

---

## Files

New:
```
app/models/entities.py          dataclasses + enums (no storage code)
app/models/repositories.py      abstract interfaces + EmailAlreadyRegistered error
app/models/seed.py              CLI commands init-db and seed, storage-independent
app/models/sqlite/__init__.py   SqliteRepositories (bundles the four repos) + init_app
app/models/sqlite/db.py         get_db() / close_db(): one connection per request in flask.g
app/models/sqlite/schema.sql    tables (DROP + CREATE)
app/models/sqlite/repositories.py   the four SQLite repository classes + row→entity mapping
tests/test_repositories.py
tests/test_seed.py
docs/plans/02-models-and-storage.md
```
Changed: `app/models/__init__.py` (`get_repos()`, `init_storage(app)`), `app/__init__.py` (calls `init_storage`), `app/config.py` (TestConfig without `:memory:`, see below), `tests/conftest.py`, `README.md` (seed section), `CLAUDE.md` (commands).

---

## 1. Entities (`app/models/entities.py`)

Plain `@dataclass`es. `id` is `None` until the entity is saved, and IDs are treated as opaque values. Prices are whole NOK as `int`.

- `Role`, `OrderStatus`, `PaymentStatus`: `(str, Enum)`, so values are stored as plain text, with a `label` property for display (`in_preparation` → "In preparation").
  - OrderStatus: submitted, approved, in_preparation, delivered, rejected, cancelled
  - PaymentStatus: not_paid, deposit_paid, invoiced, paid
- `User(id, name, email, password_hash, role)`
- `EventCategory(id, name)`
- `FoodItem(id, name, description, price_nok, minimum_quantity, published, image, allergens: list[str], dietary_labels: list[str], event_categories: list[EventCategory])`
- `GuestGroup(description, size, allergy_notes, dietary_notes)`: a value object owned by Order
- `OrderItem(id, food_item_id, food_name, quantity, unit_price_nok)` + `line_total`. `food_item_id` can become `None` if the food item is deleted later; the name and price snapshot stay.
- `Order(id, customer_id, event_date: date, number_of_guests, delivery_address, status, payment_status, created_at: datetime, items, guest_groups)` + `total`
- `Question(id, order_id, customer_id, question, answer, created_at, answered_at)`

## 2. Repository interfaces (`app/models/repositories.py`)

Abstract base classes. Controllers will only ever see these.

| Interface | Methods |
|---|---|
| `UserRepository` | `add(user)`, `get(id)`, `get_by_email(email)` (case-insensitive; `add` raises `EmailAlreadyRegistered`) |
| `FoodItemRepository` | `list_categories()`, `get_category(id)`, `add_category(cat)`, `add(item)`, `update(item)`, `delete(id)`, `get(id)`, `list_all()`, `list_published(category_id=None)` |
| `OrderRepository` | `add(order)` (order, items and guest groups in one transaction), `get(id)`, `get_for_customer(order_id, customer_id)`, `list_for_customer(customer_id)`, `list_all(status=None, event_date=None)`, `update_status(id, status)`, `update_payment_status(id, payment_status)` |
| `QuestionRepository` | `add(q)`, `get(id)`, `list_for_order(order_id)`, `list_all(unanswered_only=False)`, `answer(id, text)` (sets `answered_at`) |
| `Repositories` | holds `.users`, `.food`, `.orders`, `.questions`, plus `reset()` (empty all storage) |

`get_for_customer` returns `None` for another customer's order. That's the hook for the access rule in section 8 of the requirements.

## 3. SQLite implementation (`app/models/sqlite/`)

- **Connection:** `get_db()` opens one `sqlite3` connection per request or app context in `flask.g`, with `PRAGMA foreign_keys = ON` and `row_factory = sqlite3.Row`. A teardown closes it. This is the pattern from the Flask tutorial.
- **Schema:**

  | Table | Columns |
  |---|---|
  | `users` | `email UNIQUE COLLATE NOCASE` |
  | `event_categories` | `name UNIQUE` |
  | `food_items` | `price_nok` and `minimum_quantity` with CHECK ≥ 0 and ≥ 1; `published` 0/1; `image`; `allergens` and `dietary_labels` as JSON text |
  | `food_item_categories` | join table, CASCADE |
  | `orders` | dates as ISO text, `customer_id` FK |
  | `order_items` | `order_id` CASCADE; `food_item_id` **ON DELETE SET NULL**, so deleting a food item keeps old orders intact |
  | `guest_groups` | `order_id` CASCADE |
  | `questions` | `order_id` CASCADE, `customer_id` FK |

  Status values are not CHECK-constrained in SQL. The enums are the single place where valid values are defined.
- **Mapping:** private `_to_food_item(row)` style helpers convert rows to entities. Rows, SQL and JSON never leave this package.
- `app/models/__init__.py`: `init_storage(app)` picks the implementation from `STORAGE` and stores it in `app.extensions["repos"]`. `get_repos()` returns it. That's the only function controllers will call.

## 4. CLI commands and seed data (`app/models/seed.py`)

Both commands use only the repository interface (`reset()`, `add(...)`), so they will work unchanged for Neo4j.
- `flask --app app init-db`: empties and recreates storage.
- `flask --app app seed`: `init-db` plus synthetic data, then prints a summary and the login details:
  - 5 event categories (Birthday, Confirmation, Wedding, Conference, Christmas party)
  - About 10 food items with allergens, dietary labels and several categories each; at least one unpublished; no images yet (added in phase 11)
  - Users: 1 admin and 2 customers with obviously fake names and `@example.test` emails; passwords hashed with `werkzeug.security`
  - 3 orders with different statuses, payment statuses and event dates, with guest groups
  - 2 questions, one answered and one not
- **Demo logins:** the seed uses fixed, documented demo passwords for these local test accounts (for example `admin@example.test` / `admin123`), so graders and the group can log in after seeding. They only exist in a local database the user creates, so they aren't secrets. If the group reads section 8 strictly, the alternative is that `seed` generates random passwords and prints them; say so when reviewing.

## 5. Tests

- `tests/conftest.py`: the `app` fixture points `DATABASE` at a temporary file under `tmp_path` and calls `reset()`. `:memory:` won't work with one connection per request, because each new connection starts with an empty database. A `repos` fixture yields `get_repos()` inside an app context.
- `tests/test_repositories.py`: one test or a few per behaviour:
  - Saving and loading users; email lookup ignores case; a duplicate email raises `EmailAlreadyRegistered`.
  - Food items keep their lists and categories when saved and loaded; `list_published` hides unpublished items and filters by category; `update`; `delete` keeps old order items (name and price stay, `food_item_id` becomes `None`).
  - Orders keep their items and guest groups when saved and loaded; `total` is correct; `get_for_customer` returns `None` for another customer; `list_all` filters by status and event date; status and payment updates work.
  - Questions: `add`; `list_for_order`; `answer` sets `answered_at`; `unanswered_only` filter.
- `tests/test_seed.py`: run `seed` through `app.test_cli_runner()`, then check the counts, that exactly one admin exists, and that no stored password equals its plain-text password.
- The existing tests in `tests/test_app.py` stay green.

---

## Verification

1. `pytest`: all tests pass, old and new.
2. `flask --app app seed` prints the summary and login details, and `instance/ektemat.sqlite` is created and ignored by git.
3. Optional: open the database in the `sqlite3` shell or DB Browser for SQLite and look at the tables.
4. `git grep sqlite3 app/controllers app/views` finds nothing, which shows the storage boundary is intact.
5. The home page still works with `flask --app app run --debug`.
