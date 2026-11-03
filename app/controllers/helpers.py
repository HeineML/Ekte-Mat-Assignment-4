"""Small helpers shared by several controllers."""
from flask import request


def safe_next(target, default):
    """Only redirect to local paths, never to another site."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return default


def form_int(name):
    """The form field as an int, or None if it is missing or not a whole number."""
    try:
        return int(request.form[name])
    except (KeyError, ValueError):
        return None
