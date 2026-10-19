import pytest

from tests.conftest import approve

ITEM = {
    "title": "Blue backpack",
    "description": "Navy JanSport with a keychain.",
    "item_type": "lost",
    "location": "Cornette Library",
}
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    import routers.photos

    monkeypatch.setattr(routers.photos, "UPLOAD_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def item_id(client, student):
    return client.post("/items", json=ITEM, headers=student).json()["id"]


def review(client, headers, item_id, decision, comments=None):
    body = {"decision": decision}
    if comments is not None:
        body["comments"] = comments
    return client.post(f"/items/{item_id}/reviews", json=body, headers=headers)


def feed_ids(client):
    return [item["id"] for item in client.get("/items").json()]


def upload_photo(client, headers, item_id):
    return client.post(
        f"/items/{item_id}/photos",
        data={"caption": "Front view"},
        files={"file": ("bag.png", PNG_BYTES, "image/png")},
        headers=headers,
    )


# ---------- New posts start as pending ----------

def test_new_item_is_pending(client, student):
    response = client.post("/items", json=ITEM, headers=student)
    assert response.json()["status"] == "pending"


def test_pending_item_not_in_public_feed(client, item_id):
    assert feed_ids(client) == []


def test_pending_item_hidden_from_public_and_other_students(client, item_id, other_student):
    assert client.get(f"/items/{item_id}").status_code == 404
    assert client.get(f"/items/{item_id}", headers=other_student).status_code == 404
    assert client.get(f"/items/{item_id}/photos").status_code == 404


def test_pending_item_visible_to_owner_and_admin(client, item_id, student, admin):
    assert client.get(f"/items/{item_id}", headers=student).status_code == 200
    assert client.get(f"/items/{item_id}", headers=admin).status_code == 200


def test_pending_photo_image_hidden_from_public(client, item_id, student, admin):
    photo = upload_photo(client, student, item_id).json()
    assert client.get(photo["url"]).status_code == 404
    assert client.get(photo["url"], headers=student).status_code == 200
    assert client.get(photo["url"], headers=admin).status_code == 200


# ---------- My posts ----------

def test_my_items_lists_own_posts_with_status(client, student, other_student, admin):
    first = client.post("/items", json={**ITEM, "title": "Mine 1"}, headers=student).json()["id"]
    client.post("/items", json={**ITEM, "title": "Mine 2"}, headers=student)
    client.post("/items", json={**ITEM, "title": "Not mine"}, headers=other_student)
    approve(client, admin, first)

    response = client.get("/items/mine", headers=student)
    assert response.status_code == 200
    assert [(i["title"], i["status"]) for i in response.json()] == [
        ("Mine 2", "pending"),
        ("Mine 1", "approved"),
    ]


def test_my_items_without_login_returns_401(client):
    assert client.get("/items/mine").status_code == 401


# ---------- Review queue ----------

def test_admin_sees_pending_queue_oldest_first(client, student, admin):
    first = client.post("/items", json={**ITEM, "title": "First"}, headers=student).json()["id"]
    second = client.post("/items", json={**ITEM, "title": "Second"}, headers=student).json()["id"]
    third = client.post("/items", json={**ITEM, "title": "Third"}, headers=student).json()["id"]
    approve(client, admin, second)

    response = client.get("/moderation/pending", headers=admin)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [first, third]


def test_student_cannot_see_pending_queue(client, student):
    assert client.get("/moderation/pending", headers=student).status_code == 403


def test_pending_queue_without_login_returns_401(client):
    assert client.get("/moderation/pending").status_code == 401


# ---------- Reviewing ----------

def test_admin_approves_item(client, item_id, admin):
    response = review(client, admin, item_id, "approve", "Looks fine")
    assert response.status_code == 201
    record = response.json()
    assert record["id"] > 0
    assert record["item_id"] == item_id
    assert record["admin_id"] == int(admin["X-User-Id"])
    assert record["admin_name"] == "Admin Person"
    assert record["decision"] == "approve"
    assert record["comments"] == "Looks fine"
    assert record["reviewed_at"]

    assert client.get(f"/items/{item_id}").json()["status"] == "approved"
    assert feed_ids(client) == [item_id]
    assert client.get("/moderation/pending", headers=admin).json() == []


def test_approve_without_comments(client, item_id, admin):
    response = review(client, admin, item_id, "approve")
    assert response.status_code == 201
    assert response.json()["comments"] == ""


def test_admin_rejects_item_with_comments(client, item_id, admin, student):
    response = review(client, admin, item_id, "reject", "Contains a phone number in the title")
    assert response.status_code == 201
    assert response.json()["decision"] == "reject"
    assert client.get(f"/items/{item_id}", headers=student).json()["status"] == "rejected"
    assert feed_ids(client) == []
    assert client.get(f"/items/{item_id}").status_code == 404


def test_reject_without_comments_returns_422(client, item_id, admin):
    assert review(client, admin, item_id, "reject").status_code == 422
    assert review(client, admin, item_id, "reject", "   ").status_code == 422


def test_invalid_decision_returns_422(client, item_id, admin):
    assert review(client, admin, item_id, "maybe", "Hmm").status_code == 422


def test_student_cannot_review_returns_403(client, item_id, student):
    assert review(client, student, item_id, "approve").status_code == 403


def test_review_without_login_returns_401(client, item_id):
    assert review(client, {}, item_id, "approve").status_code == 401


def test_review_unknown_item_returns_404(client, admin):
    assert review(client, admin, 999, "approve").status_code == 404


def test_admin_can_take_down_approved_item(client, item_id, admin):
    approve(client, admin, item_id)
    review(client, admin, item_id, "reject", "Reported as spam")
    assert feed_ids(client) == []


# ---------- Review history ----------

def test_review_history_visible_to_owner_and_admin(client, item_id, student, admin):
    review(client, admin, item_id, "reject", "Please add a description")
    review(client, admin, item_id, "approve", "Thanks")

    for headers in (student, admin):
        response = client.get(f"/items/{item_id}/reviews", headers=headers)
        assert response.status_code == 200
        assert [r["decision"] for r in response.json()] == ["reject", "approve"]


def test_review_history_hidden_from_other_students(client, item_id, other_student):
    assert client.get(f"/items/{item_id}/reviews", headers=other_student).status_code == 403


def test_review_history_without_login_returns_401(client, item_id):
    assert client.get(f"/items/{item_id}/reviews").status_code == 401


def test_review_history_unknown_item_returns_404(client, admin):
    assert client.get("/items/999/reviews", headers=admin).status_code == 404


# ---------- Changes send a post back for review ----------

def test_editing_approved_item_returns_it_to_pending(client, item_id, student, admin):
    approve(client, admin, item_id)
    response = client.put(f"/items/{item_id}", json={**ITEM, "title": "Edited"}, headers=student)
    assert response.json()["status"] == "pending"
    assert feed_ids(client) == []


def test_editing_rejected_item_resubmits_it(client, item_id, student, admin):
    review(client, admin, item_id, "reject", "Too vague")
    client.put(f"/items/{item_id}", json={**ITEM, "description": "More detail"}, headers=student)
    queue = client.get("/moderation/pending", headers=admin).json()
    assert [item["id"] for item in queue] == [item_id]


def test_adding_photo_to_approved_item_returns_it_to_pending(client, item_id, student, admin):
    approve(client, admin, item_id)
    upload_photo(client, student, item_id)
    assert client.get(f"/items/{item_id}", headers=student).json()["status"] == "pending"


def test_resolving_approved_item_keeps_it_approved(client, item_id, student, admin):
    approve(client, admin, item_id)
    client.put(f"/items/{item_id}/resolve", headers=student)
    assert feed_ids(client) == [item_id]
