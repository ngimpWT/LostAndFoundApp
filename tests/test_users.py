STUDENT = {
    "name": "Alex Buff",
    "email": "alex@buffs.wtamu.edu",
    "phone": "806-555-0101",
}


def register(client, **overrides):
    return client.post("/users", json={**STUDENT, **overrides})


# ---------- Registration ----------

def test_register_student_returns_201_and_user(client):
    response = register(client)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Alex Buff"
    assert data["email"] == "alex@buffs.wtamu.edu"
    assert data["phone"] == "8065550101"  # stored as digits only
    assert data["role"] == "student"  # default role


def test_register_admin(client):
    response = register(client, role="admin")
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_register_normalizes_email_to_lowercase(client):
    response = register(client, email="Alex@Buffs.WTAMU.edu")
    assert response.status_code == 201
    assert response.json()["email"] == "alex@buffs.wtamu.edu"


def test_register_duplicate_email_returns_409(client):
    register(client)
    response = register(client, email="ALEX@buffs.wtamu.edu", name="Someone Else")
    assert response.status_code == 409


def test_register_missing_field_returns_422(client):
    response = client.post("/users", json={"name": "Alex", "email": "a@b.edu"})
    assert response.status_code == 422


def test_register_invalid_email_returns_422(client):
    assert register(client, email="not-an-email").status_code == 422


def test_register_blank_name_returns_422(client):
    assert register(client, name="   ").status_code == 422


def test_register_invalid_phone_returns_422(client):
    assert register(client, phone="call me").status_code == 422
    assert register(client, phone="123").status_code == 422


def test_register_invalid_role_returns_422(client):
    assert register(client, role="superuser").status_code == 422


# ---------- Login ----------

def test_login_with_matching_details_returns_200(client):
    user_id = register(client).json()["id"]
    response = client.post("/users/login", json=STUDENT)
    assert response.status_code == 200
    assert response.json()["id"] == user_id


def test_login_ignores_case_and_phone_formatting(client):
    register(client)
    response = client.post(
        "/users/login",
        json={"name": "alex buff", "email": "ALEX@buffs.wtamu.edu", "phone": "(806) 555-0101"},
    )
    assert response.status_code == 200


def test_login_unknown_email_returns_401(client):
    register(client)
    response = client.post("/users/login", json={**STUDENT, "email": "nobody@buffs.wtamu.edu"})
    assert response.status_code == 401


def test_login_wrong_phone_returns_401(client):
    register(client)
    response = client.post("/users/login", json={**STUDENT, "phone": "806-555-9999"})
    assert response.status_code == 401


def test_login_wrong_name_returns_401(client):
    register(client)
    response = client.post("/users/login", json={**STUDENT, "name": "Wrong Name"})
    assert response.status_code == 401


def test_login_missing_field_returns_422(client):
    response = client.post("/users/login", json={"email": STUDENT["email"]})
    assert response.status_code == 422


# ---------- Read (contact details are private) ----------

def test_me_returns_current_user(client):
    user_id = register(client).json()["id"]
    response = client.get("/users/me", headers={"X-User-Id": str(user_id)})
    assert response.status_code == 200
    assert response.json()["email"] == STUDENT["email"]


def test_me_without_login_returns_401(client):
    assert client.get("/users/me").status_code == 401


def test_me_with_unknown_user_returns_401(client):
    assert client.get("/users/me", headers={"X-User-Id": "999"}).status_code == 401


def test_user_can_read_themselves(client):
    user_id = register(client).json()["id"]
    response = client.get(f"/users/{user_id}", headers={"X-User-Id": str(user_id)})
    assert response.status_code == 200
    assert response.json()["email"] == STUDENT["email"]


def test_get_user_without_login_returns_401(client):
    user_id = register(client).json()["id"]
    assert client.get(f"/users/{user_id}").status_code == 401


def test_student_cannot_read_other_users_returns_403(client, other_student):
    user_id = register(client).json()["id"]
    assert client.get(f"/users/{user_id}", headers=other_student).status_code == 403


def test_admin_can_read_any_user(client, admin):
    user_id = register(client).json()["id"]
    response = client.get(f"/users/{user_id}", headers=admin)
    assert response.status_code == 200
    assert response.json()["email"] == STUDENT["email"]


def test_get_unknown_user_as_admin_returns_404(client, admin):
    assert client.get("/users/999", headers=admin).status_code == 404


def test_admin_lists_users(client, admin):
    register(client)
    response = client.get("/users", headers=admin)
    assert response.status_code == 200
    assert [u["email"] for u in response.json()] == ["admin@wtamu.edu", "alex@buffs.wtamu.edu"]


def test_list_users_without_login_returns_401(client):
    register(client)
    assert client.get("/users").status_code == 401


def test_student_cannot_list_users_returns_403(client, student):
    assert client.get("/users", headers=student).status_code == 403
