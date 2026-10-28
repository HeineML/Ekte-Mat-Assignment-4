def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Ekte Mat Online" in response.data


def test_templates_are_loaded_from_views(app):
    assert app.template_folder == "views"
