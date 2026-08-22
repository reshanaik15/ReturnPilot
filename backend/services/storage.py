"""
Supabase Storage integration for return-evidence photo uploads.

Uploads customer-submitted damage photos to a public Supabase Storage
bucket and returns the public URL, for use by verify_damage_photo().

Talks to Supabase Storage's REST API directly via httpx rather than the
`supabase` SDK: the pinned SDK version (2.3.4) only accepts legacy JWT-style
API keys and rejects Supabase's newer `sb_publishable_...`/`sb_secret_...`
key format at the client-side validation step, before any request is sent.
"""

import logging
import uuid

import httpx

from config import settings

logger = logging.getLogger(__name__)

BUCKET_NAME = "returns-evidence"


async def _ensure_bucket(client: httpx.AsyncClient, headers: dict) -> None:
    """Create the returns-evidence bucket with public read access if it doesn't exist yet."""
    response = await client.get(
        f"{settings.supabase_url}/storage/v1/bucket/{BUCKET_NAME}",
        headers=headers,
    )
    if response.status_code == 200:
        return

    response = await client.post(
        f"{settings.supabase_url}/storage/v1/bucket",
        headers=headers,
        json={
            "id": BUCKET_NAME,
            "name": BUCKET_NAME,
            "public": True,
            "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
        },
    )
    if response.status_code not in (200, 201):
        # Bucket may have been created concurrently, or already exists under a race
        if "already exists" not in response.text.lower():
            response.raise_for_status()
    logger.info(f"Created Supabase Storage bucket '{BUCKET_NAME}'")


async def upload_photo(
    file_bytes: bytes,
    return_id: str,
    content_type: str = "image/jpeg",
) -> str:
    """
    Upload return-evidence photo bytes to Supabase Storage and return its public URL.
    """
    headers = {
        "Authorization": f"Bearer {settings.supabase_key}",
        "apikey": settings.supabase_key,
    }
    ext = "jpg" if "jpeg" in content_type else content_type.split("/")[-1]
    path = f"{return_id}/{uuid.uuid4().hex}.{ext}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        await _ensure_bucket(client, headers)

        response = await client.post(
            f"{settings.supabase_url}/storage/v1/object/{BUCKET_NAME}/{path}",
            headers={**headers, "Content-Type": content_type, "x-upsert": "true"},
            content=file_bytes,
        )
        response.raise_for_status()

    return f"{settings.supabase_url}/storage/v1/object/public/{BUCKET_NAME}/{path}"
