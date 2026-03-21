"""Audio input helpers."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import whisper


SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm"}


class AudioInputError(ValueError):
    """Raised when the user provides an invalid audio input."""


class AudioEnvironmentError(RuntimeError):
    """Raised when the local runtime environment is not ready."""


class AudioTranscriptionError(RuntimeError):
    """Raised when Whisper fails while transcribing."""


def get_model_dir() -> Path:
    """Return the local directory used for Whisper model files."""
    project_root = Path(__file__).resolve().parents[2]
    model_dir = project_root / "models" / "whisper"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


def ensure_ffmpeg_available() -> None:
    """Ensure ffmpeg is available in the local environment."""
    if shutil.which("ffmpeg") is None:
        raise AudioEnvironmentError("ffmpeg is not installed or not found in PATH")


def validate_audio_file(audio_path: Path) -> None:
    """Validate the local audio file path."""
    if not audio_path.is_file():
        raise AudioInputError(f"audio file not found: {audio_path}")

    if audio_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise AudioInputError(
            "unsupported audio file extension. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}"
        )


def validate_model_name(model_name: str) -> None:
    """Validate the Whisper model name before loading."""
    if model_name not in whisper.available_models():
        raise AudioInputError(f"invalid Whisper model name: {model_name}")


def load_transcription_model(model_name: str = "small") -> Any:
    """Load a Whisper model from the local model directory."""
    validate_model_name(model_name)

    try:
        return whisper.load_model(model_name, download_root=str(get_model_dir()))
    except Exception as exc:
        raise AudioEnvironmentError(
            f"failed to load Whisper model '{model_name}': {exc}"
        ) from exc


def transcribe_file(audio_path: Path, model: Any, language: str | None = None) -> str:
    """Transcribe a local audio file with a loaded Whisper model."""
    validate_audio_file(audio_path)
    ensure_ffmpeg_available()

    options: dict[str, Any] = {}
    if language:
        options["language"] = language

    try:
        result = model.transcribe(str(audio_path), **options)
    except RuntimeError as exc:
        message = str(exc).lower()
        if "cuda" in message or "cudnn" in message or "torch" in message:
            raise AudioEnvironmentError(f"runtime environment error: {exc}") from exc
        raise AudioTranscriptionError(f"transcription runtime failed: {exc}") from exc
    except Exception as exc:
        raise AudioTranscriptionError(f"transcription failed: {exc}") from exc

    return result.get("text", "").strip()
