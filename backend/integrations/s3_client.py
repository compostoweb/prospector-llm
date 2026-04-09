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

import io
import uuid

import boto3
import structlog
from boto3.s3.transfer import TransferConfig
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
        Usa multipart transfer para arquivos grandes (> 8 MB).
        Retorna a URL pública do objeto.
        """
        transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            multipart_chunksize=8 * 1024 * 1024,
            use_threads=True,
        )
        self._client.upload_fileobj(
            io.BytesIO(data),
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
            Config=transfer_config,
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

    def get_bytes(self, key: str) -> tuple[bytes, str]:
        """Retorna (conteúdo, content_type) de um objeto do bucket."""
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        data: bytes = response["Body"].read()
        content_type: str = response.get("ContentType", "application/octet-stream")
        return data, content_type

    def get_object_range(self, key: str, range_header: str) -> dict:
        """
        Busca um intervalo de bytes de um objeto (para streaming de vídeo com Range requests).
        Retorna dict com 'body' (bytes), 'content_range' (str), 'content_length' (int),
        'total_size' (int) e 'content_type' (str).
        """
        response = self._client.get_object(Bucket=self._bucket, Key=key, Range=range_header)
        body: bytes = response["Body"].read()
        return {
            "body": body,
            "content_range": response.get("ContentRange", ""),
            "content_length": len(body),
            "total_size": response.get("ContentLength", len(body)),
            "content_type": response.get("ContentType", "video/mp4"),
        }

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
