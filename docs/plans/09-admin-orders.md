# 09 – Admin Orders

**Status:** done (2026-11-03). Written and implemented in one session at the user's request, one phase and one commit at a time, and **agreed by the group on 2026-11-03 after implementation**. The decisions marked **[Decision]** were accepted as written.

## Context

Customers submit orders (phase 6) and follow their status (phase 7), but nobody can change the status yet. Phase 9 adds **A3**.

**Requirement A3:** administrators must be able to see all customer orders, filter by status, filter by event date, open an individual order, change the order status and change the payment status. Order status: submitted → approved → in preparation → delivered, plus rejected and cancelled. Payment status: not paid, deposit paid, invoiced, paid.

**Out of scope:** questions on the order page (phase 10).

---

## Behaviour

All routes use `admin_required`.

| Route | Does |
|---|---|
| `GET /admin/orders?status=&event_date=` | All orders, newest first: number, customer, event date, guests, total, order status, payment status. A filter form with a status dropdown ("All statuses" + the six statuses) and an event-date field. Both filters can be combined. An unknown status or invalid date is ignored with an error message. |
| `GET /admin/orders/<id>` | Order information, customer name and email, items, guest groups with allergy and dietary notes, and two forms: order status and payment status. |
| `POST /admin/orders/<id>/status` | Sets the order status from the `OrderStatus` enum. |
| `POST /admin/orders/<id>/payment` | Sets the payment status from the `PaymentStatus` enum. |

- An unknown order id → 404; a value that isn't in the enum → 400.
- **[Decision]** Any status can be chosen from any other status. The requirements describe the normal flow but don't say transitions must be enforced, and a free choice lets the admin correct mistakes. The dropdown lists the statuses in flow order.
- After a change the admin returns to the order page with a confirmation.
- Admins now land on the order list after login. The admin nav gets an "Orders" link.

## Implementation

- **Model, `services.py`:** `customers_by_id(orders)` → `{customer_id: User}` so the list can show names without the template calling repositories.
- **Controller:** `app/controllers/admin_orders.py`, blueprint `admin_orders`, prefix `/admin/orders`.
- **Views:** `admin/orders_list.html`, `admin/order_detail.html` (reuses `orders/_status.html` macros).

## Tests (`tests/test_admin_orders.py`)

- Every route requires admin (login redirect / 403).
- The list shows all customers' orders.
- Filter by status, by event date, and both together; invalid filter values are ignored with a message.
- The detail shows customer, items, guest groups and statuses.
- Changing order status and payment status saves the enum value; the customer's order page shows the new status.
- Invalid status value → 400; unknown order → 404.

## Verification

1. `pytest`
2. Seeded server as admin: filter by "In preparation", open Ola's order, set it to Delivered and Paid, then log in as Ola and see the change.
