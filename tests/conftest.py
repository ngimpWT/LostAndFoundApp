import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app


@pytest.fixture
def client():
    """A TestClient backed by a fresh in-memory database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def make_user(client, name, email, phone="806-555-0101", role="student"):
    """Register a user and return the headers that identify them to the API."""
    response = client.post("/users", json={"name": name, "email": email, "phone": phone, "role": role})
    assert response.status_code == 201
    return {"X-User-Id": str(response.json()["id"])}


@pytest.fixture
def student(client):
    return make_user(client, "Alex Buff", "alex@buffs.wtamu.edu")


@pytest.fixture
def other_student(client):
    return make_user(client, "Jordan Buff", "jordan@buffs.wtamu.edu")


@pytest.fixture
def admin(client):
    return make_user(client, "Admin Person", "admin@wtamu.edu", role="admin")
