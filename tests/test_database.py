from sqlalchemy import create_engine, text

import models  # noqa: F401  (registers the tables on Base.metadata)
from database import Base, find_missing_columns


def test_fresh_database_has_no_missing_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    Base.metadata.create_all(bind=engine)
    assert find_missing_columns(engine) == []


def test_outdated_database_reports_missing_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    # An "items" table from before moderation was added (no status column).
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, title VARCHAR, description TEXT, "
            "item_type VARCHAR, location VARCHAR, is_resolved BOOLEAN, owner_id INTEGER, "
            "created_at DATETIME, updated_at DATETIME)"
        ))
    Base.metadata.create_all(bind=engine)  # adds the other tables, but can't change "items"
    assert find_missing_columns(engine) == ["items.status"]
