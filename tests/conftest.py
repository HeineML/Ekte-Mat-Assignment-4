import os

import pytest
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Read NEO4J_TEST_* from .env before app.config reads the environment.
load_dotenv()

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.models import get_repos  # noqa: E402
from app.models.entities import Role, User  # noqa: E402


def _test_database_problem():
    if not TestConfig.NEO4J_URI or not TestConfig.NEO4J_PASSWORD:
        return "NEO4J_TEST_URI and NEO4J_TEST_PASSWORD are not set (see .env.example)"
    if TestConfig.NEO4J_URI == os.environ.get("NEO4J_URI"):
        return "NEO4J_TEST_URI is the app's own instance; the tests would delete its data"
    return None


@pytest.fixture
def app(tmp_path):
    """An app connected to the separate Neo4j test instance, emptied before every test."""
    problem = _test_database_problem()
    if problem:
        pytest.skip(f"No Neo4j test database: {problem}")
    app = create_app(TestConfig)
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
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


# Hashing is deliberately slow, so the test password is hashed once for the whole run.
SECRET123_HASH = generate_password_hash("secret123")


@pytest.fixture
def users(repos):
    """One admin and two customers. Every password is 'secret123'."""
    def add(name, email, role=Role.CUSTOMER):
        return repos.users.add(User(name=name, email=email, password_hash=SECRET123_HASH, role=role))

    return {"admin": add("Admin", "admin@test.test", Role.ADMIN),
            "kari": add("Kari", "kari@test.test"),
            "ola": add("Ola", "ola@test.test")}


def login(client, email, password="secret123", next_url=""):
    return client.post("/login", data={"email": email, "password": password, "next": next_url})
