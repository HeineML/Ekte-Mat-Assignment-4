"""Checks that keep the storage replaceable by Neo4j (CLAUDE.md, docs/plans/00-architecture.md §3)."""
from pathlib import Path

import pytest

from tests.conftest import login

APP = Path(__file__).resolve().parent.parent / "app"


@pytest.mark.parametrize("folder", ["controllers", "views"])
def test_controllers_and_views_do_not_use_sqlite(folder):
    offenders = [str(p.relative_to(APP)) for p in (APP / folder).rglob("*")
                 if p.suffix in {".py", ".html"} and "sqlite" in p.read_text(encoding="utf-8").lower()]
    assert offenders == []


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
