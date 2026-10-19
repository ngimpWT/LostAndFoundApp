import pytest


@pytest.mark.parametrize("path", ["/", "/static/app.js", "/static/index.html"])
def test_frontend_files_are_rechecked_by_the_browser(client, path):
    # Without this, a browser may keep running old JavaScript after the files change.
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"


def test_api_responses_are_not_affected(client):
    assert "cache-control" not in client.get("/items").headers
