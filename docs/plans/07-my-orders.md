# 07 – My Orders

**Status:** implemented 2026-11-03. Written and implemented in one session at the user's request; the group has **not yet reviewed** this plan.

## Context

Customers can submit orders (phase 6) but can't see them afterwards. Phase 7 adds **C4**.

**Requirement C4:** a logged-in customer must be able to see their own orders. Each order shows the order information, the current order status and the current payment status. Customers must not see other customers' orders (§8).

**Out of scope:** questions on an order (phase 10).

---

## Behaviour

| Route | Does |
|---|---|
| `GET /orders` (login) | The customer's orders, newest first: order number, event date, guests, total, order status, payment status, link to the detail page. Empty state links to the menu. |
| `GET /orders/<id>` (login) | Order information (number, submitted date, event date, guests, delivery address), order status, payment status, the items with saved prices and total, and the guest groups with allergy and dietary notes. |

- Lookups always use `orders.get_for_customer(order_id, g.user.id)`. Someone else's order, or one that doesn't exist, returns **404** (not 403), so customers can't tell which order numbers exist.
- After checkout the customer is redirected to the new order's detail page instead of the menu.
- The nav shows "My orders" when logged in.
- Statuses are shown with the enums' `label` ("In preparation", "Deposit paid") in a coloured badge.

## Implementation

- `app/controllers/orders.py`: `list_orders` and `detail` routes; checkout redirect.
- Views: `orders/list.html`, `orders/detail.html`, `orders/_status.html` (badge macros and the items/guest-groups tables, reused by the admin pages), nav link in `base.html`, badge styles.

## Tests (`tests/test_my_orders.py`)

- Both pages require login.
- The list shows only the logged-in customer's orders, with status and payment status labels.
- The detail shows information, items, total, guest groups and statuses.
- Another customer's order and an unknown id give 404.
- Checkout redirects to the new order's page.

## Verification

1. `pytest`
2. Seeded server: log in as Kari and see her two orders; open `/orders/3` (Ola's) and get 404.
