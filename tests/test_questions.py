from datetime import date, timedelta

import pytest

from app.models.entities import Order, OrderItem, Question
from tests.conftest import login


@pytest.fixture
def orders(repos, users):
    def add(customer):
        return repos.orders.add(Order(customer_id=customer.id, event_date=date.today() + timedelta(days=10),
                                      number_of_guests=10, delivery_address="Testveien 1",
                                      items=[OrderItem(None, "Cake", 2, 650)]))

    return {"kari": add(users["kari"]), "ola": add(users["ola"])}


@pytest.fixture
def ola_question(repos, users, orders):
    return repos.questions.add(Question(order_id=orders["ola"].id, customer_id=users["ola"].id,
                                        question="Can you deliver at 17:00?"))


def ask(client, order, text):
    return client.post(f"/orders/{order.id}/questions", data={"question": text})


# Customer (C5)

def test_customer_asks_question(client, orders, repos):
    login(client, "kari@test.test")
    response = ask(client, orders["kari"], "  Are the cakes nut-free?  ")
    assert response.headers["Location"] == f"/orders/{orders['kari'].id}#questions"
    [question] = repos.questions.list_for_order(orders["kari"].id)
    assert question.question == "Are the cakes nut-free?"
    html = client.get(f"/orders/{orders['kari'].id}").get_data(as_text=True)
    assert "Are the cakes nut-free?" in html and "Waiting for an answer" in html


def test_cannot_ask_on_other_customers_order(client, orders, repos):
    login(client, "kari@test.test")
    assert ask(client, orders["ola"], "Hello?").status_code == 404
    assert repos.questions.list_all() == []


def test_ask_requires_login(client, orders):
    assert ask(client, orders["kari"], "Hello?").status_code == 302


@pytest.mark.parametrize("text, message", [("   ", "Please write a question."),
                                           ("x" * 2001, "at most 2000 characters")])
def test_invalid_question_is_rejected(client, orders, repos, text, message):
    login(client, "kari@test.test")
    response = ask(client, orders["kari"], text)
    assert message in client.get(response.headers["Location"]).get_data(as_text=True)
    assert repos.questions.list_all() == []


def test_customer_reads_answer(client, ola_question, orders, repos):
    repos.questions.answer(ola_question.id, "Yes, 17:00 works.")
    login(client, "ola@test.test")
    html = client.get(f"/orders/{orders['ola'].id}").get_data(as_text=True)
    assert "Can you deliver at 17:00?" in html and "Yes, 17:00 works." in html
    assert "Waiting for an answer" not in html


def test_customer_does_not_see_other_orders_questions(client, ola_question, orders):
    login(client, "kari@test.test")
    assert "Can you deliver at 17:00?" not in client.get(f"/orders/{orders['kari'].id}").get_data(as_text=True)


# Admin (A4)

@pytest.mark.parametrize("method, url", [("get", "/admin/questions"), ("post", "/admin/questions/1/answer")])
def test_admin_routes_require_admin(client, ola_question, method, url):
    assert getattr(client, method)(url).status_code == 302
    login(client, "ola@test.test")
    assert getattr(client, method)(url).status_code == 403


def test_admin_list_shows_question_order_and_customer(client, users, ola_question, orders):
    login(client, "admin@test.test")
    html = client.get("/admin/questions").get_data(as_text=True)
    assert "Can you deliver at 17:00?" in html
    assert f'href="/admin/orders/{orders["ola"].id}"' in html
    assert "Ola" in html


def test_admin_unanswered_filter(client, users, ola_question, orders, repos):
    answered = repos.questions.add(Question(order_id=orders["kari"].id, customer_id=users["kari"].id,
                                            question="Old question"))
    repos.questions.answer(answered.id, "Old answer")
    login(client, "admin@test.test")
    html = client.get("/admin/questions?unanswered=1").get_data(as_text=True)
    assert "Can you deliver at 17:00?" in html and "Old question" not in html


def test_admin_answers_and_can_update(client, users, ola_question, repos):
    login(client, "admin@test.test")
    response = client.post(f"/admin/questions/{ola_question.id}/answer",
                           data={"answer": "Yes.", "next": "/admin/questions?unanswered=1"})
    assert response.headers["Location"] == "/admin/questions?unanswered=1"
    saved = repos.questions.get(ola_question.id)
    assert saved.answer == "Yes." and saved.answered_at is not None

    client.post(f"/admin/questions/{ola_question.id}/answer", data={"answer": "Yes, at 17:00."})
    assert repos.questions.get(ola_question.id).answer == "Yes, at 17:00."


def test_admin_empty_answer_is_rejected(client, users, ola_question, repos):
    login(client, "admin@test.test")
    response = client.post(f"/admin/questions/{ola_question.id}/answer", data={"answer": " "})
    assert "Please write an answer." in client.get(response.headers["Location"]).get_data(as_text=True)
    assert repos.questions.get(ola_question.id).answer is None


def test_admin_answer_unknown_question_is_404(client, users):
    login(client, "admin@test.test")
    assert client.post("/admin/questions/999/answer", data={"answer": "Hi"}).status_code == 404


def test_admin_order_page_lists_its_questions(client, users, ola_question, orders):
    login(client, "admin@test.test")
    html = client.get(f"/admin/orders/{orders['ola'].id}").get_data(as_text=True)
    assert "Can you deliver at 17:00?" in html
    assert f'action="/admin/questions/{ola_question.id}/answer"' in html
