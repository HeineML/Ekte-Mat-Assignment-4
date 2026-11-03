"""Register, log in and log out (C3, §8). The logged-in user's id is kept in session["user_id"]."""
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from app.controllers.helpers import safe_next
from app.models import get_repos
from app.models.services import authenticate, register_customer

bp = Blueprint("auth", __name__)


@bp.before_app_request
def load_user():
    user_id = session.get("user_id")
    g.user = get_repos().users.get(user_id) if user_id is not None else None


def _log_in(user):
    # A fresh session on login prevents session fixation; the cart is carried over.
    cart = session.get("cart")
    session.clear()
    if cart:
        session["cart"] = cart
    session["user_id"] = user.id


def _home_for(user):
    return url_for("menu.index")


@bp.route("/register", methods=["GET", "POST"])
def register():
    next_url = request.values.get("next", "")
    if request.method == "POST":
        user, errors = register_customer(request.form.get("name", ""), request.form.get("email", ""),
                                         request.form.get("password", ""), request.form.get("password2", ""))
        if user:
            _log_in(user)
            flash(f"Welcome, {user.name}! Your account has been created.", "success")
            return redirect(safe_next(next_url, url_for("menu.index")))
        for error in errors:
            flash(error, "error")
    return render_template("auth/register.html", next_url=next_url, form=request.form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.values.get("next", "")
    if request.method == "POST":
        user = authenticate(request.form.get("email", ""), request.form.get("password", ""))
        if user:
            _log_in(user)
            flash(f"Logged in as {user.name}.", "success")
            return redirect(safe_next(next_url, _home_for(user)))
        flash("Wrong email or password.", "error")
    return render_template("auth/login.html", next_url=next_url, form=request.form)


@bp.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("menu.index"))
