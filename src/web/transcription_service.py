"""Shared service helpers for Web and JSON transcription requests."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from werkzeug.utils import secure_filename

from src.core.events import emit_event, new_turn_id, text_payload_facts
from src.core.handoff_bridge import (
    build_handoff_payload,
    get_default_handoff_output_path,
    get_default_handoff_text_path,
    save_handoff_bundle,
)
from src.core.pipeline import AudioChunk, get_cached_transcription_pipeline
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
from src.io.microphone import has_detectable_speech

LOGGER = logging.getLogger(__name__)
WEB_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
WEB_MAX_AUDIO_SECONDS = 5 * 60
WEB_MIN_RECOGNIZABLE_AUDIO_SECONDS = 0.4
WEB_FFPROBE_TIMEOUT_SECONDS = 10
WEB_FFMPEG_TIMEOUT_SECONDS = 30
WEB_VAD_AGGRESSIVENESS = 2
WEB_DEBUG_ERROR_MAX_CHARS = 300
GENERIC_INPUT_ERROR = "入力された音声ファイルを処理できませんでした。ファイル形式とサイズを確認してください。"
GENERIC_ENVIRONMENT_ERROR = "サーバー側の音声処理環境でエラーが発生しました。"
GENERIC_TRANSCRIPTION_ERROR = "文字起こし処理に失敗しました。"
NO_RECOGNIZABLE_SPEECH_MESSAGE = "音声を認識できませんでした。"


@dataclass(frozen=True)
class WebTranscriptionRequest:
    """Normalized request parameters for one Web transcription job."""

    raw_bytes: bytes
    filename: str
    turn_id: str | None = None
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
    turn_id: str
    debug: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        """Return the JSON/HTML payload shape expected by the current Web layer."""
        return {
            "message": self.message,
            "transcript": self.transcript,
            "command": self.command,
            "command_path": self.command_path,
            "command_text_path": self.command_text_path,
            "error": self.error,
            "turn_id": self.turn_id,
            "debug": self.debug,
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


def probe_audio_duration(audio_path: Path) -> float | None:
    """Return ffprobe duration for a readable uploaded audio file."""
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
        detail = summarize_audio_tool_error(exc.stderr or exc.stdout)
        message = "uploaded file is not readable audio"
        if detail:
            message = f"{message}: {detail}"
        raise AudioInputError(message) from exc

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise AudioInputError("uploaded audio duration could not be read") from exc

    duration_value = payload.get("format", {}).get("duration")
    if duration_value in {None, "", "N/A"}:
        return None
    try:
        return float(duration_value)
    except (TypeError, ValueError) as exc:
        raise AudioInputError("uploaded audio duration could not be read") from exc


def validate_uploaded_audio_content(audio_path: Path) -> float | None:
    """Use ffprobe to confirm the upload is readable audio with bounded duration."""
    duration = probe_audio_duration(audio_path)
    if duration is None:
        return None
    if duration <= 0:
        raise AudioInputError("uploaded audio duration must be greater than zero")
    if duration > WEB_MAX_AUDIO_SECONDS:
        raise AudioInputError("uploaded audio duration exceeds the web processing limit")
    return duration


def summarize_audio_tool_error(message: str | None) -> str:
    """Return a short debug-safe ffmpeg/ffprobe error summary."""
    if not message:
        return ""
    normalized = " ".join(message.strip().split())
    normalized = re.sub(r"[A-Za-z]:[\\/][^\s]+", "[path]", normalized)
    normalized = re.sub(r"(?<!:)[\\/][^\s]+", "[path]", normalized)
    if len(normalized) > WEB_DEBUG_ERROR_MAX_CHARS:
        return f"{normalized[:WEB_DEBUG_ERROR_MAX_CHARS]}...[truncated]"
    return normalized


def describe_audio_file(audio_path: Path, duration_seconds: float | None = None) -> dict[str, Any]:
    """Return debug-safe file facts for a temporary audio file."""
    exists = audio_path.exists()
    return {
        "filename": audio_path.name,
        "suffix": audio_path.suffix.lower(),
        "exists": exists,
        "size_bytes": audio_path.stat().st_size if exists else 0,
        "duration_seconds": round(duration_seconds, 3) if duration_seconds is not None else None,
    }


def evaluate_speech_presence(
    audio_path: Path,
    duration_seconds: float | None,
    debug: dict[str, Any],
) -> str | None:
    """Return a skip reason when the audio is too short or VAD finds no speech."""
    if duration_seconds is not None and duration_seconds < WEB_MIN_RECOGNIZABLE_AUDIO_SECONDS:
        debug["vad"] = {
            "checked": False,
            "speech_detected": False,
            "reason": "duration_below_minimum",
            "duration_seconds": round(duration_seconds, 3),
            "minimum_seconds": WEB_MIN_RECOGNIZABLE_AUDIO_SECONDS,
        }
        return "duration_below_minimum"

    if audio_path.suffix.lower() != ".wav":
        debug["vad"] = {
            "checked": False,
            "speech_detected": None,
            "reason": "vad_requires_normalized_wav",
        }
        return None

    try:
        speech_detected = has_detectable_speech(
            audio_path,
            aggressiveness=WEB_VAD_AGGRESSIVENESS,
        )
    except AudioEnvironmentError as exc:
        LOGGER.info("Skipped Web VAD for %s: %s", audio_path.name, exc)
        debug["vad"] = {
            "checked": False,
            "speech_detected": None,
            "reason": "vad_unavailable",
            "error_type": exc.__class__.__name__,
        }
        return None

    debug["vad"] = {
        "checked": True,
        "speech_detected": speech_detected,
        "reason": "speech_detected" if speech_detected else "no_speech_detected",
        "aggressiveness": WEB_VAD_AGGRESSIVENESS,
    }
    if not speech_detected:
        return "vad_no_speech"
    return None


def process_web_transcription(request_data: WebTranscriptionRequest) -> WebTranscriptionResponse:
    """Run one Web transcription request and normalize the response payload."""
    turn_id = request_data.turn_id or new_turn_id("web")
    temp_path = build_temp_upload_path(request_data.filename)
    normalized_path = temp_path.with_suffix(".normalized.wav")
    debug: dict[str, Any] = {
        "turn_id": turn_id,
        "uploaded_filename": request_data.filename,
        "recording_blob_size_bytes": len(request_data.raw_bytes),
        "model": request_data.model_name,
        "language": request_data.language or "",
        "source": request_data.source,
        "ffprobe_duration_seconds": None,
        "uploaded_audio": None,
        "webm_normalized": False,
        "normalized_audio": None,
        "whisper_invoked": False,
        "whisper_skipped": False,
        "skip_reason": "",
    }

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
        audio_path = temp_path
        analysis_duration_seconds = None
        debug["uploaded_audio"] = describe_audio_file(temp_path)
        if temp_path.suffix.lower() == ".webm":
            audio_path = normalize_audio_for_transcription(
                temp_path,
                normalized_path,
                timeout_seconds=WEB_FFMPEG_TIMEOUT_SECONDS,
            )
            debug["webm_normalized"] = True
            analysis_duration_seconds = validate_uploaded_audio_content(audio_path)
            debug["normalized_audio"] = describe_audio_file(audio_path, analysis_duration_seconds)
        else:
            analysis_duration_seconds = validate_uploaded_audio_content(temp_path)
            debug["uploaded_audio"] = describe_audio_file(temp_path, analysis_duration_seconds)
        debug["ffprobe_duration_seconds"] = (
            round(analysis_duration_seconds, 3)
            if analysis_duration_seconds is not None
            else None
        )
        skip_reason = evaluate_speech_presence(
            audio_path,
            analysis_duration_seconds,
            debug,
        )
        if skip_reason:
            debug["whisper_skipped"] = True
            debug["skip_reason"] = skip_reason
            LOGGER.info(
                "Skipped Web transcription before Whisper: filename=%s reason=%s",
                request_data.filename,
                skip_reason,
            )
        else:
            debug["whisper_invoked"] = True
            emit_event(
                "stt_start",
                turn_id=turn_id,
                source=request_data.source,
                payload={
                    "model": request_data.model_name,
                    "language": request_data.language or "",
                    "audio": describe_audio_file(audio_path, analysis_duration_seconds),
                },
            )
            try:
                pipeline = get_cached_transcription_pipeline(
                    model_name=request_data.model_name
                )
                transcript = pipeline.transcribe_chunk(
                    AudioChunk(path=audio_path, source=request_data.source),
                    language=request_data.language,
                )
            except Exception as exc:
                emit_event(
                    "stt_done",
                    turn_id=turn_id,
                    source=request_data.source,
                    payload={
                        "model": request_data.model_name,
                        "status": "error",
                        "error_type": exc.__class__.__name__,
                    },
                )
                raise
            emit_event(
                "stt_done",
                turn_id=turn_id,
                source=request_data.source,
                payload={
                    "model": request_data.model_name,
                    "status": "ok",
                    **text_payload_facts(transcript),
                },
            )
            emit_event(
                "stt_final",
                turn_id=turn_id,
                source=request_data.source,
                payload=text_payload_facts(transcript),
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
                    emit_event(
                        "handoff_saved",
                        turn_id=turn_id,
                        source=request_data.source,
                        payload={
                            "json_filename": saved_paths.json_path.name,
                            "text_filename": saved_paths.text_path.name,
                            "transcript": text_payload_facts(transcript),
                            "command": text_payload_facts(command),
                        },
                    )
    except AudioInputError as exc:
        LOGGER.info("Rejected web transcription input: %s", exc)
        debug["error_type"] = exc.__class__.__name__
        debug["error_detail"] = summarize_audio_tool_error(str(exc))
        error = GENERIC_INPUT_ERROR
        status_code = 400
    except AudioEnvironmentError as exc:
        LOGGER.exception("Web transcription environment failure: %s", exc)
        debug["error_type"] = exc.__class__.__name__
        debug["error_detail"] = summarize_audio_tool_error(str(exc))
        error = GENERIC_ENVIRONMENT_ERROR
        status_code = 500
    except AudioTranscriptionError as exc:
        LOGGER.exception("Web transcription failure: %s", exc)
        debug["error_type"] = exc.__class__.__name__
        debug["error_detail"] = summarize_audio_tool_error(str(exc))
        error = GENERIC_TRANSCRIPTION_ERROR
        status_code = 500
    finally:
        LOGGER.info("Web transcription debug: %s", debug)
        if temp_path.exists():
            temp_path.unlink()
        if normalized_path.exists():
            normalized_path.unlink()

    return WebTranscriptionResponse(
        message=(
            ""
            if error
            else (
                NO_RECOGNIZABLE_SPEECH_MESSAGE
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
        turn_id=turn_id,
        debug=debug,
    )
