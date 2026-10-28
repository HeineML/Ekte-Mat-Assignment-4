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
