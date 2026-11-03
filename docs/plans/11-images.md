# 11 – Images

**Status:** done (2026-11-03). Written and implemented in one session at the user's request, one phase and one commit at a time, and **agreed by the group on 2026-11-03 after implementation**. The decisions marked **[Decision]** were accepted as written.

## Context

Food items have an `image` field (phase 2) and the menu card shows a placeholder when it's empty (phase 3), but admins can't add images yet. Phase 11 adds **A2**.

**Requirement A2:** administrators must be able to provide an image for a food item, either by uploading a picture or by writing an instruction for an AI image service. The administrator should be able to preview the image before saving it. A simple upload/placeholder implementation without an external AI API is acceptable for the first version.

**[Decision]** Upload only. No AI service is used, so no API key is needed (§2, §8).

---

## Behaviour

On the food item form (`/admin/food/new` and `/admin/food/<id>/edit`):
- A file field "Picture" (accepts images). As soon as a file is chosen, the browser shows a **preview** next to the field, before the form is saved. The preview uses `URL.createObjectURL` in a small script, `app/static/js/image-preview.js`; nothing is uploaded until "Save".
- When editing, the current picture (or the placeholder) is shown; choosing a new file replaces it on save.
- A checkbox "Remove the current picture" sets the item back to the placeholder.
- Allowed types: PNG, JPEG, GIF and WebP (by extension and the browser's content type). **[Decision]** At most 5 MB per upload (`MAX_CONTENT_LENGTH`); larger uploads get an error message instead of a crash.
- Files are saved under `app/static/uploads/` with a random name (`<uuid>.<ext>`), so user-supplied filenames are never used on disk. The folder is gitignored.
- When an image is replaced or removed, or the food item is deleted, the old file is deleted.
- If the form has other errors, nothing is saved and the file must be chosen again (browsers don't keep file fields).

The admin food list shows a small thumbnail. The customer menu shows the uploaded picture, or the placeholder.

## Implementation

- **Model, `app/models/images.py`** (file storage for images; the rest of the app only passes `FileStorage` objects and filenames): `is_allowed(file)`, `save_image(file)` → filename, `delete_image(filename)`.
- **`services.save_food_item`** gets `image_file=None, remove_image=False`; it validates the type together with the other fields and saves or deletes files only when everything is valid. New `delete_food_item(item)` deletes the item and its file.
- **Config:** `UPLOAD_FOLDER` (default `app/static/uploads`, a `tmp_path` folder in tests) and `MAX_CONTENT_LENGTH`.
- **Controller:** `admin_food.py` passes `request.files["image"]` and the remove checkbox. A 413 handler in `app/__init__.py` flashes "The picture is too large" and returns to the form.
- **Views:** `admin/food_form.html` (multipart form, file input, preview, remove checkbox), thumbnail in `admin/food_list.html`, `{% block scripts %}` in `base.html`.

## Tests (`tests/test_images.py`)

- Creating an item with a PNG saves the file under a random name and stores the filename; the menu shows `/static/uploads/<name>`.
- A `.txt` file or a non-image content type is rejected and nothing is saved.
- Replacing deletes the old file; "remove" deletes it and clears the field; deleting the item deletes the file.
- Editing without choosing a file keeps the current image.
- A file larger than the limit gives the "too large" message.
- The form contains the preview script and element.

## Verification

1. `pytest`
2. Seeded server as admin: edit "Cream cake", choose a picture, see the preview before saving, save, see it on the menu; remove it again.
