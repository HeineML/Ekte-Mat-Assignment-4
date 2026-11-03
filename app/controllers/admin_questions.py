"""Admin: customer questions (A4). Every route requires the admin role."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.controllers.decorators import admin_required
from app.controllers.helpers import safe_next
from app.models import get_repos
from app.models.services import answer_question, customers_by_id

bp = Blueprint("admin_questions", __name__, url_prefix="/admin/questions")


@bp.route("")
@admin_required
def index():
    unanswered_only = request.args.get("unanswered") == "1"
    questions = get_repos().questions.list_all(unanswered_only=unanswered_only)
    return render_template("admin/questions.html", questions=questions, customers=customers_by_id(questions),
                           unanswered_only=unanswered_only)


@bp.post("/<int:question_id>/answer")
@admin_required
def answer(question_id):
    question = get_repos().questions.get(question_id)
    if question is None:
        abort(404)
    errors = answer_question(question, request.form.get("answer", ""))
    for error in errors:
        flash(error, "error")
    if not errors:
        flash(f"Answer to the question on order #{question.order_id} saved.", "success")
    return redirect(safe_next(request.form.get("next", ""), url_for("admin_questions.index")))
