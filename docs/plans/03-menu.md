# 03 – Customer Menu

**Status:** done (2026-10-28). Agreed in Plan mode the same day. Small deviation: `?event=abc` is parsed by hand, because `request.args.get(type=int)` would silently turn it into "all events" instead of a 404. The `food_card` macro also accepts a `{% call %}` block, so phase 4 can add a cart form to it.

## Context

Phases 1–2 delivered an app that runs and a complete model and storage layer with seeded synthetic data, but the browser still only shows a placeholder home page. Phase 3 adds the first real customer feature: **C1, menu by event**. Customers browse published food items grouped by event category, and can narrow the menu to a single event. This is also the first phase that exercises the full MVC path (controller → `get_repos()` → view), so it sets the pattern later phases copy.

**Requirement C1** (`docs/requirements.md`):
- Browse food items grouped by event category.
- Each item shows its picture, name, description, price in NOK, minimum order quantity, allergens and dietary labels.
- Only published items are visible.

**Out of scope:**
- Add-to-cart buttons (phase 4).
- Real images. Items have none until phase 11, so a placeholder picture is shown.

---

## Behaviour

| URL | Shows |
|---|---|
| `/` and `/menu` | A row of event tabs ("All events", Birthday, Christmas party, Confirmation, Conference, Wedding), then one section per event category containing that category's published items. Categories with no published items are skipped. An item in several categories appears in each of their sections, so each section is complete on its own. |
| `/menu?event=<id>` | The same tabs with that event highlighted, and only that category's published items. |
| `/menu?event=999` (unknown) or `?event=abc` | 404. |

If nothing is published at all, the page shows a friendly empty message.

Each food card shows:
- the picture (`static/uploads/<image>` if set, otherwise `static/img/placeholder.svg`)
- the name and description
- the price, e.g. "650 kr", with thousands separated by a space, e.g. "1 250 kr"
- "Minimum order: 10"
- "Allergens: milk, gluten", or "No listed allergens"
- dietary labels as small badges (vegan, gluten-free, …)

---

## Implementation

**Model: `app/models/services.py` (new).** This is where domain rules start, as `00-architecture.md` planned.
- `menu_by_event(category_id=None)` returns a list of `(EventCategory, [FoodItem])` pairs, using only `get_repos().food.list_categories()` and `list_published(category_id)`. It skips empty categories and returns `None` if `category_id` doesn't exist.
- Keeping the grouping in the model makes it testable without HTTP and keeps the controller thin.

**Controller: `app/controllers/menu.py` (replace the stub).**
- `@bp.route("/")` and `@bp.route("/menu")` → `index()`.
- Reads `request.args.get("event", type=int)`. Flask returns `None` for `abc` as well as for a missing value, so a present but invalid value is treated as "unknown" and gives a 404.
- Calls `menu_by_event`; `abort(404)` on `None`.
- Renders `menu/index.html` with `categories` (for the tabs), `sections` and `selected_id`.

**Views:**
- `app/views/menu/index.html`: tabs, sections and empty state; replaces the stub.
- `app/views/menu/_food_card.html`: a `food_card(item)` Jinja macro, so the cart (phase 4) and admin pages can reuse the same card.
- `app/views/base.html`: no change is needed; the Menu link already exists.

**Shared bits:**
- Register a `nok` Jinja filter in `app/__init__.py` (`650 → "650 kr"`, `1250 → "1 250 kr"`).
- `app/static/img/placeholder.svg`: a simple, neutral plate icon (inline SVG file, no external assets).
- `app/static/css/style.css`: tabs, a responsive card grid that drops to one column at phone width, and badges.

**Docs:**
- `docs/plans/03-menu.md`: this plan.
- `CLAUDE.md`: one line noting `services.py` exists and that `nok` and the `food_card` macro are reusable.

---

## Tests (`tests/test_menu.py`, new)

A small fixture adds two categories and three items (one unpublished, one in both categories) through `repos`. No seed is needed.
- `menu_by_event()` groups correctly, skips empty categories, and excludes unpublished items.
- `menu_by_event(unknown_id)` returns `None`.
- `GET /` and `GET /menu` return 200, show both category headings and the published item names, and **don't** show the unpublished item.
- `GET /menu?event=<id>` shows only that category's items.
- `GET /menu?event=999` and `?event=abc` return 404.
- A card shows the price "650 kr", the minimum quantity, the allergens and the dietary labels.
- An empty database shows the empty-menu message.
- The `nok` filter formats `1250` as `"1 250 kr"`.
- The existing 18 tests stay green. `test_home_page_renders` still passes, because the header contains "Ekte Mat Online".

---

## Verification

1. `pytest`: all tests pass.
2. `flask --app app seed`, then `flask --app app run --debug`. At http://127.0.0.1:5000, check that:
   - the five event tabs and their sections show the seeded dishes;
   - "Sushi platter" (unpublished) is **not** shown;
   - clicking "Christmas party" shows only the pork rib, pinnekjøtt and rice cream;
   - narrowing the browser window to phone width makes the cards stack into one column.
3. `git grep sqlite -- app/controllers app/views` still finds nothing.
