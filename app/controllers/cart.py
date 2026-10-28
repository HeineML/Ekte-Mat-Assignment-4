"""Shopping cart (C2). The cart lives in the session as {food_item_id: quantity} until checkout."""
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.models import get_repos
from app.models.services import build_cart, check_quantity

bp = Blueprint("cart", __name__, url_prefix="/cart")


def _load():
    # Session data is JSON, so keys are stored as strings.
    return {int(item_id): qty for item_id, qty in session.get("cart", {}).items()}


def _save(raw):
    session["cart"] = {str(item_id): qty for item_id, qty in raw.items()}
    session.modified = True


def _form_int(name):
    try:
        return int(request.form[name])
    except (KeyError, ValueError):
        return None


def _published_item_or_404():
    item_id = _form_int("food_item_id")
    item = get_repos().food.get(item_id) if item_id is not None else None
    if item is None or not item.published:
        abort(404)
    return item


def _safe_next():
    """Only redirect to local paths, never to another site."""
    target = request.form.get("next", "")
    if target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("menu.index")


@bp.app_context_processor
def inject_cart_count():
    return {"cart_count": len(session.get("cart", {}))}


@bp.route("")
def index():
    raw = _load()
    cart = build_cart(raw)
    if len(cart.lines) != len(raw):
        _save({line.item.id: line.quantity for line in cart.lines})
    for name in cart.removed:
        flash(f"{name} is no longer on the menu and was removed from your cart.", "info")
    return render_template("cart/index.html", cart=cart)


@bp.post("/add")
def add():
    item = _published_item_or_404()
    quantity = _form_int("quantity")
    if quantity is None or quantity < 1:
        flash("Please enter a quantity of at least 1.", "error")
        return redirect(_safe_next())

    raw = _load()
    new_quantity = raw.get(item.id, 0) + quantity
    error = check_quantity(item, new_quantity)
    if error:
        flash(error, "error")
    else:
        raw[item.id] = new_quantity
        _save(raw)
        flash(f"Added {quantity} × {item.name} to your cart.", "success")
    return redirect(_safe_next())


@bp.post("/update")
def update():
    raw = _load()
    item_id = _form_int("food_item_id")
    if item_id not in raw:
        abort(404)
    item = _published_item_or_404()

    quantity = _form_int("quantity")
    if quantity is None or quantity < 1:
        flash("Please enter a whole number. Use Remove to take an item out of the cart.", "error")
    elif error := check_quantity(item, quantity):
        flash(error, "error")
    else:
        raw[item.id] = quantity
        _save(raw)
        flash(f"Updated {item.name} to {quantity}.", "success")
    return redirect(url_for("cart.index"))


@bp.post("/remove")
def remove():
    raw = _load()
    item_id = _form_int("food_item_id")
    if raw.pop(item_id, None) is not None:
        _save(raw)
        flash("Item removed from your cart.", "success")
    return redirect(url_for("cart.index"))
