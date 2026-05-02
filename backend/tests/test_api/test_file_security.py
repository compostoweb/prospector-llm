from __future__ import annotations

import uuid

from core.file_security import detect_audio_content_type, pick_audio_extension, sanitize_download_filename
from models.audio_file import AudioFile


def test_detect_audio_content_type_from_magic_bytes() -> None:
    assert detect_audio_content_type(b"ID3\x04\x00\x00rest") == "audio/mpeg"
    assert detect_audio_content_type(b"RIFFxxxxWAVErest") == "audio/wav"
    assert detect_audio_content_type(b"OggSrest") == "audio/ogg"


def test_pick_audio_extension_prefers_content_type() -> None:
    assert pick_audio_extension(content_type="audio/wav", original_filename="voice.mp3") == ".wav"


def test_sanitize_download_filename_blocks_header_injection() -> None:
    assert sanitize_download_filename('..\\demo\r\nvoice.mp3', fallback='file.bin') == 'demo__voice.mp3'


def test_audio_file_response_can_use_presigned_url(monkeypatch) -> None:
    from api.routes import audio_files as audio_files_route

    audio_file = AudioFile(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="Demo",
        s3_key="audio/tenant/demo.mp3",
        url="https://minio.local/prospector/audio/tenant/demo.mp3",
        content_type="audio/mpeg",
        size_bytes=1234,
        language="pt-BR",
    )

    class _FakeS3Client:
        def generate_presigned_url(self, key: str, expiry_seconds: int = 300) -> str:
            assert key == "audio/tenant/demo.mp3"
            assert expiry_seconds == audio_files_route.settings.S3_PRIVATE_URL_EXPIRY_SECONDS
            return "https://signed.example/audio/demo.mp3?signature=abc"

    monkeypatch.setattr(audio_files_route, "s3_client", _FakeS3Client())

    response = audio_files_route._build_audio_file_response(audio_file)

    assert response.url.startswith("https://signed.example/audio/demo.mp3")