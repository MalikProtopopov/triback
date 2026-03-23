"""File service — async S3 operations via aioboto3, image resize via Pillow."""

import io
import uuid
from typing import Any

import aioboto3
from fastapi import UploadFile
from PIL import Image

from app.core.config import settings
from app.core.exceptions import AppValidationError

IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
DOCUMENT_MIMES = IMAGE_MIMES | {"application/pdf"}


def build_media_url(s3_key: str | None) -> str | None:
    """Turn an S3 object key into a full public URL.

    Falls back to returning the raw key when ``S3_PUBLIC_URL`` is empty
    (e.g. during tests or when the variable is not yet configured).
    """
    if not s3_key:
        return None
    base = settings.S3_PUBLIC_URL
    if not base:
        return s3_key
    return f"{base.rstrip('/')}/{s3_key.lstrip('/')}"


def _get_s3_session() -> aioboto3.Session:
    return aioboto3.Session()


def _s3_client_kwargs() -> dict[str, Any]:
    return {
        "service_name": "s3",
        "endpoint_url": settings.S3_ENDPOINT_URL,
        "aws_access_key_id": settings.S3_ACCESS_KEY,
        "aws_secret_access_key": settings.S3_SECRET_KEY,
    }


async def upload_file(
    file: UploadFile,
    path: str,
    allowed_types: set[str] | None = None,
    max_size_mb: int = 5,
) -> str:
    """Upload a file to S3. Returns the S3 object key."""
    if allowed_types and file.content_type not in allowed_types:
        raise AppValidationError(
            f"Недопустимый тип файла: {file.content_type}. "
            f"Допустимые: {', '.join(sorted(allowed_types))}",
        )

    data = await file.read()

    if len(data) > max_size_mb * 1024 * 1024:
        raise AppValidationError(f"Файл превышает {max_size_mb} MB")

    ext = _extension_from_mime(file.content_type or "")
    key = f"{path}/{uuid.uuid4()}{ext}"

    session = _get_s3_session()
    async with session.client(**_s3_client_kwargs()) as s3:
        await s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=file.content_type or "application/octet-stream",
        )
    return key


async def get_presigned_url(s3_key: str, ttl: int = 600) -> str:
    """Generate a presigned GET URL for a private S3 object."""
    session = _get_s3_session()
    async with session.client(**_s3_client_kwargs()) as s3:
        url: str = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": s3_key},
            ExpiresIn=ttl,
        )
    return url


async def delete_file(s3_key: str) -> None:
    """Delete an object from S3."""
    session = _get_s3_session()
    async with session.client(**_s3_client_kwargs()) as s3:
        await s3.delete_object(Bucket=settings.S3_BUCKET, Key=s3_key)


def resize_image(
    data: bytes,
    max_size: tuple[int, int] = (800, 800),
    thumb_size: tuple[int, int] = (200, 200),
) -> tuple[bytes, bytes]:
    """Resize image to max_size and create a thumbnail. Returns (resized, thumbnail) as JPEG bytes."""
    opened = Image.open(io.BytesIO(data))
    img: Image.Image = opened.convert("RGB")

    resized = img.copy()
    resized.thumbnail(max_size, Image.Resampling.LANCZOS)
    buf_main = io.BytesIO()
    resized.save(buf_main, format="JPEG", quality=85)

    thumb = img.copy()
    thumb.thumbnail(thumb_size, Image.Resampling.LANCZOS)
    buf_thumb = io.BytesIO()
    thumb.save(buf_thumb, format="JPEG", quality=80)

    return buf_main.getvalue(), buf_thumb.getvalue()


async def upload_image_with_thumbnail(
    file: UploadFile,
    path: str,
    max_size_mb: int = 5,
) -> tuple[str, str]:
    """Upload an image to S3 with resize (800x800) and thumbnail (200x200).
    Returns (main_key, thumb_key).
    """
    if file.content_type not in IMAGE_MIMES:
        raise AppValidationError(
            f"Недопустимый тип файла: {file.content_type}. "
            f"Допустимые: {', '.join(sorted(IMAGE_MIMES))}",
        )

    data = await file.read()
    if len(data) > max_size_mb * 1024 * 1024:
        raise AppValidationError(f"Файл превышает {max_size_mb} MB")

    main_bytes, thumb_bytes = resize_image(data)

    file_id = str(uuid.uuid4())
    main_key = f"{path}/{file_id}.jpg"
    thumb_key = f"{path}/{file_id}_thumb.jpg"

    session = _get_s3_session()
    async with session.client(**_s3_client_kwargs()) as s3:
        await s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=main_key,
            Body=main_bytes,
            ContentType="image/jpeg",
        )
        await s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=thumb_key,
            Body=thumb_bytes,
            ContentType="image/jpeg",
        )

    return main_key, thumb_key


def _extension_from_mime(mime: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }
    return mapping.get(mime, ".bin")
