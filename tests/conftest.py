import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from make_admin import promote_to_admin


@pytest.fixture
def session_factory():
    """A fresh in-memory database for each test. Call it to open a session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(bind=engine, autoflush=False)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(session_factory):
    """A TestClient whose requests use the test database."""

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(client, name, email, phone="806-555-0101"):
    """Register a user and return the headers that identify them to the API."""
    response = client.post("/users", json={"name": name, "email": email, "phone": phone})
    assert response.status_code == 201
    return {"X-User-Id": str(response.json()["id"])}


def approve(client, admin_headers, item_id):
    """Have an admin approve a post so it shows up in the public feed."""
    response = client.post(
        f"/items/{item_id}/reviews", json={"decision": "approve"}, headers=admin_headers
    )
    assert response.status_code == 201


@pytest.fixture
def student(client):
    return make_user(client, "Alex Buff", "alex@buffs.wtamu.edu")


@pytest.fixture
def other_student(client):
    return make_user(client, "Jordan Buff", "jordan@buffs.wtamu.edu")


@pytest.fixture
def admin(client, session_factory):
    headers = make_user(client, "Admin Person", "admin@wtamu.edu")
    with session_factory() as db:
        promote_to_admin(db, "admin@wtamu.edu")
    return headers
