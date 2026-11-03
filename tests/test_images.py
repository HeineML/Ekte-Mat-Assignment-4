import io
import os

import pytest

from app.models.entities import EventCategory
from tests.conftest import login

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32  # content isn't inspected, only type and extension


@pytest.fixture
def birthday(repos):
    return repos.food.add_category(EventCategory("Birthday"))


@pytest.fixture
def admin(client, users):
    login(client, "admin@test.test")


def upload_dir(app):
    return app.config["UPLOAD_FOLDER"]


def stored_files(app):
    folder = upload_dir(app)
    return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


def form(birthday, image=None, **extra):
    data = {"name": "Cake", "description": "Sponge cake", "price_nok": "650", "minimum_quantity": "1",
            "category_ids": [birthday.id], "published": "on", **extra}
    if image is not None:
        data["image"] = image
    return data


def png(name="cake.png", content_type="image/png"):
    return (io.BytesIO(PNG), name, content_type)


def create(client, birthday, image=None, **extra):
    return client.post("/admin/food/new", data=form(birthday, image, **extra), content_type="multipart/form-data")


def only_item(repos):
    [item] = repos.food.list_all()
    return item


def test_upload_saves_file_with_random_name(client, admin, birthday, repos, app):
    create(client, birthday, png("../../evil name.png"))
    item = only_item(repos)
    assert item.image.endswith(".png") and "evil" not in item.image and "/" not in item.image
    assert stored_files(app) == [item.image]
    assert f"/static/uploads/{item.image}" in client.get("/menu").get_data(as_text=True)


@pytest.mark.parametrize("image", [png("notes.txt", "text/plain"), png("fake.png", "text/html")])
def test_non_image_is_rejected(client, admin, birthday, repos, app, image):
    html = create(client, birthday, image).get_data(as_text=True)
    assert "The picture must be a PNG, JPEG, GIF or WebP file." in html
    assert repos.food.list_all() == []
    assert stored_files(app) == []


def test_no_picture_uses_placeholder(client, admin, birthday, repos):
    create(client, birthday)
    assert only_item(repos).image is None
    assert "img/placeholder.svg" in client.get("/menu").get_data(as_text=True)


def test_replace_keep_and_remove(client, admin, birthday, repos, app):
    create(client, birthday, png())
    item = only_item(repos)
    first = item.image
    url = f"/admin/food/{item.id}/edit"

    client.post(url, data=form(birthday), content_type="multipart/form-data")
    assert repos.food.get(item.id).image == first  # no file chosen: keep the picture

    client.post(url, data=form(birthday, png("new.jpg", "image/jpeg")), content_type="multipart/form-data")
    second = repos.food.get(item.id).image
    assert second != first and second.endswith(".jpg")
    assert stored_files(app) == [second]

    client.post(url, data=form(birthday, remove_image="on"), content_type="multipart/form-data")
    assert repos.food.get(item.id).image is None
    assert stored_files(app) == []


def test_delete_item_deletes_picture(client, admin, birthday, repos, app):
    create(client, birthday, png())
    client.post(f"/admin/food/{only_item(repos).id}/delete")
    assert stored_files(app) == []


def test_too_large_upload(client, admin, birthday, repos, app):
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    big = (io.BytesIO(b"\0" * (1024 * 1024 + 1)), "big.png", "image/png")
    response = create(client, birthday, big)
    assert response.status_code == 302
    assert "The picture is too large" in client.get(response.headers["Location"]).get_data(as_text=True)
    assert repos.food.list_all() == []


def test_form_has_preview(client, admin, birthday):
    html = client.get("/admin/food/new").get_data(as_text=True)
    assert 'enctype="multipart/form-data"' in html
    assert 'data-preview="image-preview"' in html and 'id="image-preview"' in html
    assert "js/image-preview.js" in html
