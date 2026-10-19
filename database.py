import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Set the DATABASE_URL environment variable to use a different database file.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lost_and_found.db")

# check_same_thread=False lets FastAPI use the connection across threads.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that opens a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
