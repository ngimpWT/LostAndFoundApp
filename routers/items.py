from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

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


def with_details(query):
    """Load each listed post's owner and photos in bulk.

    Without this, SQLAlchemy runs one extra query per post the first time its
    owner or photos are used ("N+1 queries"), which gets slow as the list grows.
    """
    return query.options(selectinload(models.Item.owner), selectinload(models.Item.photos))


@router.get("", response_model=list[schemas.ItemOut])
def list_items(db: Session = Depends(get_db)):
    """The public campus feed: only posts an admin has approved."""
    query = select(models.Item).where(models.Item.status == "approved").order_by(*NEWEST_FIRST)
    return db.scalars(with_details(query)).all()


# The routes below are declared before "/{item_id}" so words like "search"
# and "mine" aren't mistaken for an item id.


def keyword_matches(word: str):
    """A condition that is true when the word appears anywhere in a post.

    icontains() is a case-insensitive "LIKE %word%". autoescape=True makes
    characters like % and _ match literally instead of acting as wildcards.
    """
    return or_(
        models.Item.title.icontains(word, autoescape=True),
        models.Item.description.icontains(word, autoescape=True),
        models.Item.location.icontains(word, autoescape=True),
        models.Item.photos.any(models.Photo.caption.icontains(word, autoescape=True)),
    )


@router.get("/search", response_model=list[schemas.ItemOut])
def search_items(
    params: Annotated[schemas.ItemSearch, Query()],
    db: Session = Depends(get_db),
):
    """Search approved posts by keyword, item type, and campus location (FR-5)."""
    query = select(models.Item).where(models.Item.status == "approved")

    for word in params.q.split():
        query = query.where(keyword_matches(word))
    if params.item_type:
        query = query.where(models.Item.item_type == params.item_type)
    if params.location:
        query = query.where(models.Item.location.icontains(params.location, autoescape=True))
    if not params.include_resolved:
        query = query.where(models.Item.is_resolved.is_(False))

    return db.scalars(with_details(query.order_by(*NEWEST_FIRST))).all()


@router.get("/locations", response_model=list[str])
def list_locations(db: Session = Depends(get_db)):
    """Every campus location used by an approved post, for the search filter dropdown."""
    query = (
        select(models.Item.location)
        .where(models.Item.status == "approved")
        .distinct()
        .order_by(models.Item.location)
    )
    return db.scalars(query).all()


@router.get("/mine", response_model=list[schemas.ItemOut])
def list_my_items(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All of the current user's posts, whatever their moderation status."""
    query = select(models.Item).where(models.Item.owner_id == user.id).order_by(*NEWEST_FIRST)
    return db.scalars(with_details(query)).all()


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
