"""Admin: food items (A1) and their pictures (A2). Every route requires the admin role."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.controllers.decorators import admin_required
from app.controllers.helpers import form_int
from app.models import get_repos
from app.models.services import delete_food_item, save_food_item

bp = Blueprint("admin_food", __name__, url_prefix="/admin/food")


def _item_or_404(item_id):
    item = get_repos().food.get(item_id)
    if item is None:
        abort(404)
    return item


def _form(item):
    """Show the form for a new (item=None) or existing food item, and save it on POST."""
    if request.method == "POST":
        upload = request.files.get("image")
        saved, errors = save_food_item(
            item,
            name=request.form.get("name", ""),
            description=request.form.get("description", ""),
            price_nok=form_int("price_nok"),
            minimum_quantity=form_int("minimum_quantity"),
            category_ids=[int(c) for c in request.form.getlist("category_ids") if c.isdigit()],
            allergens=request.form.get("allergens", ""),
            dietary_labels=request.form.get("dietary_labels", ""),
            published="published" in request.form,
            image_file=upload if upload and upload.filename else None,
            remove_image="remove_image" in request.form,
        )
        if saved:
            flash(f"Saved {saved.name}.", "success")
            return redirect(url_for("admin_food.index"))
        for error in errors:
            flash(error, "error")
        values = request.form
        selected = {int(c) for c in request.form.getlist("category_ids") if c.isdigit()}
    elif item:
        values = {"name": item.name, "description": item.description, "price_nok": item.price_nok,
                  "minimum_quantity": item.minimum_quantity, "allergens": ", ".join(item.allergens),
                  "dietary_labels": ", ".join(item.dietary_labels), "published": item.published}
        selected = {c.id for c in item.event_categories}
    else:
        values, selected = {"minimum_quantity": 1}, set()

    return render_template("admin/food_form.html", item=item, values=values, selected=selected,
                           categories=get_repos().food.list_categories())


@bp.route("")
@admin_required
def index():
    return render_template("admin/food_list.html", items=get_repos().food.list_all())


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def new():
    return _form(None)


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(item_id):
    return _form(_item_or_404(item_id))


@bp.post("/<int:item_id>/toggle-published")
@admin_required
def toggle_published(item_id):
    item = _item_or_404(item_id)
    item.published = not item.published
    get_repos().food.update(item)
    flash(f"{item.name} is now {'published' if item.published else 'unpublished'}.", "success")
    return redirect(url_for("admin_food.index"))


@bp.post("/<int:item_id>/delete")
@admin_required
def delete(item_id):
    item = _item_or_404(item_id)
    delete_food_item(item)
    flash(f"Deleted {item.name}. Existing orders keep its name and price.", "success")
    return redirect(url_for("admin_food.index"))
