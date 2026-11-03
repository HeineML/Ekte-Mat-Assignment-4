# 12 – Hardening and Documentation

**Status:** implemented 2026-11-03. Written and implemented in one session at the user's request; the group has **not yet reviewed** this plan. The assessed version has **not been tagged yet**: the group decides which commit is assessed.

## Context

Phases 0–11 implement every mandatory requirement in `docs/requirements.md` §6. Phase 12 covers priority item 12 ("tests, seed data and documentation") and the deliverables in §11. Phase 13 (optional extensions, §7) is **skipped** by the group's decision on 2026-11-03.

## Changes

- **Friendly error pages** for 400, 403 and 404 (`views/errors/error.html`), so access-control failures don't show Flask's default pages.
- **Architecture test** (`tests/test_architecture.py`): fails if a controller or template mentions `sqlite`, which keeps the storage replaceable by Neo4j.
- **Seed data:** two more synthetic orders (one delivered and paid, one cancelled), so the admin filters and every common status can be demonstrated. The seed now has 5 orders covering 5 of the 6 statuses.
- **README:** features, installation, seed, run and test instructions, a manual test walkthrough, project structure.
- **CLAUDE.md:** updated for the finished phases (images module, services, error pages, test fixtures).

## Requirement traceability

| Req | Feature | Routes | Plan | Tests |
|---|---|---|---|---|
| C1 | Menu grouped and filtered by event; only published items | `GET /`, `/menu?event=` | 03 | `test_menu.py` |
| C2 | Cart: add, change, remove, estimated total, minimum quantity | `/cart`, `/cart/add`, `/cart/update`, `/cart/remove` | 04 | `test_cart.py` |
| C3 | Register, log in, submit order with guest groups | `/register`, `/login`, `/logout`, `/checkout` | 05, 06 | `test_auth.py`, `test_checkout.py` |
| C4 | My orders with order and payment status, own orders only | `/orders`, `/orders/<id>` | 07 | `test_my_orders.py` |
| C5 | Ask about an order, read the answer | `POST /orders/<id>/questions` | 10 | `test_questions.py` |
| A1 | Create, edit, delete, publish/unpublish food items | `/admin/food…` | 08 | `test_admin_food.py` |
| A2 | Upload picture with preview before saving; placeholder | `/admin/food/new`, `/admin/food/<id>/edit` | 11 | `test_images.py` |
| A3 | All orders, filter by status and event date, change status and payment | `/admin/orders…` | 09 | `test_admin_orders.py` |
| A4 | See questions with their order, answer them | `/admin/questions…`, `/admin/orders/<id>` | 10 | `test_questions.py` |
| §5 | Domain model, price snapshot on order items | – | 02, 06 | `test_repositories.py`, `test_checkout.py` |
| §8 | Hashed passwords, own data only, admin role required | decorators | 05, 07, 10 | `test_auth.py`, `test_my_orders.py`, `test_questions.py`, `*_admin_*` |
| §2 | Storage isolated behind repositories | – | 00, 02 | `test_repositories.py`, `test_architecture.py` |

## Verification (done 2026-11-03)

1. `pytest`: 160 tests pass.
2. A seeded dev server (separate database) was driven over HTTP: menu hides the unpublished dish; checkout requires login and redirects to the new order; another customer's order gives 404; a customer gets 403 on admin pages; the admin lands on orders, filters by status, changes status and payment, answers a question; the customer sees the new statuses and the answer; an uploaded picture is served on the menu.

## Left for the group

- Review plans 05–12 and the **[Decision]** points in them.
- Choose and tag the assessed version (for example `git tag v1.0`), and take screenshots for the report (§11).
