"""
Audio Transcription Service for NoteMate AI.
Uses faster-whisper for fast, local, private speech-to-text processing on CPU or GPU.
"""

import os
import tempfile
from typing import Dict, Any, Optional

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aac"}


class AudioService:
    def __init__(self):
        self.model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny")
        self.device = os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        self._model = None

    def _get_model(self):
        """Lazy loader for faster-whisper model."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=os.path.join(tempfile.gettempdir(), "notemate_whisper_cache"),
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize faster-whisper model ({self.model_size}): {str(e)}"
                )
        return self._model

    def is_supported_file(self, filename: str) -> bool:
        ext = os.path.splitext(filename.lower())[1]
        return ext in SUPPORTED_AUDIO_EXTENSIONS

    def transcribe_file_path(self, file_path: str) -> Dict[str, Any]:
        """Transcribe an audio file saved on disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("Uploaded audio file is empty (0 bytes).")

        model = self._get_model()
        segments, info = model.transcribe(file_path, beam_size=5)

        transcript_segments = []
        for segment in segments:
            transcript_segments.append(segment.text.strip())

        full_transcript = " ".join(transcript_segments).strip()

        return {
            "transcript": full_transcript,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration_seconds": round(info.duration, 2),
        }

    def transcribe_bytes(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Transcribe audio from in-memory byte buffer."""
        ext = os.path.splitext(filename)[1] or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(file_bytes)

        try:
            return self.transcribe_file_path(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass


audio_service = AudioService()
