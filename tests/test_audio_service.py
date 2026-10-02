"""
Unit tests for AudioService validation, format support, and error handling.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.services.audio_service import AudioService
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_supported_audio_formats():
    service = AudioService()
    assert service.is_supported_file("recording.mp3") is True
    assert service.is_supported_file("lecture.wav") is True
    assert service.is_supported_file("voice.m4a") is True
    assert service.is_supported_file("meeting.ogg") is True
    assert service.is_supported_file("clip.webm") is True
    assert service.is_supported_file("document.pdf") is False
    assert service.is_supported_file("malicious.exe") is False


def test_transcribe_missing_file_raises_error():
    service = AudioService()
    with pytest.raises(FileNotFoundError):
        service.transcribe_file_path("non_existent_audio_file_12345.mp3")


def test_transcribe_empty_file_raises_error():
    service = AudioService()
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError) as exc:
            service.transcribe_file_path(tmp_path)
        assert "empty" in str(exc.value).lower()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_upload_invalid_audio_type_endpoint(client):
    """Verify endpoint rejects non-audio file extensions with HTTP 400."""
    response = client.post(
        "/api/audio/transcribe",
        files={"file": ("notes.txt", b"plain text content", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported audio format" in response.json()["detail"]


def test_upload_empty_audio_endpoint(client):
    """Verify endpoint rejects 0-byte audio file with HTTP 400."""
    response = client.post(
        "/api/audio/transcribe",
        files={"file": ("recording.mp3", b"", "audio/mpeg")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
