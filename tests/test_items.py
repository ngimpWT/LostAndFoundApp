from tests.conftest import approve

ITEM = {
    "title": "Blue backpack",
    "description": "Navy JanSport with a keychain, left near the study rooms.",
    "item_type": "lost",
    "location": "Cornette Library",
}


def create_item(client, headers, **overrides):
    return client.post("/items", json={**ITEM, **overrides}, headers=headers)


# ---------- Create ----------

def test_student_creates_item_returns_201(client, student):
    response = create_item(client, student)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["title"] == "Blue backpack"
    assert data["description"] == ITEM["description"]
    assert data["item_type"] == "lost"
    assert data["location"] == "Cornette Library"
    assert data["is_resolved"] is False
    assert data["owner_id"] == int(student["X-User-Id"])
    assert data["owner_name"] == "Alex Buff"


def test_create_found_item(client, student):
    response = create_item(client, student, item_type="found")
    assert response.status_code == 201
    assert response.json()["item_type"] == "found"


def test_create_without_login_returns_401(client):
    assert client.post("/items", json=ITEM).status_code == 401


def test_create_with_unknown_user_returns_401(client):
    assert create_item(client, {"X-User-Id": "999"}).status_code == 401


def test_admin_cannot_create_item_returns_403(client, admin):
    assert create_item(client, admin).status_code == 403


def test_create_invalid_item_type_returns_422(client, student):
    assert create_item(client, student, item_type="stolen").status_code == 422


def test_create_blank_title_returns_422(client, student):
    assert create_item(client, student, title="   ").status_code == 422


def test_create_blank_location_returns_422(client, student):
    assert create_item(client, student, location="").status_code == 422


def test_create_missing_field_returns_422(client, student):
    response = client.post("/items", json={"title": "Keys"}, headers=student)
    assert response.status_code == 422


# ---------- Read ----------

def test_list_items_newest_first(client, student, admin):
    for title in ["First", "Second"]:
        approve(client, admin, create_item(client, student, title=title).json()["id"])
    response = client.get("/items")
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Second", "First"]


def test_get_item_by_id(client, student):
    item_id = create_item(client, student).json()["id"]
    response = client.get(f"/items/{item_id}", headers=student)
    assert response.status_code == 200
    assert response.json()["title"] == "Blue backpack"


def test_get_unknown_item_returns_404(client):
    assert client.get("/items/999").status_code == 404


# ---------- Update ----------

def test_owner_updates_item(client, student):
    item_id = create_item(client, student).json()["id"]
    changes = {**ITEM, "title": "Navy backpack", "location": "Student Center"}
    response = client.put(f"/items/{item_id}", json=changes, headers=student)
    assert response.status_code == 200
    assert response.json()["title"] == "Navy backpack"
    assert response.json()["location"] == "Student Center"
    assert client.get(f"/items/{item_id}", headers=student).json()["title"] == "Navy backpack"


def test_update_by_other_student_returns_403(client, student, other_student):
    item_id = create_item(client, student).json()["id"]
    response = client.put(f"/items/{item_id}", json=ITEM, headers=other_student)
    assert response.status_code == 403


def test_update_without_login_returns_401(client, student):
    item_id = create_item(client, student).json()["id"]
    assert client.put(f"/items/{item_id}", json=ITEM).status_code == 401


def test_update_unknown_item_returns_404(client, student):
    assert client.put("/items/999", json=ITEM, headers=student).status_code == 404


def test_update_invalid_data_returns_422(client, student):
    item_id = create_item(client, student).json()["id"]
    response = client.put(f"/items/{item_id}", json={**ITEM, "item_type": "maybe"}, headers=student)
    assert response.status_code == 422


# ---------- Resolve ----------

def test_owner_marks_item_resolved(client, student):
    item_id = create_item(client, student).json()["id"]
    response = client.put(f"/items/{item_id}/resolve", headers=student)
    assert response.status_code == 200
    assert response.json()["is_resolved"] is True
    assert client.get(f"/items/{item_id}", headers=student).json()["is_resolved"] is True


def test_resolve_by_other_student_returns_403(client, student, other_student):
    item_id = create_item(client, student).json()["id"]
    assert client.put(f"/items/{item_id}/resolve", headers=other_student).status_code == 403


def test_resolve_without_login_returns_401(client, student):
    item_id = create_item(client, student).json()["id"]
    assert client.put(f"/items/{item_id}/resolve").status_code == 401


def test_resolve_unknown_item_returns_404(client, student):
    assert client.put("/items/999/resolve", headers=student).status_code == 404
