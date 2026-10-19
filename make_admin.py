"""Promote a registered user to admin.

Admins can't sign themselves up; an existing admin (or whoever runs the server)
promotes an account from the command line instead:

    uv run python make_admin.py someone@wtamu.edu

The person must register through the website first. They'll see the admin
view the next time they load the page.
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import Base, SessionLocal, engine


def promote_to_admin(db: Session, email: str) -> models.User | None:
    """Give the user with this email the admin role. Returns None if no such user."""
    user = db.scalar(select(models.User).where(models.User.email == email.strip().lower()))
    if user is None:
        return None
    user.role = "admin"
    db.commit()
    return user


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: uv run python make_admin.py <email>")

    Base.metadata.create_all(bind=engine)  # works even on a brand-new database
    with SessionLocal() as db:
        user = promote_to_admin(db, sys.argv[1])
        if user is None:
            sys.exit(f"No user with email {sys.argv[1]!r}. Register on the website first.")
        print(f"{user.name} ({user.email}) is now an admin.")
