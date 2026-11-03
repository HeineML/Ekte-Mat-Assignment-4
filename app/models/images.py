"""Image files for food items (A2), stored in config UPLOAD_FOLDER under random names.

Food items only store the filename. Controllers pass in werkzeug FileStorage objects and never
touch the file system themselves.
"""
import os
import uuid

from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def is_allowed(file):
    """True if the upload looks like a PNG, JPEG, GIF or WebP picture."""
    return _extension(file.filename or "") in ALLOWED_EXTENSIONS and (file.mimetype or "").startswith("image/")


def save_image(file):
    """Save the upload under a random name and return that filename."""
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{_extension(file.filename)}"
    file.save(os.path.join(folder, filename))
    return filename


def delete_image(filename):
    """Delete a stored image. Missing files are ignored."""
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    if os.path.exists(path):
        os.remove(path)
