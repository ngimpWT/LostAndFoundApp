from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(prefix="/items", tags=["items"])


def get_item_or_404(item_id: int, db: Session) -> models.Item:
    item = db.get(models.Item, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


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


@router.get("", response_model=list[schemas.ItemOut])
def list_items(db: Session = Depends(get_db)):
    query = select(models.Item).order_by(models.Item.created_at.desc(), models.Item.id.desc())
    return db.scalars(query).all()


@router.get("/{item_id}", response_model=schemas.ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return get_item_or_404(item_id, db)


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
