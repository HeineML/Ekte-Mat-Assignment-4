import pytest
from werkzeug.security import check_password_hash

from app.controllers.decorators import admin_required, login_required
from app.models.entities import Role
from tests.conftest import login


def session_data(client):
    with client.session_transaction() as sess:
        return dict(sess)


def register(client, name="Nina", email="nina@test.test", password="password1", password2=None, **extra):
    data = {"name": name, "email": email, "password": password,
            "password2": password if password2 is None else password2, **extra}
    return client.post("/register", data=data)


# Register

def test_register_creates_logged_in_customer(client, repos):
    response = register(client, email="  Nina@Test.test ")
    assert response.status_code == 302
    user = repos.users.get_by_email("nina@test.test")
    assert user.email == "nina@test.test"
    assert user.role == Role.CUSTOMER
    assert user.password_hash != "password1"
    assert check_password_hash(user.password_hash, "password1")
    assert session_data(client)["user_id"] == user.id


@pytest.mark.parametrize("fields, message", [
    ({"name": ""}, "Please enter your name."),
    ({"email": "not-an-email"}, "Please enter a valid email address."),
    ({"password": "short"}, "at least 8 characters"),
    ({"password2": "different1"}, "The passwords don&#39;t match."),
])
def test_register_validation(client, repos, fields, message):
    response = register(client, **fields)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert "user_id" not in session_data(client)


def test_register_duplicate_email(client, users):
    html = register(client, email="KARI@test.test").get_data(as_text=True)
    assert "An account with this email already exists." in html


def test_register_cannot_create_admin(client, repos):
    register(client, role="admin")
    assert repos.users.get_by_email("nina@test.test").role == Role.CUSTOMER


def test_register_form_keeps_name_and_email(client):
    html = register(client, password="short").get_data(as_text=True)
    assert 'value="Nina"' in html and 'value="nina@test.test"' in html
    assert "short" not in html


# Login and logout

def test_login_success(client, users):
    response = login(client, "kari@test.test")
    assert response.status_code == 302
    assert session_data(client)["user_id"] == users["kari"].id
    html = client.get("/").get_data(as_text=True)
    assert "Kari" in html and "Log out" in html


@pytest.mark.parametrize("email, password", [("kari@test.test", "wrong-password"), ("nobody@test.test", "secret123")])
def test_login_failure(client, users, email, password):
    response = login(client, email, password)
    assert response.status_code == 200
    assert "Wrong email or password." in response.get_data(as_text=True)
    assert "user_id" not in session_data(client)


def test_login_keeps_cart(client, users):
    with client.session_transaction() as sess:
        sess["cart"] = {"1": 10}
    login(client, "kari@test.test")
    assert session_data(client)["cart"] == {"1": 10}


def test_login_redirects_to_local_next_only(client, users):
    assert login(client, "kari@test.test", next_url="/cart").headers["Location"] == "/cart"
    client.post("/logout")
    assert login(client, "kari@test.test", next_url="https://evil.example/").headers["Location"] == "/menu"


def test_logout(client, users):
    login(client, "kari@test.test")
    client.post("/logout")
    assert "user_id" not in session_data(client)
    assert "Log in" in client.get("/").get_data(as_text=True)


# Decorators

@pytest.fixture
def protected(app):
    app.add_url_rule("/test-customer", "test_customer", login_required(lambda: "customer page"))
    app.add_url_rule("/test-admin", "test_admin", admin_required(lambda: "admin page"))


def test_login_required_redirects_to_login(client, protected):
    response = client.get("/test-customer?x=1")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/test-customer?x%3D1"


def test_login_required_allows_logged_in(client, users, protected):
    login(client, "kari@test.test")
    assert client.get("/test-customer").get_data(as_text=True) == "customer page"


def test_admin_required(client, users, protected):
    assert client.get("/test-admin").status_code == 302
    login(client, "kari@test.test")
    assert client.get("/test-admin").status_code == 403
    client.post("/logout")
    login(client, "admin@test.test")
    assert client.get("/test-admin").get_data(as_text=True) == "admin page"
