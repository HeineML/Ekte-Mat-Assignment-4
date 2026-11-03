from datetime import date, timedelta

import pytest

from app.models.entities import EventCategory, FoodItem, OrderStatus, PaymentStatus
from tests.conftest import login

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


@pytest.fixture
def menu(repos):
    party = repos.food.add_category(EventCategory("Birthday"))

    def add(name, price, minimum):
        return repos.food.add(FoodItem(name=name, description="Test", price_nok=price, minimum_quantity=minimum,
                                       published=True, event_categories=[party]))

    return {"sandwich": add("Sandwich", 50, 10), "cake": add("Cake", 650, 1)}


@pytest.fixture
def customer(client, users, menu):
    """Kari, logged in, with 20 sandwiches and 2 cakes in the cart."""
    login(client, "kari@test.test")
    with client.session_transaction() as sess:
        sess["cart"] = {str(menu["sandwich"].id): 20, str(menu["cake"].id): 2}
    return users["kari"]


def checkout(client, groups=(), **fields):
    data = {"event_date": TOMORROW, "number_of_guests": "30", "delivery_address": "Testveien 1, 5000 Bergen",
            **fields}
    for name in ("description", "size", "allergy_notes", "dietary_notes"):
        data[f"group_{name}"] = [g.get(name, "") for g in groups]
    return client.post("/checkout", data=data)


def cart_in_session(client):
    with client.session_transaction() as sess:
        return sess.get("cart")


def test_checkout_requires_login(client, menu):
    response = client.get("/checkout")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/checkout"


def test_checkout_with_empty_cart_redirects_to_cart(client, users):
    login(client, "kari@test.test")
    response = client.get("/checkout")
    assert response.headers["Location"] == "/cart"


def test_checkout_page_shows_cart(client, customer):
    html = client.get("/checkout").get_data(as_text=True)
    assert "Sandwich" in html and "Cake" in html
    assert "2 300 kr" in html  # 20 × 50 + 2 × 650


def test_valid_checkout_saves_order(client, customer, repos, menu):
    groups = [{"description": "Adults", "size": "25"},
              {"description": "Children", "size": "5", "allergy_notes": "Milk", "dietary_notes": "Halal"},
              {}]
    response = checkout(client, groups)
    assert response.status_code == 302

    [order] = repos.orders.list_for_customer(customer.id)
    assert order.event_date == date.today() + timedelta(days=1)
    assert order.number_of_guests == 30
    assert order.delivery_address == "Testveien 1, 5000 Bergen"
    assert order.status == OrderStatus.SUBMITTED
    assert order.payment_status == PaymentStatus.NOT_PAID
    assert [(i.food_name, i.quantity, i.unit_price_nok) for i in order.items] == [
        ("Sandwich", 20, 50), ("Cake", 2, 650)]
    assert order.total == 2300
    assert [(g.description, g.size, g.allergy_notes, g.dietary_notes) for g in order.guest_groups] == [
        ("Adults", 25, "", ""), ("Children", 5, "Milk", "Halal")]
    assert cart_in_session(client) is None


def test_checkout_without_groups_stores_all_guests(client, customer, repos):
    checkout(client)
    [order] = repos.orders.list_for_customer(customer.id)
    assert [(g.description, g.size) for g in order.guest_groups] == [("All guests", 30)]


@pytest.mark.parametrize("fields, groups, message", [
    ({"event_date": ""}, [], "Please enter a valid event date."),
    ({"event_date": "not-a-date"}, [], "Please enter a valid event date."),
    ({"event_date": date.today().isoformat()}, [], "The event date must be after today."),
    ({"number_of_guests": "0"}, [], "The number of guests must be at least 1."),
    ({"number_of_guests": "many"}, [], "The number of guests must be at least 1."),
    ({"delivery_address": "  "}, [], "Please enter a delivery address."),
    ({}, [{"allergy_notes": "Nuts"}], "Guest group 1 needs a description"),
    ({}, [{"description": "Kids", "size": "x"}], "Guest group 1 needs a description"),
    ({}, [{"description": "A", "size": "20"}, {"description": "B", "size": "11"}], "more than the 30 guests"),
])
def test_checkout_validation(client, customer, repos, fields, groups, message):
    response = checkout(client, groups, **fields)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert repos.orders.list_for_customer(customer.id) == []
    assert cart_in_session(client) is not None


def test_checkout_rechecks_minimum_quantity(client, customer, repos, menu):
    with client.session_transaction() as sess:
        sess["cart"] = {str(menu["sandwich"].id): 5}
    html = checkout(client).get_data(as_text=True)
    assert "Minimum order for Sandwich is 10." in html
    assert repos.orders.list_for_customer(customer.id) == []


def test_form_keeps_entered_values_on_error(client, customer):
    html = checkout(client, [{"description": "Kids", "size": "3", "allergy_notes": "Nuts"}],
                    delivery_address="").get_data(as_text=True)
    assert 'value="Kids"' in html and 'value="Nuts"' in html


def test_price_change_does_not_change_order(client, customer, repos, menu):
    checkout(client)
    sandwich = menu["sandwich"]
    sandwich.price_nok = 999
    sandwich.name = "Renamed"
    repos.food.update(sandwich)
    [order] = repos.orders.list_for_customer(customer.id)
    assert (order.items[0].food_name, order.items[0].unit_price_nok) == ("Sandwich", 50)


def test_cart_page_links_to_checkout(client, customer):
    assert 'href="/checkout"' in client.get("/cart").get_data(as_text=True)
