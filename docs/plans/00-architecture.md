# 00 – Architecture and Development Plan

**Status:** agreed. Drafted with Claude Code in Plan mode on 2026-10-28 and agreed by the group on 2026-10-28. Group decisions: SQLite storage, rename `documents/` → `models/`, guest groups as a list on Order.

## Context

The repo contains only `docs/requirements.md` (the group's requirements, reconstructed from the Oblig 4 text and the Lab 7 instructions) and a first-draft structure the group pushed. There is no application code yet. Section 9 of the requirements says to plan first and then implement in small phases, so this document proposes the architecture and roadmap for the group to review. **No application code is written in this step.** Once the plan is approved, the only output is two documentation files (see "What happens after approval").

Requirement IDs (C1–C5, A1–A4) refer to `docs/requirements.md`. Nothing below adds a new mandatory requirement. Places where the requirements leave room for interpretation are marked **[Decision]**.

---

## 1. Project structure

### What's there now
```
app/controllers   (file: "#flas blueprints and routes")
app/documents     (file: "#domain classes and repository classes")
app/static        (file: "CSS, JavaScript and pictures")
app/views         (file: "#jinja2-maler, HTML-pages")
docs/requirements.md
```
The idea is right: one folder per MVC part under `app/`. Recommended changes:

1. **Turn the four placeholder *files* into directories.** They were committed as one-line files, so nothing can go inside them yet.
2. **[Decision] Rename `documents/` → `models/`.** The requirements call this layer "Model", and "documents" could be confused with document storage or `docs/`. The folder's intended content (domain classes plus repository classes) stays the same.
3. **Keep `views/` as the template folder** with `Flask(__name__, template_folder="views")`. The MVC naming survives and Flask works the same way.
4. **Add the minimum supporting files:** an app factory, config, tests, a `requirements.txt` with dependencies (separate from `docs/requirements.md`), CLAUDE.md and a README.

### Proposed structure (first working version)
```
app/
  __init__.py              create_app(): config, blueprints, storage wiring, CLI commands
  config.py                Config / TestConfig (SECRET_KEY from env, DB path)
  models/                  ── MODEL
    entities.py            dataclasses + status enums (no storage code)
    repositories.py        abstract repository interfaces (the "contract")
    sqlite/                SQLite implementation of the interfaces
      schema.sql
      repositories.py
    services.py            domain rules: min-quantity check, place order (price snapshot), allowed status values
  controllers/             ── CONTROLLER (one blueprint per area)
    auth.py  menu.py  cart.py  orders.py
    admin_food.py  admin_orders.py  admin_questions.py
    decorators.py          login_required, admin_required
  views/                   ── VIEW (Jinja2)
    base.html  auth/  menu/  cart/  orders/  admin/
  static/
    css/  js/  img/ (placeholder image)  uploads/ (gitignored)
instance/                  SQLite file lives here (gitignored by the existing .gitignore)
tests/
docs/requirements.md
docs/plans/
CLAUDE.md  README.md  requirements.txt
```
Seeding and DB setup are Flask CLI commands registered in the factory (`flask --app app init-db`, `flask --app app seed`), so there's no separate scripts folder. The start command is `flask --app app run`, so there's no `run.py`.

---

## 2. Domain model

Entities are plain Python dataclasses in `app/models/entities.py`. IDs are treated as opaque values: integers in SQLite, and possibly something else in Neo4j.

| Entity | Attributes |
|---|---|
| **User** | id, name, email (unique), password_hash, role (`customer` \| `admin`) |
| **EventCategory** | id, name (Birthday, Confirmation, Wedding, Conference, Christmas party) |
| **FoodItem** | id, name, description, price_nok, minimum_quantity, published, image (filename or None), allergens: list, dietary_labels: list, event_categories: list |
| **Order** | id, customer_id, event_date, number_of_guests, delivery_address, status, payment_status, created_at, items: list[OrderItem], guest_groups (see below) |
| **OrderItem** | id, order_id, food_item_id, food_name, quantity, unit_price_nok (copied when the order is placed) |
| **Question** | id, order_id, customer_id, question, answer, created_at, answered_at |

Enums:
- `OrderStatus`: submitted, approved, in_preparation, delivered, rejected, cancelled
- `PaymentStatus`: not_paid, deposit_paid, invoiced, paid

**[Decision] Allergy and dietary notes "per guest group" (C3).** Section 5 lists `allergy_notes` and `dietary_notes` as single fields on Order, but C3 asks for notes *per guest group*. Recommendation: a small value object **GuestGroup** (description, size, allergy_notes, dietary_notes) stored as a list on Order. The checkout form shows a few rows and ignores blank ones. The simpler alternative is two free-text fields on Order where the customer describes each group, which is closer to section 5 but weaker on C3.

Relationships (as in section 5): User 1–* Order; Order 1–* OrderItem; OrderItem *–1 FoodItem; Order 1–* Question; User 1–* Question; FoodItem *–* EventCategory; Order 1–* GuestGroup (if chosen).

**Shopping cart:** stored in the Flask session as `{food_item_id: quantity}`, not in the database. Customers can fill a cart before logging in, and the cart becomes an Order when they check out.

---

## 3. Storage that can be swapped for Neo4j

- `app/models/repositories.py` defines abstract classes: `UserRepository`, `FoodItemRepository` (including categories), `OrderRepository` (including items and guest groups), `QuestionRepository`. Method names describe what the domain needs, for example `list_published(category=None)`, `list_all(status=None, event_date=None)`, `get_for_customer(order_id, customer_id)` and `create_with_items(...)`.
- `app/models/sqlite/` implements those classes with the built-in `sqlite3` module, so no ORM is needed. **[Decision] SQLite rather than JSON:** filtering, uniqueness and multi-table writes are much easier, and the requirements allow either.
- The factory picks the implementation from config (`STORAGE = "sqlite"`) and makes it available through a single accessor, `get_repos()`.
- **Rules that make Neo4j a drop-in later:**
  - Controllers and templates only import from `app.models` (entities, services, `get_repos()`), never from `sqlite3` or `app.models.sqlite`.
  - Repositories return entity dataclasses, never `sqlite3.Row`s or SQL.
  - Multi-step writes such as an order plus its items happen in a single repository method.
  - Lists such as allergens or categories are lists on the entity. How they're stored (join tables, JSON columns, graph relationships) is the repository's private business.
  - Repository tests are written against the interface, so the same tests can be run against a future Neo4j implementation.

Swapping later means adding `app/models/neo4j/` and changing one config value.

---

## 4. Controllers and routes

| Blueprint | Routes | Covers |
|---|---|---|
| `menu` | `GET /` → menu; `GET /menu?event=<id>` (grouped by category, published items only) | C1 |
| `cart` | `GET /cart`; `POST /cart/add`; `POST /cart/update`; `POST /cart/remove` | C2 |
| `auth` | `GET/POST /register`; `GET/POST /login`; `POST /logout` | C3 |
| `orders` (login) | `GET/POST /checkout`; `GET /orders`; `GET /orders/<id>`; `POST /orders/<id>/questions` | C3, C4, C5 |
| `admin_food` (admin) | `GET /admin/food`; `GET/POST /admin/food/new`; `GET/POST /admin/food/<id>/edit`; `POST /admin/food/<id>/delete`; `POST /admin/food/<id>/toggle-published` | A1, A2 |
| `admin_orders` (admin) | `GET /admin/orders?status=&event_date=`; `GET /admin/orders/<id>`; `POST /admin/orders/<id>/status`; `POST /admin/orders/<id>/payment` | A3 |
| `admin_questions` (admin) | `GET /admin/questions?unanswered=1`; `POST /admin/questions/<id>/answer` | A4 |

Access control lives in `decorators.py`. Customer order and question lookups always go through `get_for_customer(...)`, which returns 404 for other customers' orders (section 8). Admins log in at the same `/login` and are sent to `/admin/orders`. Admin accounts are created only by the seed command, never by public registration.

---

## 5. Views (pages)

**Customer:** `base.html` (nav, flash messages, cart count) · `menu/index.html` (event tabs, item cards with picture, price, minimum quantity, allergens and labels) · `cart/index.html` (quantities, remove, estimated total, minimum-quantity errors) · `auth/register.html`, `auth/login.html` · `orders/checkout.html` (event date, guests, address, guest-group rows) · `orders/list.html` (order and payment status) · `orders/detail.html` (items, statuses, questions and answers, form to ask a question)

**Admin:** `admin/food_list.html` (with publish toggle) · `admin/food_form.html` (create/edit, image upload with JavaScript preview before saving, used for both A1 and A2) · `admin/orders_list.html` (filters for status and event date) · `admin/order_detail.html` (change status and payment, see its questions) · `admin/questions.html` (list, linked order, answer form)

**Images (A2):** upload to `static/uploads/`. Before saving, the browser shows the chosen file using `FileReader`. Items without an image show a placeholder. No external AI API is used in the first version.

---

## 6. Development phases

Each phase ends with a working app, its tests passing and a commit. Each phase starts with Plan mode and an agreed plan in `docs/plans/` (section 9). The order follows the priority list in section 12.

| # | Phase | Delivers | Req |
|---|---|---|---|
| 0 | Architecture and CLAUDE.md | this plan saved as `docs/plans/00-architecture.md`; `CLAUDE.md` | §2, §9 |
| 1 | Foundation | placeholders → folders, app factory, config, `base.html`, a stub home page, `requirements.txt`, README draft, pytest smoke test | §12.1 |
| 2 | Models and storage | entities, repository interfaces, SQLite implementation and schema, `init-db` and `seed` commands with synthetic data, repository tests | §12.2 |
| 3 | Customer menu | menu page grouped and filtered by event | C1 |
| 4 | Shopping cart | session cart, minimum-quantity validation | C2 |
| 5 | Register and login | hashed passwords, session login, decorators, seeded admin | C3, §8 |
| 6 | Checkout | order with guest groups and price snapshot | C3 |
| 7 | My orders | list and detail of own orders, access control | C4 |
| 8 | Admin food | create, edit, delete, publish | A1 |
| 9 | Admin orders | list, filters, detail, change status and payment | A3 |
| 10 | Questions and answers | customer asks, admin answers, customer reads | C5, A4 |
| 11 | Images | upload, preview, placeholder | A2 |
| 12 | Hardening and docs | more tests, complete seed data, finished README, tag the assessed version | §11 |
| 13 | Optional extensions | only if time remains | §7 |

Small neighbouring phases (for example 3+4 or 10+11) can share one plan if the group prefers.

---

## 7. What CLAUDE.md should contain

- Required header; one paragraph of project context; `docs/requirements.md` is the source of truth and requirements must not be invented; **Lab 7 was not completed by the group, so material must not be presented as Lab 7 work**.
- Commands: create the venv, `pip install -r requirements.txt`, `flask --app app init-db`, `flask --app app seed`, `flask --app app run --debug`, `pytest`, and how to run a single test (`pytest tests/test_x.py::test_name`). These are added in phase 1 once they actually exist.
- Architecture rules: the MVC boundaries above; templates are in `app/views`; controllers never touch `sqlite3`; repositories return entities; keep the code ready for Neo4j.
- Domain rules that are easy to get wrong: only published items are shown to customers; minimum quantity is enforced; prices are copied onto order items; status and payment values come from the enums; customers can only access their own orders and questions.
- Workflow: Plan mode → agreed plan in `docs/plans/NN-name.md` → implement one phase → tests → commit; reference requirement IDs in plans and commits.
- Security: synthetic data only, hashed passwords, `SECRET_KEY` from the environment, no secrets or `.env` committed.

## 8. Plans to save under docs/plans/

`00-architecture.md` (this document, once agreed), then one plan per phase: `01-foundation.md`, `02-models-and-storage.md`, `03-menu.md`, `04-cart.md`, `05-auth.md`, `06-checkout.md`, `07-my-orders.md`, `08-admin-food.md`, `09-admin-orders.md`, `10-questions.md`, `11-images.md`, `12-hardening.md`. Each plan lists: goal, requirement IDs, files touched, steps, how to verify, and status (proposed, agreed or done). This gives the audit trail and traceability that section 10 asks for.

---

## Output of phase 0

Only documentation, no application code: this file and `CLAUDE.md`.

## Verification
- The group checks this document against `docs/requirements.md`: every item in section 6 of the requirements maps to a phase, and nothing has been added as mandatory that isn't in the requirements.

## Group decisions (2026-10-28)
1. Storage: **SQLite** (not JSON).
2. Model folder: **renamed `documents/` → `models/`**.
3. Guest groups: **a list of GuestGroup on Order** (not two free-text fields).
