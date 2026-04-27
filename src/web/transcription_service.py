"""Shared service helpers for Web and JSON transcription requests."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

from src.core.handoff_bridge import (
    build_handoff_payload,
    get_default_handoff_output_path,
    get_default_handoff_text_path,
    save_handoff_bundle,
)
from src.core.pipeline import AudioChunk, TranscriptionPipeline
from src.io.audio import (
    AudioEnvironmentError,
    AudioInputError,
    AudioTranscriptionError,
    SUPPORTED_AUDIO_EXTENSIONS,
    ensure_ffmpeg_available,
    normalize_audio_for_transcription,
    validate_audio_file,
    validate_model_name,
)

LOGGER = logging.getLogger(__name__)
WEB_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
WEB_MAX_AUDIO_SECONDS = 5 * 60
WEB_FFPROBE_TIMEOUT_SECONDS = 10
WEB_FFMPEG_TIMEOUT_SECONDS = 30
GENERIC_INPUT_ERROR = "入力された音声ファイルを処理できませんでした。ファイル形式とサイズを確認してください。"
GENERIC_ENVIRONMENT_ERROR = "サーバー側の音声処理環境でエラーが発生しました。"
GENERIC_TRANSCRIPTION_ERROR = "文字起こし処理に失敗しました。"


@dataclass(frozen=True)
class WebTranscriptionRequest:
    """Normalized request parameters for one Web transcription job."""

    raw_bytes: bytes
    filename: str
    model_name: str = "small"
    language: str | None = None
    command_only: bool = False
    save_handoff: bool = False
    source: str = "web"
    success_message: str | None = None


@dataclass(frozen=True)
class WebTranscriptionResponse:
    """Normalized response payload for one Web transcription job."""

    message: str
    transcript: str
    command: str
    command_path: str
    command_text_path: str
    error: str
    status_code: int

    def to_payload(self) -> dict[str, str]:
        """Return the JSON/HTML payload shape expected by the current Web layer."""
        return {
            "message": self.message,
            "transcript": self.transcript,
            "command": self.command,
            "command_path": self.command_path,
            "command_text_path": self.command_text_path,
            "error": self.error,
        }


def get_upload_dir() -> Path:
    """Return the upload directory for the web UI."""
    project_root = Path(__file__).resolve().parents[2]
    upload_dir = project_root / ".cache" / "web_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def build_temp_upload_path(filename: str) -> Path:
    """Return a unique temporary path for an uploaded audio file."""
    upload_dir = get_upload_dir()
    safe_name = secure_filename(filename) or "upload.wav"
    stem = Path(safe_name).stem or "upload"
    suffix = Path(safe_name).suffix or ".wav"
    return upload_dir / f"{stem}_{uuid4().hex}{suffix}"


def validate_upload_payload(raw_bytes: bytes, filename: str) -> None:
    """Validate upload metadata before writing the temporary file."""
    if not raw_bytes:
        raise AudioInputError("uploaded audio file is empty")
    if len(raw_bytes) > WEB_MAX_UPLOAD_BYTES:
        raise AudioInputError("uploaded audio file exceeds the web upload size limit")
    safe_name = secure_filename(filename) or "upload.wav"
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        raise AudioInputError("unsupported uploaded audio file extension")


def validate_uploaded_audio_content(audio_path: Path) -> None:
    """Use ffprobe to confirm the upload is readable audio with bounded duration."""
    validate_audio_file(audio_path)
    if shutil.which("ffprobe") is None:
        raise AudioEnvironmentError("ffprobe is not installed or not found in PATH")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(audio_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=WEB_FFPROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioInputError("uploaded audio metadata probe timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise AudioInputError("uploaded file is not readable audio") from exc

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise AudioInputError("uploaded audio duration could not be read") from exc

    duration_value = payload.get("format", {}).get("duration")
    if duration_value in {None, "", "N/A"}:
        return
    try:
        duration = float(duration_value)
    except (TypeError, ValueError) as exc:
        raise AudioInputError("uploaded audio duration could not be read") from exc
    if duration <= 0:
        raise AudioInputError("uploaded audio duration must be greater than zero")
    if duration > WEB_MAX_AUDIO_SECONDS:
        raise AudioInputError("uploaded audio duration exceeds the web processing limit")


def process_web_transcription(request_data: WebTranscriptionRequest) -> WebTranscriptionResponse:
    """Run one Web transcription request and normalize the response payload."""
    temp_path = build_temp_upload_path(request_data.filename)
    normalized_path = temp_path.with_suffix(".normalized.wav")

    transcript = ""
    command = ""
    command_path = ""
    command_text_path = ""
    error = ""
    status_code = 200

    try:
        validate_upload_payload(request_data.raw_bytes, request_data.filename)
        validate_model_name(request_data.model_name)
        ensure_ffmpeg_available()
        temp_path.write_bytes(request_data.raw_bytes)
        validate_uploaded_audio_content(temp_path)
        audio_path = temp_path
        if temp_path.suffix.lower() == ".webm":
            audio_path = normalize_audio_for_transcription(
                temp_path,
                normalized_path,
                timeout_seconds=WEB_FFMPEG_TIMEOUT_SECONDS,
            )
        pipeline = TranscriptionPipeline(model_name=request_data.model_name)
        transcript = pipeline.transcribe_chunk(
            AudioChunk(path=audio_path, source=request_data.source),
            language=request_data.language,
        )
        payload = build_handoff_payload(transcript)
        command = "" if payload is None else payload.command
        if request_data.save_handoff:
            saved_paths = save_handoff_bundle(
                transcript,
                json_path=get_default_handoff_output_path(source=request_data.source),
                text_path=get_default_handoff_text_path(source=request_data.source),
            )
            if saved_paths is not None:
                command_path = str(saved_paths.json_path)
                command_text_path = str(saved_paths.text_path)
    except AudioInputError as exc:
        LOGGER.info("Rejected web transcription input: %s", exc)
        error = GENERIC_INPUT_ERROR
        status_code = 400
    except AudioEnvironmentError as exc:
        LOGGER.exception("Web transcription environment failure: %s", exc)
        error = GENERIC_ENVIRONMENT_ERROR
        status_code = 500
    except AudioTranscriptionError as exc:
        LOGGER.exception("Web transcription failure: %s", exc)
        error = GENERIC_TRANSCRIPTION_ERROR
        status_code = 500
    finally:
        if temp_path.exists():
            temp_path.unlink()
        if normalized_path.exists():
            normalized_path.unlink()

    return WebTranscriptionResponse(
        message=(
            ""
            if error
            else (
                "音声を認識できませんでした。"
                if not transcript
                else (request_data.success_message or "文字起こしが完了しました。")
            )
        ),
        transcript="" if request_data.command_only else transcript,
        command=command,
        command_path=command_path,
        command_text_path=command_text_path,
        error=error,
        status_code=status_code,
    )
