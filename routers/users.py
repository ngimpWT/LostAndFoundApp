from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user, require_admin
from database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.User).where(models.User.email == user_in.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    user = models.User(**user_in.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.UserOut)
def login_user(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == credentials.email))
    if (
        user is None
        or user.phone != credentials.phone
        or user.name.lower() != credentials.name.lower()
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Name, email, or phone is incorrect")
    return user


# Users' email and phone are also their login details, so they're private:
# you can see your own, and admins can see everyone's.


@router.get("", response_model=list[schemas.UserOut])
def list_users(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.scalars(select(models.User).order_by(models.User.id)).all()


# Declared before "/{user_id}" so "me" isn't mistaken for a user id.
@router.get("/me", response_model=schemas.UserOut)
def get_me(user: models.User = Depends(get_current_user)):
    """The logged-in user. The frontend uses this to check a saved session is still valid."""
    return user


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: int,
    viewer: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if viewer.id != user_id and viewer.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own account")
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user
