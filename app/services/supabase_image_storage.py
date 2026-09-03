"""
Supabase Storage (S3-compatible) - a third DRONE_IMAGE_STORAGE option
alongside AWS S3 (app.services.ai_service.AWSAIService.upload_to_s3) and
local disk (app.services.local_image_storage.save_image_locally).

Supabase Storage exposes a genuine S3-compatible API (separate "S3 Access
Keys" issued per-project in the Supabase dashboard - distinct from the
project's anon/service-role JWT keys, and distinct from
app.db_config.EnterpriseDBConfig's SUPABASE_URL, which is only used to build
a Postgres connection string). This reuses boto3's S3 client exactly like
the AWS path, just pointed at Supabase's endpoint.

Important: the returned URL is NOT the S3 endpoint. Supabase serves public
objects through its own REST gateway (/storage/v1/object/public/...), not
the raw S3 endpoint used for uploads. This only works for public buckets -
private buckets would need a signed-URL call instead (not implemented here).
"""

import boto3

from app.config import settings


def save_image_to_supabase(content: bytes, file_name: str, folder: str) -> str:
    key = f"{folder}/{file_name}"

    client = boto3.client(
        "s3",
        endpoint_url=settings.SUPABASE_STORAGE_ENDPOINT_URL,
        aws_access_key_id=settings.SUPABASE_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SUPABASE_STORAGE_SECRET_ACCESS_KEY,
        region_name="us-east-1",
    )
    client.put_object(
        Bucket=settings.SUPABASE_STORAGE_BUCKET,
        Key=key,
        Body=content,
        ContentType="image/jpeg",
    )

    return f"{settings.SUPABASE_PROJECT_URL}/storage/v1/object/public/{settings.SUPABASE_STORAGE_BUCKET}/{key}"
