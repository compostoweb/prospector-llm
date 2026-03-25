"""
integrations/s3_client.py

Cliente S3 para armazenamento de arquivos no MinIO.

Responsabilidades:
  - Upload de arquivos (áudios, etc.)
  - Geração de URLs de acesso público
  - Deleção de objetos

Base URL: configurada via S3_ENDPOINT_URL (MinIO)
Auth:     S3_ACCESS_KEY + S3_SECRET_KEY
"""

from __future__ import annotations

import uuid

import boto3
import structlog
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from core.config import settings

logger = structlog.get_logger()


class S3Client:
    """Wrapper sobre boto3 S3 para MinIO."""

    def __init__(self) -> None:
        self._bucket = settings.S3_BUCKET
        self._endpoint = settings.S3_ENDPOINT_URL
        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=BotoConfig(signature_version="s3v4"),
        )

    def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str = "audio/mpeg",
    ) -> str:
        """
        Faz upload de bytes para o bucket.
        Retorna a URL pública do objeto.
        """
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        url = f"{self._endpoint}/{self._bucket}/{key}"
        logger.info("s3.uploaded", key=key, content_type=content_type)
        return url

    def upload_audio(
        self,
        data: bytes,
        tenant_id: str,
        filename: str,
        content_type: str = "audio/mpeg",
    ) -> tuple[str, str]:
        """
        Faz upload de arquivo de áudio.
        Retorna (key, url).
        """
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "mp3"
        key = f"audio/{tenant_id}/{uuid.uuid4()}.{ext}"
        url = self.upload_bytes(data, key, content_type)
        return key, url

    def delete_object(self, key: str) -> None:
        """Remove um objeto do bucket."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("s3.deleted", key=key)
        except ClientError as exc:
            logger.error("s3.delete_error", key=key, error=str(exc))
            raise

    def get_public_url(self, key: str) -> str:
        """Retorna a URL pública para um objeto."""
        return f"{self._endpoint}/{self._bucket}/{key}"

    def head_object(self, key: str) -> dict | None:
        """Verifica se um objeto existe. Retorna metadados ou None."""
        try:
            return self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError:
            return None


def _create_s3_client() -> S3Client | None:
    """Cria o singleton se configuração S3 estiver disponível."""
    if settings.S3_ENDPOINT_URL and settings.S3_ACCESS_KEY:
        return S3Client()
    logger.warning("s3.not_configured", msg="S3/MinIO não configurado.")
    return None


s3_client: S3Client | None = _create_s3_client()
