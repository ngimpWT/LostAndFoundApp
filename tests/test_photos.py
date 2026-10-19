import pytest

ITEM = {
    "title": "Blue backpack",
    "description": "Navy JanSport with a keychain.",
    "item_type": "lost",
    "location": "Cornette Library",
}

# The first bytes of a real PNG file, followed by some filler data.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    """Save uploaded photos to a temporary folder instead of the real uploads/."""
    import routers.photos

    monkeypatch.setattr(routers.photos, "UPLOAD_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def item_id(client, student):
    response = client.post("/items", json=ITEM, headers=student)
    return response.json()["id"]


def upload(client, item_id, headers, caption="Front view", content=PNG_BYTES,
           filename="bag.png", content_type="image/png"):
    return client.post(
        f"/items/{item_id}/photos",
        data={"caption": caption},
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


# ---------- Upload ----------

def test_owner_uploads_photo_returns_201(client, student, item_id):
    response = upload(client, item_id, student)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["item_id"] == item_id
    assert data["caption"] == "Front view"
    assert data["url"] == f"/photos/{data['id']}/image"


def test_uploaded_photo_is_saved_and_served(client, student, item_id, upload_dir):
    photo = upload(client, item_id, student).json()
    assert len(list(upload_dir.iterdir())) == 1

    response = client.get(photo["url"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG_BYTES


def test_upload_jpeg(client, student, item_id):
    response = upload(client, item_id, student, content=JPEG_BYTES,
                      filename="bag.jpg", content_type="image/jpeg")
    assert response.status_code == 201


def test_item_includes_its_photos(client, student, item_id):
    upload(client, item_id, student, caption="Front view")
    upload(client, item_id, student, caption="Keychain close-up")
    item = client.get(f"/items/{item_id}").json()
    assert [p["caption"] for p in item["photos"]] == ["Front view", "Keychain close-up"]


def test_list_photos_for_item(client, student, item_id):
    upload(client, item_id, student, caption="One")
    upload(client, item_id, student, caption="Two")
    response = client.get(f"/items/{item_id}/photos")
    assert response.status_code == 200
    assert [p["caption"] for p in response.json()] == ["One", "Two"]


def test_new_item_has_no_photos(client, item_id):
    assert client.get(f"/items/{item_id}").json()["photos"] == []


def test_upload_without_login_returns_401(client, item_id):
    assert upload(client, item_id, {}).status_code == 401


def test_upload_by_other_student_returns_403(client, item_id, other_student):
    assert upload(client, item_id, other_student).status_code == 403


def test_upload_to_unknown_item_returns_404(client, student):
    assert upload(client, 999, student).status_code == 404


def test_upload_blank_caption_returns_422(client, student, item_id):
    assert upload(client, item_id, student, caption="   ").status_code == 422


def test_upload_missing_caption_returns_422(client, student, item_id):
    response = client.post(
        f"/items/{item_id}/photos",
        files={"file": ("bag.png", PNG_BYTES, "image/png")},
        headers=student,
    )
    assert response.status_code == 422


def test_upload_missing_file_returns_422(client, student, item_id):
    response = client.post(f"/items/{item_id}/photos", data={"caption": "Hi"}, headers=student)
    assert response.status_code == 422


def test_upload_non_image_returns_415(client, student, item_id):
    response = upload(client, item_id, student, content=b"hello",
                      filename="notes.txt", content_type="text/plain")
    assert response.status_code == 415


def test_upload_fake_image_returns_415(client, student, item_id):
    # Claims to be a PNG, but the bytes are actually HTML.
    response = upload(client, item_id, student, content=b"<html>not an image</html>")
    assert response.status_code == 415


def test_upload_too_large_returns_413(client, student, item_id, upload_dir):
    big = PNG_BYTES + b"\x00" * (5 * 1024 * 1024)
    assert upload(client, item_id, student, content=big).status_code == 413
    assert list(upload_dir.iterdir()) == []


def test_photos_for_unknown_item_returns_404(client):
    assert client.get("/items/999/photos").status_code == 404


def test_image_for_unknown_photo_returns_404(client):
    assert client.get("/photos/999/image").status_code == 404


# ---------- Delete ----------

def test_owner_deletes_photo(client, student, item_id, upload_dir):
    photo = upload(client, item_id, student).json()
    response = client.delete(f"/photos/{photo['id']}", headers=student)
    assert response.status_code == 204
    assert list(upload_dir.iterdir()) == []
    assert client.get(photo["url"]).status_code == 404
    assert client.get(f"/items/{item_id}").json()["photos"] == []


def test_delete_by_other_student_returns_403(client, student, other_student, item_id):
    photo = upload(client, item_id, student).json()
    assert client.delete(f"/photos/{photo['id']}", headers=other_student).status_code == 403


def test_delete_without_login_returns_401(client, student, item_id):
    photo = upload(client, item_id, student).json()
    assert client.delete(f"/photos/{photo['id']}").status_code == 401


def test_delete_unknown_photo_returns_404(client, student):
    assert client.delete("/photos/999", headers=student).status_code == 404
