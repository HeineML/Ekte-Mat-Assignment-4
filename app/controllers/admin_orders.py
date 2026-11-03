"""Admin: orders (A3). Every route requires the admin role."""
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.controllers.decorators import admin_required
from app.models import get_repos
from app.models.entities import OrderStatus, PaymentStatus
from app.models.services import customers_by_id

bp = Blueprint("admin_orders", __name__, url_prefix="/admin/orders")


def _order_or_404(order_id):
    order = get_repos().orders.get(order_id)
    if order is None:
        abort(404)
    return order


def _enum_or_400(enum, value):
    try:
        return enum(value)
    except ValueError:
        abort(400)


@bp.route("")
@admin_required
def index():
    status, event_date = None, None
    raw_status = request.args.get("status", "")
    raw_date = request.args.get("event_date", "")
    if raw_status:
        try:
            status = OrderStatus(raw_status)
        except ValueError:
            flash(f"Unknown status {raw_status!r}; showing all statuses.", "error")
    if raw_date:
        try:
            event_date = date.fromisoformat(raw_date)
        except ValueError:
            flash(f"{raw_date!r} is not a valid date; showing all dates.", "error")

    orders = get_repos().orders.list_all(status=status, event_date=event_date)
    return render_template("admin/orders_list.html", orders=orders, customers=customers_by_id(orders),
                           statuses=list(OrderStatus), status=status, event_date=event_date)


@bp.route("/<int:order_id>")
@admin_required
def detail(order_id):
    order = _order_or_404(order_id)
    return render_template("admin/order_detail.html", order=order,
                           customer=get_repos().users.get(order.customer_id),
                           statuses=list(OrderStatus), payment_statuses=list(PaymentStatus))


@bp.post("/<int:order_id>/status")
@admin_required
def update_status(order_id):
    order = _order_or_404(order_id)
    status = _enum_or_400(OrderStatus, request.form.get("status", ""))
    get_repos().orders.update_status(order.id, status)
    flash(f"Order #{order.id} is now {status.label.lower()}.", "success")
    return redirect(url_for("admin_orders.detail", order_id=order.id))


@bp.post("/<int:order_id>/payment")
@admin_required
def update_payment(order_id):
    order = _order_or_404(order_id)
    payment_status = _enum_or_400(PaymentStatus, request.form.get("payment_status", ""))
    get_repos().orders.update_payment_status(order.id, payment_status)
    flash(f"Payment status of order #{order.id} is now {payment_status.label.lower()}.", "success")
    return redirect(url_for("admin_orders.detail", order_id=order.id))
