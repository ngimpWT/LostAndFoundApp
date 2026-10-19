from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

import models
from database import get_db


def get_current_user(
    x_user_id: int | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    """Identify the logged-in user from the X-User-Id header.

    The frontend sends this header after a successful login. This keeps the
    project simple for learning purposes; a real app would use a signed token
    so users can't pretend to be someone else.
    """
    user = db.get(models.User, x_user_id) if x_user_id is not None else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "You must be logged in")
    return user


def get_optional_user(
    x_user_id: int | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User | None:
    """Like get_current_user, but returns None for visitors who aren't logged in."""
    if x_user_id is None:
        return None
    return get_current_user(x_user_id, db)


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can do this")
    return user
