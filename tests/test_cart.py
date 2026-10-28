import pytest

from app.models.entities import EventCategory, FoodItem
from app.models.services import build_cart, check_quantity


@pytest.fixture
def items(repos):
    party = repos.food.add_category(EventCategory("Birthday"))

    def add(name, published=True, price=100, minimum=10):
        return repos.food.add(FoodItem(name=name, description="Test", price_nok=price,
                                       minimum_quantity=minimum, published=published,
                                       event_categories=[party]))

    return {"sandwich": add("Sandwich"), "cake": add("Cake", price=650, minimum=1),
            "draft": add("Draft", published=False)}


def cart_in_session(client):
    with client.session_transaction() as sess:
        return dict(sess.get("cart", {}))


def set_cart(client, cart):
    with client.session_transaction() as sess:
        sess["cart"] = {str(k): v for k, v in cart.items()}


def add(client, item, quantity, next_url="/menu"):
    return client.post("/cart/add", data={"food_item_id": item.id, "quantity": quantity, "next": next_url})


# Services

def test_check_quantity(items):
    sandwich = items["sandwich"]
    assert check_quantity(sandwich, 9) == "Minimum order for Sandwich is 10."
    assert check_quantity(sandwich, 10) is None
    assert check_quantity(sandwich, 50) is None


def test_build_cart_totals(items, repos):
    cart = build_cart({items["sandwich"].id: 20, items["cake"].id: 2})
    assert [line.line_total for line in cart.lines] == [2000, 1300]
    assert cart.total == 3300
    assert cart.removed == []


def test_build_cart_drops_unavailable_items(items, repos):
    cart = build_cart({items["sandwich"].id: 10, items["draft"].id: 10, 999: 5})
    assert [line.item.name for line in cart.lines] == ["Sandwich"]
    assert cart.removed == ["Draft"]


# Add

def test_add_valid_quantity(client, items):
    response = add(client, items["sandwich"], 20)
    assert response.status_code == 302
    assert response.headers["Location"] == "/menu"
    assert cart_in_session(client) == {str(items["sandwich"].id): 20}


def test_add_below_minimum_is_rejected(client, items):
    response = add(client, items["sandwich"], 5)
    assert cart_in_session(client) == {}
    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Minimum order for Sandwich is 10." in html


def test_add_twice_sums_quantities(client, items):
    add(client, items["sandwich"], 10)
    add(client, items["sandwich"], 3)  # below minimum on its own, but 13 in total is fine
    assert cart_in_session(client) == {str(items["sandwich"].id): 13}


@pytest.mark.parametrize("quantity", ["0", "-5", "abc", ""])
def test_add_invalid_quantity(client, items, quantity):
    add(client, items["cake"], quantity)
    assert cart_in_session(client) == {}


def test_add_unpublished_or_unknown_item_is_404(client, items):
    assert add(client, items["draft"], 10).status_code == 404
    assert client.post("/cart/add", data={"food_item_id": 999, "quantity": 10}).status_code == 404


def test_add_does_not_redirect_to_other_sites(client, items):
    response = add(client, items["cake"], 1, next_url="https://evil.example/")
    assert response.headers["Location"] == "/menu"
    response = add(client, items["cake"], 1, next_url="//evil.example/")
    assert response.headers["Location"] == "/menu"


# Update and remove

def test_update_quantity(client, items):
    set_cart(client, {items["sandwich"].id: 10})
    client.post("/cart/update", data={"food_item_id": items["sandwich"].id, "quantity": 30})
    assert cart_in_session(client) == {str(items["sandwich"].id): 30}


@pytest.mark.parametrize("quantity", ["3", "0", "abc"])
def test_update_rejects_invalid_quantity(client, items, quantity):
    set_cart(client, {items["sandwich"].id: 30})
    response = client.post("/cart/update", data={"food_item_id": items["sandwich"].id, "quantity": quantity})
    assert cart_in_session(client) == {str(items["sandwich"].id): 30}
    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert 'class="flash flash-error"' in html


def test_remove(client, items):
    set_cart(client, {items["sandwich"].id: 10, items["cake"].id: 1})
    client.post("/cart/remove", data={"food_item_id": items["sandwich"].id})
    assert cart_in_session(client) == {str(items["cake"].id): 1}


# Cart page

def test_cart_page_shows_lines_and_estimated_total(client, items):
    set_cart(client, {items["sandwich"].id: 20, items["cake"].id: 2})
    html = client.get("/cart").get_data(as_text=True)
    assert "Sandwich" in html and "Cake" in html
    assert "2 000 kr" in html          # 20 × 100
    assert "1 300 kr" in html          # 2 × 650
    assert "Estimated total" in html
    assert "3 300 kr" in html
    assert "Cart (2)" in html


def test_empty_cart(client, items):
    html = client.get("/cart").get_data(as_text=True)
    assert "Your cart is empty." in html
    assert "Cart (0)" in html


def test_unpublished_item_is_dropped_from_cart(client, items, repos):
    set_cart(client, {items["sandwich"].id: 10, items["cake"].id: 1})
    cake = items["cake"]
    cake.published = False
    repos.food.update(cake)

    html = client.get("/cart").get_data(as_text=True)
    assert "Cake is no longer on the menu" in html
    assert cart_in_session(client) == {str(items["sandwich"].id): 10}


def test_menu_cards_have_add_to_cart_form(client, items):
    html = client.get("/menu").get_data(as_text=True)
    assert 'action="/cart/add"' in html
