import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Set the DATABASE_URL environment variable to use a different database file.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lost_and_found.db")

# check_same_thread=False lets FastAPI use the connection across threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def find_missing_columns(engine) -> list[str]:
    """List columns our models define that the database file doesn't have yet.

    create_all() creates missing tables but never changes existing ones, so a
    database made by an older version of the app can be missing new columns.
    """
    inspector = inspect(engine)
    missing = []
    for table in Base.metadata.sorted_tables:
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        missing += [f"{table.name}.{c.name}" for c in table.columns if c.name not in existing]
    return missing


def get_db():
    """FastAPI dependency that opens a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
