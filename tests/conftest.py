import pytest

from app import create_app
from app.config import TestConfig
from app.models import get_repos


@pytest.fixture
def app(tmp_path):
    app = create_app(TestConfig)
    app.config["DATABASE"] = str(tmp_path / "test.sqlite")
    with app.app_context():
        get_repos().reset()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def repos(app):
    with app.app_context():
        yield get_repos()


@pytest.fixture
def users(repos):
    """One admin and two customers. Every password is 'secret123'."""
    from werkzeug.security import generate_password_hash
    from app.models.entities import Role, User

    def add(name, email, role=Role.CUSTOMER):
        return repos.users.add(User(name=name, email=email,
                                    password_hash=generate_password_hash("secret123"), role=role))

    return {"admin": add("Admin", "admin@test.test", Role.ADMIN),
            "kari": add("Kari", "kari@test.test"),
            "ola": add("Ola", "ola@test.test")}


def login(client, email, password="secret123", next_url=""):
    return client.post("/login", data={"email": email, "password": password, "next": next_url})
