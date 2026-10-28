"""Customer menu (C1). Currently a stub home page; the real menu comes in phase 3."""
from flask import Blueprint, render_template

bp = Blueprint("menu", __name__)


@bp.route("/")
def index():
    return render_template("menu/index.html")
