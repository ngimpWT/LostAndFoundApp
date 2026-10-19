from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user, get_optional_user
from database import get_db

router = APIRouter(prefix="/items", tags=["items"])


def get_item_or_404(item_id: int, db: Session) -> models.Item:
    item = db.get(models.Item, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


def get_visible_item(item_id: int, user: models.User | None, db: Session) -> models.Item:
    """Load an item the viewer is allowed to see.

    Approved posts are public. Pending and rejected posts can only be seen by
    their owner and by admins; everyone else gets a 404 as if it didn't exist.
    """
    item = get_item_or_404(item_id, db)
    if item.status == "approved":
        return item
    if user is not None and (user.id == item.owner_id or user.role == "admin"):
        return item
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")


def get_owned_item(item_id: int, user: models.User, db: Session) -> models.Item:
    """Load an item, making sure it exists and belongs to the current user."""
    item = get_item_or_404(item_id, db)
    if item.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only change your own posts")
    return item


@router.post("", response_model=schemas.ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    item_in: schemas.ItemIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only students can post items")

    item = models.Item(**item_in.model_dump(), owner_id=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


NEWEST_FIRST = (models.Item.created_at.desc(), models.Item.id.desc())


@router.get("", response_model=list[schemas.ItemOut])
def list_items(db: Session = Depends(get_db)):
    """The public campus feed: only posts an admin has approved."""
    query = select(models.Item).where(models.Item.status == "approved").order_by(*NEWEST_FIRST)
    return db.scalars(query).all()


# Declared before "/{item_id}" so "mine" isn't mistaken for an item id.
@router.get("/mine", response_model=list[schemas.ItemOut])
def list_my_items(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All of the current user's posts, whatever their moderation status."""
    query = select(models.Item).where(models.Item.owner_id == user.id).order_by(*NEWEST_FIRST)
    return db.scalars(query).all()


@router.get("/{item_id}", response_model=schemas.ItemOut)
def get_item(
    item_id: int,
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return get_visible_item(item_id, user, db)


@router.put("/{item_id}", response_model=schemas.ItemOut)
def update_item(
    item_id: int,
    item_in: schemas.ItemIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_owned_item(item_id, user, db)
    for field, value in item_in.model_dump().items():
        setattr(item, field, value)
    item.status = "pending"  # changed posts must be reviewed again
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}/resolve", response_model=schemas.ItemOut)
def resolve_item(
    item_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_owned_item(item_id, user, db)
    item.is_resolved = True
    db.commit()
    db.refresh(item)
    return item
