"""Tests for the repository interface. They only use get_repos() and entities, so they can be reused
for another storage backend."""
from datetime import date

import pytest

from app.models.entities import (
    EventCategory, FoodItem, GuestGroup, Order, OrderItem, OrderStatus, PaymentStatus, Question, Role, User,
)
from app.models.repositories import EmailAlreadyRegistered


def make_user(repos, email="kari@example.test", role=Role.CUSTOMER):
    return repos.users.add(User(name="Test User", email=email, password_hash="hash", role=role))


def make_food(repos, name="Cream cake", published=True, categories=(), price=650, minimum=1):
    return repos.food.add(FoodItem(
        name=name, description="Test item", price_nok=price, minimum_quantity=minimum,
        published=published, allergens=["milk", "gluten"], dietary_labels=["vegetarian"],
        event_categories=list(categories),
    ))


def make_order(repos, customer, food, quantity=10, event_date=date(2026, 12, 24), **kwargs):
    return repos.orders.add(Order(
        customer_id=customer.id, event_date=event_date, number_of_guests=20,
        delivery_address="Testveien 1, 5000 Bergen",
        items=[OrderItem(food_item_id=food.id, food_name=food.name, quantity=quantity,
                         unit_price_nok=food.price_nok)],
        guest_groups=[GuestGroup("Adults", 18), GuestGroup("Children", 2, allergy_notes="Nuts")],
        **kwargs,
    ))


# Users

def test_user_roundtrip_and_email_lookup_ignores_case(repos):
    user = make_user(repos, role=Role.ADMIN)
    assert user.id is not None
    found = repos.users.get_by_email("KARI@example.TEST")
    assert found == user
    assert found.is_admin
    assert repos.users.get(user.id) == user
    assert repos.users.get_by_email("nobody@example.test") is None


def test_duplicate_email_is_rejected(repos):
    make_user(repos)
    with pytest.raises(EmailAlreadyRegistered):
        make_user(repos, email="Kari@Example.test")


# Food items

def test_food_item_roundtrip_keeps_lists_and_categories(repos):
    wedding = repos.food.add_category(EventCategory("Wedding"))
    birthday = repos.food.add_category(EventCategory("Birthday"))
    item = make_food(repos, categories=[wedding, birthday])

    loaded = repos.food.get(item.id)
    assert loaded.allergens == ["milk", "gluten"]
    assert loaded.dietary_labels == ["vegetarian"]
    assert [c.name for c in loaded.event_categories] == ["Birthday", "Wedding"]
    assert [c.name for c in repos.food.list_categories()] == ["Birthday", "Wedding"]


def test_list_published_hides_unpublished_and_filters_by_category(repos):
    wedding = repos.food.add_category(EventCategory("Wedding"))
    birthday = repos.food.add_category(EventCategory("Birthday"))
    make_food(repos, "Cake", categories=[wedding, birthday])
    make_food(repos, "Salmon", categories=[wedding])
    make_food(repos, "Draft", published=False, categories=[wedding])

    assert [f.name for f in repos.food.list_published()] == ["Cake", "Salmon"]
    assert [f.name for f in repos.food.list_published(category_id=birthday.id)] == ["Cake"]
    assert len(repos.food.list_all()) == 3


def test_update_food_item(repos):
    wedding = repos.food.add_category(EventCategory("Wedding"))
    conference = repos.food.add_category(EventCategory("Conference"))
    item = make_food(repos, categories=[wedding])

    item.price_nok = 700
    item.published = False
    item.event_categories = [conference]
    repos.food.update(item)

    loaded = repos.food.get(item.id)
    assert loaded.price_nok == 700
    assert not loaded.published
    assert [c.name for c in loaded.event_categories] == ["Conference"]


