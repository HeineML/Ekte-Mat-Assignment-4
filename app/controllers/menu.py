"""Customer menu (C1): published food items grouped by event category, filtered by allergens and
dietary labels, and the photo credits."""
import json
import os

from flask import Blueprint, abort, current_app, render_template, request

from app.models import get_repos
from app.models.services import menu_by_event, menu_filters

bp = Blueprint("menu", __name__)


@bp.route("/")
@bp.route("/menu")
def index():
    selected_id = None
    raw_event = request.args.get("event")
    if raw_event is not None:
        try:
            selected_id = int(raw_event)
        except ValueError:
            abort(404)

    allergens, labels, without, diet = menu_filters(request.args.getlist("without"),
                                                    request.args.getlist("diet"))
    sections = menu_by_event(selected_id, exclude_allergens=without, require_labels=diet)
    if sections is None:
        abort(404)

    return render_template(
        "menu/index.html",
        categories=get_repos().food.list_categories(),
        sections=sections,
        selected_id=selected_id,
        allergens=allergens,
        labels=labels,
        without=without,
        diet=diet,
    )


@bp.route("/photo-credits")
def photo_credits():
    """Attribution for the freely licensed seed photos (required by their CC BY / CC BY-SA licences)."""
    path = os.path.join(current_app.static_folder, "img", "food", "credits.json")
    with open(path, encoding="utf-8") as f:
        credits = json.load(f)
    return render_template("menu/credits.html", credits=credits)
