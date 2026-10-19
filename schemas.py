import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


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


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    item_type: str
    location: str
    is_resolved: bool
    owner_id: int
    owner_name: str
    created_at: datetime
    updated_at: datetime
    photos: list[PhotoOut]
