# 08 – Admin Food Items

**Status:** implemented 2026-11-03. Written and implemented in one session at the user's request; the group has **not yet reviewed** this plan. Decisions marked **[Decision]** are open for the group to change.

## Context

The customer side (C1–C4) works with seeded food items. Phase 8 starts the admin panel with **A1**.

**Requirement A1:** administrators must be able to add, edit and remove food items. A food item has at least name, description, price in NOK, minimum order quantity, event categories, allergens, dietary labels and published/unpublished status. §6 also lists "Publish/unpublish food items". Every admin route requires the admin role (§8).

**Out of scope:** images (phase 11, A2). Editing an item keeps its current image.

---

## Behaviour

All routes use `admin_required` (logged out → login; customer → 403).

| Route | Does |
|---|---|
| `GET /admin/food` | Every food item, published or not: name, price, minimum, categories, published status, and buttons for publish/unpublish, edit and delete. |
| `GET/POST /admin/food/new` | Empty form; on success the item is saved and the admin returns to the list. |
| `GET/POST /admin/food/<id>/edit` | The same form, filled in. |
| `POST /admin/food/<id>/delete` | Deletes after a browser confirm dialog. Old orders keep the dish's name and price (the schema sets `food_item_id` to NULL). |
| `POST /admin/food/<id>/toggle-published` | Switches published ↔ unpublished. |

Unknown ids give 404.

Form fields and rules:

| Field | Rule |
|---|---|
| Name | Required. |
| Description | **[Decision]** Required, because the menu card always shows it (C1). |
| Price (NOK) | Whole number ≥ 0. |
| Minimum order quantity | Whole number ≥ 1. |
| Event categories | Checkboxes for the existing categories. **[Decision]** At least one is required, because the menu is grouped by event and an item without a category would never be shown. |
| Allergens, dietary labels | Comma-separated text, for example `gluten, milk`. Blank entries and duplicates are dropped. |
| Published | Checkbox. |

Errors show the form again with the entered values. The nav shows an "Admin" section (Food, and later Orders and Questions) to admins. After login, admins land on the food list until phase 9 adds the order list.

Managing the event categories themselves isn't in the requirements, so the five seeded categories are fixed.

---

## Implementation

- **Model, `services.py`:** `save_food_item(item, *, name, description, price_nok, minimum_quantity, category_ids, allergens, dietary_labels, published)` → `(item, errors)`. `item` is `None` for a new one. Parsed ints arrive as `None` when the input wasn't a number. `parse_list(text)` splits comma-separated text.
- **Controller, `app/controllers/admin_food.py`:** blueprint `admin_food`, prefix `/admin/food`.
- **Views:** `admin/food_list.html`, `admin/food_form.html`, admin links in `base.html`.

## Tests (`tests/test_admin_food.py`)

- Every route: logged out → login redirect; customer → 403.
- List shows published and unpublished items.
- Create a valid item; the menu shows it when published.
- Validation errors (name, description, price, minimum, categories) don't save anything.
- Edit changes fields and categories.
- Toggle publishes and unpublishes.
- Delete removes the item and an existing order keeps the item's name and price.
- Unknown id → 404.

## Verification

1. `pytest`
2. Seeded server, as admin: create a dish, publish it, see it on the menu, edit the price, unpublish, delete.
