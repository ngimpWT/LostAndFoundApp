import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user, get_optional_user
from database import get_db
from routers.items import get_owned_item, get_visible_item

router = APIRouter(tags=["photos"])

UPLOAD_DIR = Path("uploads")
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB


def detect_image_type(contents: bytes) -> tuple[str, str] | None:
    """Look at a file's first bytes to tell which image format it really is.

    Returns (content_type, file_extension), or None if it isn't a supported image.
    We don't trust the browser's content type, since it can be faked.
    """
    if contents.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if contents.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if contents.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif", ".gif"
    if contents[:4] == b"RIFF" and contents[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def get_photo_or_404(photo_id: int, db: Session) -> models.Photo:
    photo = db.get(models.Photo, photo_id)
    if photo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    return photo


@router.post(
    "/items/{item_id}/photos",
    response_model=schemas.PhotoOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_photo(
    item_id: int,
    file: UploadFile = File(),
    caption: str = Form(max_length=200),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_owned_item(item_id, user, db)

    caption = caption.strip()
    if not caption:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "caption must not be blank")

    # Read one byte past the limit so we can tell if the file is too big.
    contents = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(contents) > MAX_PHOTO_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Photos must be 5 MB or smaller")

    image_type = detect_image_type(contents)
    if image_type is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Photos must be JPEG, PNG, GIF, or WebP images"
        )
    content_type, extension = image_type

    # Save under a random name so uploads never overwrite each other.
    filename = uuid.uuid4().hex + extension
    UPLOAD_DIR.mkdir(exist_ok=True)
    (UPLOAD_DIR / filename).write_bytes(contents)

    photo = models.Photo(
        item_id=item.id, caption=caption, filename=filename, content_type=content_type
    )
    db.add(photo)
    item.status = "pending"  # new photos must be reviewed before they're public
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/items/{item_id}/photos", response_model=list[schemas.PhotoOut])
def list_photos(
    item_id: int,
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return get_visible_item(item_id, user, db).photos


@router.get("/photos/{photo_id}/image")
def get_photo_image(
    photo_id: int,
    user: models.User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    photo = get_photo_or_404(photo_id, db)
    get_visible_item(photo.item_id, user, db)  # photos of hidden posts stay hidden
    if not (UPLOAD_DIR / photo.filename).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo file is missing")
    return FileResponse(UPLOAD_DIR / photo.filename, media_type=photo.content_type)


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    photo = get_photo_or_404(photo_id, db)
    get_owned_item(photo.item_id, user, db)  # only the post's owner may delete

    (UPLOAD_DIR / photo.filename).unlink(missing_ok=True)
    db.delete(photo)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
