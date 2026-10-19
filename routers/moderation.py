from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user, require_admin
from database import get_db
from routers.items import get_item_or_404

router = APIRouter(tags=["moderation"])

# The status an item ends up in after each kind of decision.
STATUS_AFTER = {"approve": "approved", "reject": "rejected"}


@router.get("/moderation/pending", response_model=list[schemas.ItemOut])
def list_pending_items(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """The admin review queue, oldest first so nothing waits too long."""
    query = (
        select(models.Item)
        .where(models.Item.status == "pending")
        .order_by(models.Item.created_at, models.Item.id)
    )
    return db.scalars(query).all()


@router.post(
    "/items/{item_id}/reviews",
    response_model=schemas.ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def review_item(
    item_id: int,
    review_in: schemas.ReviewIn,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Log an admin's approve/reject decision and update the item's status."""
    item = get_item_or_404(item_id, db)

    review = models.Review(item_id=item.id, admin_id=admin.id, **review_in.model_dump())
    db.add(review)
    item.status = STATUS_AFTER[review_in.decision]
    db.commit()
    db.refresh(review)
    return review


@router.get("/items/{item_id}/reviews", response_model=list[schemas.ReviewOut])
def list_reviews(
    item_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A post's review history, visible to its owner and to admins."""
    item = get_item_or_404(item_id, db)
    if user.role != "admin" and user.id != item.owner_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only see reviews of your own posts")
    return item.reviews
