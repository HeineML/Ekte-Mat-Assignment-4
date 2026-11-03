# 06 – Checkout

**Status:** done (2026-11-03). Written and implemented in one session at the user's request, one phase and one commit at a time, and **agreed by the group on 2026-11-03 after implementation**. The decisions marked **[Decision]** were accepted as written.

## Context

Customers can fill a cart (phase 4) and log in (phase 5). Phase 6 turns the cart into an **Order**, completing **C3**.

**Requirement C3:** when submitting an order the customer must provide event date, number of guests, delivery address, and allergy notes and dietary notes **per guest group**. No online payment.

Group decision (2026-10-28, `00-architecture.md`): guest groups are a list of `GuestGroup` (description, size, allergy notes, dietary notes) on `Order`.

**Out of scope:** the order list and detail pages (phase 7). Until then, a successful checkout returns to the menu with a confirmation message.

---

## Behaviour

`GET/POST /checkout` (login required, so a logged-out customer is sent to login and comes back with the cart intact).

The page shows the cart summary (dish, quantity, unit price, line total, estimated total) and a form:

| Field | Rule |
|---|---|
| Event date | Required, a valid date. **[Decision]** Must be after today. |
| Number of guests | Required whole number ≥ 1. |
| Delivery address | Required. |
| Guest groups (four rows: description, size, allergy notes, dietary notes) | Blank rows are ignored. A row with any content needs a description and a size ≥ 1. **[Decision]** The group sizes together may not exceed the number of guests. **[Decision]** If every row is blank, one group "All guests" with the full number of guests and no notes is stored. |

On submit:
- The cart is rebuilt with `build_cart` (current prices, unpublished items dropped) and every line is checked again with `check_quantity`.
- An empty cart redirects to the cart page with a message.
- On errors the form is shown again with the entered values.
- On success the order is saved with status *submitted* and payment status *not paid*. Each `OrderItem` copies the dish's name and current price. The cart is emptied.

The cart page gets a "Go to checkout" button in place of the "coming soon" note.

---

## Implementation

**Model: `app/models/services.py`.** `place_order(customer_id, cart, event_date, number_of_guests, delivery_address, guest_groups)` → `(order, errors)`. Takes parsed values (`date`/`int`, or `None` when the input couldn't be parsed), applies every rule above and saves the order in one `repos.orders.add()` call.

**Controller: `app/controllers/orders.py`** (new blueprint `orders`). Parses the form (date, ints, guest group rows), calls `place_order`, and clears `session["cart"]` on success through `cart.clear()` so only `cart.py` touches the session format.

**Views:** `orders/checkout.html`; checkout button in `cart/index.html`; guest group table styles.

## Tests (`tests/test_checkout.py`)

- Logged out → redirect to login with `next=/checkout`.
- Empty cart → redirect to the cart.
- Valid checkout saves the order with items, guest groups, price snapshot, statuses, and clears the cart.
- Blank guest group rows are ignored; no rows gives one "All guests" group.
- Errors: missing/invalid/past date, guests < 1, missing address, incomplete group row, group sizes above the number of guests, quantity below minimum. The order isn't saved and the cart is kept.
- Changing a dish's price after the order doesn't change the order.

## Verification

1. `pytest`
2. Seeded server: add dishes, check out as Kari with two guest groups, then check the database through the admin pages in phase 9 (or the tests).
