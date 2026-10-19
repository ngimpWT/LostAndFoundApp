import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserCredentials(BaseModel):
    """The three fields a user provides to register or log in (FR-1)."""

    name: str
    email: EmailStr
    phone: str

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        if len(value) > 100:
            raise ValueError("name must be at most 100 characters")
        return value

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, value: str) -> str:
        return value.lower()

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, value: str) -> str:
        # Accept common formats like "(806) 555-0101" or "+1 806.555.0101",
        # then store just the digits so logins match regardless of formatting.
        if not re.fullmatch(r"[0-9+\-(). ]+", value):
            raise ValueError("phone may only contain digits, spaces, and + - ( ) .")
        digits = re.sub(r"\D", "", value)
        if not 7 <= len(digits) <= 15:
            raise ValueError("phone must contain 7 to 15 digits")
        return digits


class UserCreate(UserCredentials):
    role: Literal["student", "admin"] = "student"


class UserLogin(UserCredentials):
    pass


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    role: str
    created_at: datetime


def clean_text(value: str, field: str, max_length: int) -> str:
    """Trim whitespace and make sure a required text field isn't blank or too long."""
    value = value.strip()
    if not value:
        raise ValueError(f"{field} must not be blank")
    if len(value) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters")
    return value


class ItemIn(BaseModel):
    """Fields a student provides when creating or editing a post (FR-2)."""

    title: str
    description: str
    item_type: Literal["lost", "found"]
    location: str

    @field_validator("title")
    @classmethod
    def title_valid(cls, value: str) -> str:
        return clean_text(value, "title", 100)

    @field_validator("description")
    @classmethod
    def description_valid(cls, value: str) -> str:
        return clean_text(value, "description", 2000)

    @field_validator("location")
    @classmethod
    def location_valid(cls, value: str) -> str:
        return clean_text(value, "location", 100)


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    caption: str
    url: str
    created_at: datetime


class ItemSearch(BaseModel):
    """Query parameters for GET /items/search (FR-5). Every filter is optional."""

    q: str = Field("", max_length=100, description="Keywords; every word must match")
    item_type: Literal["lost", "found"] | None = None
    location: str = Field("", max_length=100, description="Partial campus location")
    include_resolved: bool = False

    @field_validator("q", "location")
    @classmethod
    def trimmed(cls, value: str) -> str:
        return value.strip()


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    item_type: str
    location: str
    is_resolved: bool
    status: str
    owner_id: int
    owner_name: str
    created_at: datetime
    updated_at: datetime
    photos: list[PhotoOut]


class ReviewIn(BaseModel):
    """An admin's decision on a pending post (FR-4)."""

    decision: Literal["approve", "reject"]
    comments: str = ""

    @field_validator("comments")
    @classmethod
    def comments_trimmed(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 1000:
            raise ValueError("comments must be at most 1000 characters")
        return value

    @model_validator(mode="after")
    def reject_needs_comments(self):
        # The student needs to know why their post was rejected.
        if self.decision == "reject" and not self.comments:
            raise ValueError("comments are required when rejecting a post")
        return self


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    admin_id: int
    admin_name: str
    decision: str
    comments: str
    reviewed_at: datetime
