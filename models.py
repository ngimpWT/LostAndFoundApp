from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), default="student")  # "student" or "admin"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    items: Mapped[list["Item"]] = relationship(back_populates="owner")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    # Columns used by search filters are indexed so lookups stay fast.
    item_type: Mapped[str] = mapped_column(String(10), index=True)  # "lost" or "found"
    location: Mapped[str] = mapped_column(String(100), index=True)  # campus location
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    # Moderation status: "pending" until an admin reviews it, then "approved" or "rejected".
    # Only approved posts appear in the public feed.
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    owner: Mapped[User] = relationship(back_populates="items")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="item", order_by="Photo.id", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="item", order_by="Review.id", cascade="all, delete-orphan"
    )

    @property
    def owner_name(self) -> str:
        return self.owner.name


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    caption: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(100))  # name of the file saved in uploads/
    content_type: Mapped[str] = mapped_column(String(50))  # e.g. "image/png"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    item: Mapped[Item] = relationship(back_populates="photos")

    @property
    def url(self) -> str:
        return f"/photos/{self.id}/image"


class Review(Base):
    """An admin's moderation decision on an item post (FR-4)."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(10))  # "approve" or "reject"
    comments: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    item: Mapped[Item] = relationship(back_populates="reviews")
    admin: Mapped[User] = relationship()

    @property
    def admin_name(self) -> str:
        return self.admin.name