def test_deleting_food_item_keeps_old_order_items(repos):
    customer = make_user(repos)
    item = make_food(repos, price=650)
    order = make_order(repos, customer, item, quantity=2)

    repos.food.delete(item.id)

    assert repos.food.get(item.id) is None
    line = repos.orders.get(order.id).items[0]
    assert line.food_item_id is None
    assert (line.food_name, line.unit_price_nok, line.quantity) == ("Cream cake", 650, 2)


# Orders

def test_order_roundtrip_with_items_guest_groups_and_total(repos):
    customer = make_user(repos)
    item = make_food(repos, price=650)
    order = make_order(repos, customer, item, quantity=3)

    loaded = repos.orders.get(order.id)
    assert loaded.event_date == date(2026, 12, 24)
    assert loaded.status == OrderStatus.SUBMITTED
    assert loaded.payment_status == PaymentStatus.NOT_PAID
    assert loaded.created_at is not None
    assert loaded.total == 3 * 650
    assert [g.description for g in loaded.guest_groups] == ["Adults", "Children"]
    assert loaded.guest_groups[1].allergy_notes == "Nuts"


def test_order_price_is_a_snapshot(repos):
    customer = make_user(repos)
    item = make_food(repos, price=650)
    order = make_order(repos, customer, item)

    item.price_nok = 999
    repos.food.update(item)

    assert repos.orders.get(order.id).items[0].unit_price_nok == 650


def test_customer_cannot_get_another_customers_order(repos):
    kari = make_user(repos, "kari@example.test")
    ola = make_user(repos, "ola@example.test")
    order = make_order(repos, kari, make_food(repos))

    assert repos.orders.get_for_customer(order.id, kari.id) is not None
    assert repos.orders.get_for_customer(order.id, ola.id) is None
    assert repos.orders.list_for_customer(ola.id) == []
    assert [o.id for o in repos.orders.list_for_customer(kari.id)] == [order.id]


def test_list_all_filters_by_status_and_event_date(repos):
    customer = make_user(repos)
    item = make_food(repos)
    christmas = make_order(repos, customer, item, event_date=date(2026, 12, 24))
    summer = make_order(repos, customer, item, event_date=date(2026, 6, 20), status=OrderStatus.APPROVED)

    assert len(repos.orders.list_all()) == 2
    assert [o.id for o in repos.orders.list_all(status=OrderStatus.APPROVED)] == [summer.id]
    assert [o.id for o in repos.orders.list_all(event_date=date(2026, 12, 24))] == [christmas.id]
    assert repos.orders.list_all(status=OrderStatus.APPROVED, event_date=date(2026, 12, 24)) == []


def test_update_status_and_payment_status(repos):
    order = make_order(repos, make_user(repos), make_food(repos))

    repos.orders.update_status(order.id, OrderStatus.IN_PREPARATION)
    repos.orders.update_payment_status(order.id, PaymentStatus.INVOICED)

    loaded = repos.orders.get(order.id)
    assert loaded.status == OrderStatus.IN_PREPARATION
    assert loaded.payment_status == PaymentStatus.INVOICED


def test_invalid_status_is_rejected(repos):
    order = make_order(repos, make_user(repos), make_food(repos))
    with pytest.raises(ValueError):
        repos.orders.update_status(order.id, "lost")


# Questions

def test_questions_add_list_and_answer(repos):
    customer = make_user(repos)
    order = make_order(repos, customer, make_food(repos))
    question = repos.questions.add(Question(order_id=order.id, customer_id=customer.id,
                                            question="Can you deliver at 17:00?"))

    assert [q.id for q in repos.questions.list_for_order(order.id)] == [question.id]
    assert [q.id for q in repos.questions.list_all(unanswered_only=True)] == [question.id]
    assert not repos.questions.get(question.id).is_answered

    repos.questions.answer(question.id, "Yes.")

    answered = repos.questions.get(question.id)
    assert answered.answer == "Yes."
    assert answered.answered_at is not None
    assert repos.questions.list_all(unanswered_only=True) == []
    assert len(repos.questions.list_all()) == 1
