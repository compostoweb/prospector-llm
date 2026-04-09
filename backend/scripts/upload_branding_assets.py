"""
scripts/upload_branding_assets.py

Faz upload dos assets de branding (logo) para o MinIO e configura
COMPOSTO_WEB_LOGO_EMAIL_URL no arquivo .env do ambiente ativo.

Uso:
    ENV=dev python scripts/upload_branding_assets.py
    ENV=prod python scripts/upload_branding_assets.py

O script:
1. Faz upload de compostoweb-logo-primary-white-bg.webp para branding/compostoweb-logo-email.webp
2. Aplica política de leitura pública no prefixo branding/ do bucket
3. Imprime a URL pública
4. Atualiza COMPOSTO_WEB_LOGO_EMAIL_URL no .env.<ENV>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import boto3
import structlog
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from core.config import settings
from core.logging import configure_logging

configure_logging()
logger = structlog.get_logger()

LOGO_KEY = "branding/compostoweb-logo-email.webp"
LOGO_PATH = BACKEND_ROOT / "assets" / "branding" / "compostoweb-logo-primary-white-bg.webp"


def _set_public_read_policy(client: boto3.client, bucket: str) -> None:
    """Define política de leitura pública no prefixo branding/ do bucket."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/branding/*"],
            }
        ],
    }
    try:
        client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        logger.info("s3.branding_policy_applied", bucket=bucket)
    except ClientError as exc:
        logger.warning("s3.branding_policy_skipped", error=str(exc))


def _update_env_file(env_path: Path, logo_url: str) -> None:
    """Atualiza ou adiciona COMPOSTO_WEB_LOGO_EMAIL_URL no arquivo .env."""
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    line = f"COMPOSTO_WEB_LOGO_EMAIL_URL={logo_url}"
    if re.search(r"^COMPOSTO_WEB_LOGO_EMAIL_URL=", content, re.MULTILINE):
        content = re.sub(
            r"^COMPOSTO_WEB_LOGO_EMAIL_URL=.*$",
            line,
            content,
            flags=re.MULTILINE,
        )
    else:
        content = content.rstrip("\n") + f"\n{line}\n"
    env_path.write_text(content, encoding="utf-8")
    logger.info("env.logo_url_updated", path=str(env_path), url=logo_url)


def main() -> None:
    if not settings.S3_ENDPOINT_URL or not settings.S3_ACCESS_KEY:
        logger.error("s3.not_configured", msg="S3_ENDPOINT_URL e S3_ACCESS_KEY são obrigatórios.")
        sys.exit(1)

    if not LOGO_PATH.exists():
        logger.error("branding.logo_missing", path=str(LOGO_PATH))
        sys.exit(1)

    client = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )

    _set_public_read_policy(client, settings.S3_BUCKET)

    logo_bytes = LOGO_PATH.read_bytes()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=LOGO_KEY,
        Body=logo_bytes,
        ContentType="image/webp",
    )
    logger.info("s3.logo_uploaded", key=LOGO_KEY, size=len(logo_bytes))

    public_url = f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET}/{LOGO_KEY}"
    print(f"\nLogo URL: {public_url}\n")

    env_file = BACKEND_ROOT / f".env.{settings.ENV}"
    _update_env_file(env_file, public_url)
    print(f"COMPOSTO_WEB_LOGO_EMAIL_URL atualizado em {env_file.name}")


if __name__ == "__main__":
    main()
