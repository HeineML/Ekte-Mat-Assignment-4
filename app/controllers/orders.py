"""Customer orders: checkout (C3)."""
from datetime import date, timedelta

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.controllers.cart import clear_cart, raw_cart
from app.controllers.decorators import login_required
from app.models.entities import GuestGroup
from app.models.services import build_cart, place_order

bp = Blueprint("orders", __name__)

GUEST_GROUP_ROWS = 4
GROUP_FIELDS = ("description", "size", "allergy_notes", "dietary_notes")


def _parse_int(value):
    try:
        return int(value)
    except ValueError:
        return None


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _group_rows():
    """The guest group rows as entered, padded to GUEST_GROUP_ROWS so the form can show them again."""
    columns = [request.form.getlist(f"group_{name}") for name in GROUP_FIELDS]
    rows = []
    for i in range(max(GUEST_GROUP_ROWS, *(len(c) for c in columns))):
        rows.append({name: (column[i].strip() if i < len(column) else "")
                     for name, column in zip(GROUP_FIELDS, columns)})
    return rows


def _guest_groups(rows):
    """GuestGroup entities for the rows that aren't blank. An invalid size becomes None."""
    return [GuestGroup(description=row["description"], size=_parse_int(row["size"]),
                       allergy_notes=row["allergy_notes"], dietary_notes=row["dietary_notes"])
            for row in rows if any(row.values())]


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = build_cart(raw_cart())
    for name in cart.removed:
        flash(f"{name} is no longer on the menu and was left out of your order.", "info")
    if not cart.lines:
        flash("Your cart is empty. Add some dishes before checking out.", "info")
        return redirect(url_for("cart.index"))

    rows = _group_rows()
    if request.method == "POST":
        order, errors = place_order(
            customer_id=g.user.id,
            cart=cart,
            event_date=_parse_date(request.form.get("event_date", "")),
            number_of_guests=_parse_int(request.form.get("number_of_guests", "")),
            delivery_address=request.form.get("delivery_address", ""),
            guest_groups=_guest_groups(rows),
        )
        if order:
            clear_cart()
            flash(f"Thank you! Your order #{order.id} has been submitted.", "success")
            return redirect(url_for("menu.index"))
        for error in errors:
            flash(error, "error")

    return render_template("orders/checkout.html", cart=cart, form=request.form, rows=rows,
                           min_date=date.today() + timedelta(days=1))
