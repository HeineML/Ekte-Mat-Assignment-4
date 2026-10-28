# 04 – Shopping Cart

**Status:** done (2026-10-28). Agreed in Plan mode the same day. Deviations:
- The quantity field on menu cards uses `min="1"`, not the item's minimum, because a smaller amount can be added to a line that's already in the cart, as long as the total meets the minimum.
- Updating an item that isn't in the cart returns 404.
- Removing an item that isn't in the cart does nothing.
- Add-to-cart rows are pinned to the bottom of the card so the buttons line up.

## Context

Phase 3 delivered the customer menu (C1). Customers can now browse dishes but not choose any. Phase 4 adds **C2, shopping cart**, which is the step between browsing and checkout (phase 6).

**Requirement C2** (`docs/requirements.md`): customers must be able to add food items to the cart, change quantities, remove items and see an estimated total. The system must reject quantities below the food item's minimum order quantity.

The architecture (`00-architecture.md`) already decided that the cart lives in the **Flask session** as `{food_item_id: quantity}`, so it works without logging in. It becomes an Order at checkout.

**Out of scope:**
- Login (phase 5) and checkout (phase 6). The cart page shows a note in place of a checkout button until then.

---

## Behaviour

| Action | Rule | Result |
|---|---|---|
| **Add** (form on each menu card: a quantity field pre-filled with the item's minimum, and an "Add to cart" button) | Quantity must be a whole number ≥ 1, and the **resulting** cart quantity must be ≥ the minimum. Adding an item already in the cart adds to its quantity. | Success: flash "Added 20 × Open sandwiches", back to the same menu view. Too low: error flash "Minimum order for Open sandwiches is 20", cart unchanged. |
| **Change quantity** (number field and "Update" on each cart line) | New quantity must be ≥ the minimum. 0, negative numbers and non-numbers are rejected, and the error suggests using Remove. | Success flash, or an error flash with the old quantity kept. |
| **Remove** (button on each line) | none | Line removed. |
| **Estimated total** | sum of quantity × current price | Shown at the bottom, labelled *Estimated total*. The price is fixed when the order is placed in phase 6. |

**Edge cases:**
- Adding an item that doesn't exist or isn't published → 404.
- An item in the cart that is later unpublished or deleted is dropped from the cart the next time the cart is shown, with an info flash naming it.
- An empty cart shows "Your cart is empty" and a link to the menu.

The nav shows **"Cart (n)"**, where *n* is the number of lines in the cart, on every page.

---

## Implementation

**Model: `app/models/services.py` (extend).** Domain rules only; this file doesn't know about the session.
- `CartLine` dataclass (`item: FoodItem`, `quantity`) with `line_total`, and `Cart` (`lines`, `total`, `removed: list[str]` names of dropped items).
- `build_cart(raw: dict) -> Cart`: looks up each id with `get_repos().food.get()`, keeps only published items, and records the dropped names.
- `check_quantity(item, quantity) -> str | None`: returns an error message, or `None` if the quantity is OK. Phase 6 checkout will reuse it.

**Controller: `app/controllers/cart.py` (new blueprint `cart`).**
- Small session helpers `_load()` and `_save(raw)`. Keys are stored as strings, because the session is JSON. `session.modified` is set on every change.
- Routes:

  | Route | Does |
  |---|---|
  | `GET /cart` | `build_cart`; if anything was dropped, saves the cleaned cart and flashes the names; renders `cart/index.html` |
  | `POST /cart/add` | form: `food_item_id`, `quantity`, `next` |
  | `POST /cart/update` | form: `food_item_id`, `quantity` |
  | `POST /cart/remove` | form: `food_item_id` |

- After add, the user is redirected to `next` only if it's a local path (starts with `/` but not `//`), otherwise to the menu. This prevents an open redirect.
- `@bp.app_context_processor` provides `cart_count` to all templates, read from the session only (no database query).
- Registered in `app/__init__.py`.

**Views:**
- `app/views/menu/index.html`: passes an add-to-cart form into `food_card` through the existing `{% call %}` slot. The form has `type="number" min=minimum_quantity` as a browser hint; the server still checks.
- `app/views/cart/index.html` (new): a table with name, unit price, quantity form, line total and Remove; the estimated total; the empty state; a note that checkout comes after login.
- `app/views/base.html`: a "Cart (n)" link in the nav.
- `app/static/css/style.css`: the cart table, which scrolls sideways on phones, and the small inline forms.

**Config: `app/config.py`.** Set `SESSION_COOKIE_SAMESITE = "Lax"`. Cart actions are POST forms without CSRF tokens, and this makes browsers refuse to send the session cookie on cross-site form posts. It's a one-line safeguard; full CSRF protection isn't a requirement.

**Docs:**
- `docs/plans/04-cart.md`: this plan.
- `CLAUDE.md`: note where the cart lives (session format, `build_cart` and `check_quantity` in services).

---

## Tests (`tests/test_cart.py`, new)

A fixture adds a category, one published item (minimum 10, 100 kr) and one unpublished item.

**Services:**
- `check_quantity` returns an error below the minimum and `None` at or above it.
- `build_cart` computes line totals and the total.
- `build_cart` drops unpublished or unknown ids and lists their names in `removed`.

**Routes:**
- Adding a valid quantity puts it in the session and redirects.
- Adding below the minimum gives an error flash and leaves the cart unchanged.
- Adding twice sums the quantities. Adding a smaller amount to an existing line is accepted when the total meets the minimum.
- Adding an unpublished or nonexistent item → 404.
- Updating to a valid quantity works. Updating below the minimum, to 0, or to `"abc"` is rejected and the old quantity is kept.
- Removing works.
- `GET /cart` shows the line, the line total, the estimated total and "Cart (1)" in the nav. An empty cart shows the empty message.
- An item unpublished after it was added is dropped from the cart with a flash.
- `next=https://evil.example` redirects to the menu, not to the external site.

The existing 29 tests stay green.

---

## Verification

1. `pytest`: all tests pass.
2. `flask --app app seed`, `flask --app app run --debug`, then in the browser:
   - Add 20 open sandwiches. The nav shows "Cart (1)".
   - Try adding 5 roast beef (minimum 10). You get an error flash and the cart is unchanged.
   - On `/cart`, change sandwiches to 30. The line total and estimated total update.
   - Try 3. You get an error and the quantity stays 30.
   - Remove the line. You see the empty-cart message.
3. `git grep sqlite -- app/controllers app/views` still finds nothing.
