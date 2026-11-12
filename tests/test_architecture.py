"""Checks that only the model layer talks to the database (see CLAUDE.md)."""
import re
from pathlib import Path

import pytest

from tests.conftest import login

APP = Path(__file__).resolve().parent.parent / "app"


# Words that would mean a controller or template talks to the database directly.
STORAGE_WORDS = ["sqlite", "neo4j", "cypher", "graphdatabase", "match (", "detach delete"]


@pytest.mark.parametrize("folder", ["controllers", "views"])
def test_controllers_and_views_do_not_touch_storage(folder):
    offenders = [f"{p.relative_to(APP)}: {word}" for p in (APP / folder).rglob("*")
                 if p.suffix in {".py", ".html"}
                 for word in STORAGE_WORDS if word in p.read_text(encoding="utf-8").lower()]
    assert offenders == []


def _imports(pattern):
    """Python files under app/ and tests/ with an import line matching `pattern`."""
    regex = re.compile(rf"^\s*(import|from)\s+{pattern}\b", re.MULTILINE)
    return [p for folder in (APP, APP.parent / "tests") for p in folder.rglob("*.py")
            if regex.search(p.read_text(encoding="utf-8"))]


def test_only_the_neo4j_package_imports_the_driver():
    offenders = [p for p in _imports("neo4j") if (APP / "models" / "neo4j") not in p.parents]
    assert offenders == []


def test_nothing_uses_the_legacy_sqlite_code():
    assert _imports(r"(legacy|sqlite3)") == []


@pytest.mark.parametrize("url, status", [("/does-not-exist", 404), ("/orders/999", 404)])
def test_friendly_error_pages(client, users, url, status):
    login(client, "kari@test.test")
    response = client.get(url)
    assert response.status_code == status
    assert "Back to the menu" in response.get_data(as_text=True)


def test_forbidden_page(client, users):
    login(client, "kari@test.test")
    response = client.get("/admin/orders")
    assert response.status_code == 403
    assert "administrators" in response.get_data(as_text=True)
