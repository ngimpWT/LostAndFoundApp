import pytest
from sqlalchemy import event

from tests.conftest import approve

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    import routers.photos

    monkeypatch.setattr(routers.photos, "UPLOAD_DIR", tmp_path)


@pytest.fixture
def items(client, student, admin):
    """A small set of posts to search. Returns {title: id}."""

    def post(title, description, item_type, location, publish=True):
        body = {"title": title, "description": description,
                "item_type": item_type, "location": location}
        item_id = client.post("/items", json=body, headers=student).json()["id"]
        if publish:
            approve(client, admin, item_id)
        return item_id

    ids = {
        "Blue backpack": post("Blue backpack", "Navy JanSport with keychain", "lost", "Cornette Library"),
        "Car keys": post("Car keys", "Toyota fob on a red lanyard", "found", "Student Center"),
        "Blue water bottle": post("Blue water bottle", "Hydro Flask with stickers", "found", "Recreation Center"),
        "Calculator": post("Calculator", "TI-84 with initials JB", "lost", "Classroom Center"),
        "Secret pending post": post("Secret pending post", "Blue phone", "lost", "Cornette Library", publish=False),
    }

    # A resolved post: approved, then marked resolved by its owner.
    ids["Old umbrella"] = post("Old umbrella", "Black umbrella", "found", "Cornette Library")
    client.put(f"/items/{ids['Old umbrella']}/resolve", headers=student)

    # A photo caption that mentions something the title/description don't.
    client.post(
        f"/items/{ids['Calculator']}/photos",
        data={"caption": "Purple sticker on the back"},
        files={"file": ("calc.png", PNG_BYTES, "image/png")},
        headers=student,
    )
    approve(client, admin, ids["Calculator"])  # adding a photo sent it back to pending
    return ids


def search(client, **params):
    response = client.get("/items/search", params=params)
    assert response.status_code == 200, response.text
    return [item["title"] for item in response.json()]


# ---------- No filters ----------

def test_search_without_filters_returns_open_approved_posts_newest_first(client, items):
    assert search(client) == ["Calculator", "Blue water bottle", "Car keys", "Blue backpack"]


def test_search_never_returns_pending_posts(client, items):
    assert "Secret pending post" not in search(client, q="secret")


def test_search_with_no_matches_returns_empty_list(client, items):
    assert search(client, q="unicorn") == []


# ---------- Keyword ----------

def test_keyword_matches_title(client, items):
    assert search(client, q="backpack") == ["Blue backpack"]


def test_keyword_matches_description(client, items):
    assert search(client, q="toyota") == ["Car keys"]


def test_keyword_matches_location(client, items):
    assert search(client, q="recreation") == ["Blue water bottle"]


def test_keyword_matches_photo_caption(client, items):
    assert search(client, q="purple") == ["Calculator"]


def test_keyword_is_case_insensitive(client, items):
    assert search(client, q="BLUE") == ["Blue water bottle", "Blue backpack"]


def test_every_keyword_must_match(client, items):
    # "blue" matches two posts, but only one also mentions "library".
    assert search(client, q="blue library") == ["Blue backpack"]


def test_blank_keyword_is_ignored(client, items):
    assert len(search(client, q="   ")) == 4


def test_wildcard_characters_are_treated_literally(client, items):
    assert search(client, q="%") == []
    assert search(client, q="_") == []


def test_keyword_too_long_returns_422(client):
    assert client.get("/items/search", params={"q": "x" * 101}).status_code == 422


# ---------- Filters ----------

def test_filter_by_item_type(client, items):
    assert search(client, item_type="lost") == ["Calculator", "Blue backpack"]
    assert search(client, item_type="found") == ["Blue water bottle", "Car keys"]


def test_invalid_item_type_returns_422(client):
    assert client.get("/items/search", params={"item_type": "stolen"}).status_code == 422


def test_filter_by_location_is_partial_and_case_insensitive(client, items):
    assert search(client, location="center") == ["Calculator", "Blue water bottle", "Car keys"]
    assert search(client, location="Cornette Library") == ["Blue backpack"]


def test_include_resolved(client, items):
    assert "Old umbrella" not in search(client)
    assert "Old umbrella" in search(client, include_resolved=True)


def test_combined_keyword_type_and_location(client, items):
    assert search(client, q="blue", item_type="found", location="recreation") == ["Blue water bottle"]
    assert search(client, q="blue", item_type="found", location="library") == []


# ---------- Location options ----------

def test_locations_lists_distinct_approved_locations_sorted(client, items):
    response = client.get("/items/locations")
    assert response.status_code == 200
    assert response.json() == [
        "Classroom Center",
        "Cornette Library",
        "Recreation Center",
        "Student Center",
    ]


def test_locations_empty_when_nothing_approved(client):
    assert client.get("/items/locations").json() == []


# ---------- Performance ----------

def test_search_query_count_does_not_grow_with_results(client, session_factory, admin, student, other_student):
    """Owners and photos should load in bulk, not with one extra query per post."""
    for i in range(10):
        headers = student if i % 2 else other_student
        body = {"title": f"Item {i}", "description": "d", "item_type": "lost", "location": "Library"}
        item_id = client.post("/items", json=body, headers=headers).json()["id"]
        client.post(
            f"/items/{item_id}/photos",
            data={"caption": "Photo"},
            files={"file": ("p.png", PNG_BYTES, "image/png")},
            headers=headers,
        )
        approve(client, admin, item_id)

    statements = []
    engine = session_factory.kw["bind"]
    listener = lambda *args: statements.append(args[2])  # args[2] is the SQL text
    event.listen(engine, "before_cursor_execute", listener)
    try:
        response = client.get("/items/search")
    finally:
        event.remove(engine, "before_cursor_execute", listener)

    assert len(response.json()) == 10
    assert len(statements) <= 4, statements
