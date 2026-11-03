from datetime import date, timedelta

import pytest

from app.models.entities import GuestGroup, Order, OrderItem, OrderStatus, PaymentStatus
from tests.conftest import login


@pytest.fixture
def orders(repos, users):
    def add(customer, guests, **kwargs):
        return repos.orders.add(Order(
            customer_id=customer.id, event_date=date.today() + timedelta(days=10), number_of_guests=guests,
            delivery_address="Testveien 1", items=[OrderItem(None, "Cake", 2, 650)],
            guest_groups=[GuestGroup("Children", 3, allergy_notes="Milk allergy", dietary_notes="Halal")],
            **kwargs))

    return {"kari": add(users["kari"], 12, status=OrderStatus.IN_PREPARATION,
                        payment_status=PaymentStatus.DEPOSIT_PAID),
            "ola": add(users["ola"], 99)}


@pytest.mark.parametrize("url", ["/orders", "/orders/1"])
def test_pages_require_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?next=")


def test_list_shows_only_own_orders(client, orders):
    login(client, "kari@test.test")
    html = client.get("/orders").get_data(as_text=True)
    assert f"#{orders['kari'].id}" in html
    assert f"#{orders['ola'].id}" not in html
    assert "In preparation" in html and "Deposit paid" in html
    assert "1 300 kr" in html


def test_empty_list(client, users):
    login(client, "kari@test.test")
    assert "You haven't placed any orders yet." in client.get("/orders").get_data(as_text=True)


def test_detail_shows_order(client, orders):
    login(client, "kari@test.test")
    html = client.get(f"/orders/{orders['kari'].id}").get_data(as_text=True)
    for text in ["In preparation", "Deposit paid", "Testveien 1", "Cake", "1 300 kr",
                 "Children", "Milk allergy", "Halal"]:
        assert text in html


def test_other_customers_order_is_404(client, orders):
    login(client, "kari@test.test")
    assert client.get(f"/orders/{orders['ola'].id}").status_code == 404
    assert client.get("/orders/999").status_code == 404


def test_nav_has_my_orders_link(client, users):
    login(client, "kari@test.test")
    assert 'href="/orders"' in client.get("/").get_data(as_text=True)
