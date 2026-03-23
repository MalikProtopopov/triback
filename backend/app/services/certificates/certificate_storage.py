"""S3 access for certificate PDFs and template assets."""

from __future__ import annotations

import contextlib

import structlog

from app.core.config import settings
from app.services import file_service

logger = structlog.get_logger(__name__)


async def download_s3_bytes(s3_key: str | None) -> bytes | None:
    if not s3_key:
        return None
    try:
        session = file_service._get_s3_session()
        async with session.client(**file_service._s3_client_kwargs()) as s3:
            resp = await s3.get_object(
                Bucket=settings.S3_BUCKET, Key=s3_key
            )
            body: bytes = await resp["Body"].read()
            return body
    except Exception:
        logger.warning("s3_asset_download_failed", s3_key=s3_key)
        return None


async def put_certificate_pdf(s3_key: str, pdf_bytes: bytes) -> None:
    session = file_service._get_s3_session()
    async with session.client(**file_service._s3_client_kwargs()) as s3:
        await s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )


async def delete_stored_file(s3_key: str | None) -> None:
    if not s3_key:
        return
    with contextlib.suppress(Exception):
        await file_service.delete_file(s3_key)
