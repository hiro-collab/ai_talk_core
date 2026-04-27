"""Audio input helpers."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any

import torch
import whisper


SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm"}


class AudioInputError(ValueError):
    """Raised when the user provides an invalid audio input."""


class AudioEnvironmentError(RuntimeError):
    """Raised when the local runtime environment is not ready."""


class AudioTranscriptionError(RuntimeError):
    """Raised when Whisper fails while transcribing."""


def should_retry_model_load_on_cpu(exc: Exception) -> bool:
    """Return True when a Whisper load failure should retry on CPU."""
    message = str(exc).lower()
    return "cuda-capable device" in message or "cuda error" in message or "devices unavailable" in message


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


def get_runtime_status() -> dict[str, str | bool | None]:
    """Return a compact view of the local transcription runtime status."""
    cuda_available = torch.cuda.is_available()
    device = "cuda" if cuda_available else "cpu"
    torch_cuda_version = torch.version.cuda
    torch_cuda_build = torch_cuda_version is not None
    nvidia_driver_version: str | None = None
    nvidia_gpu_name: str | None = None
    nvidia_smi_available = shutil.which("nvidia-smi") is not None
    if nvidia_smi_available:
        try:
            command = [
                "nvidia-smi",
                "--query-gpu=driver_version,gpu_name",
                "--format=csv,noheader",
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
            first_line = completed.stdout.strip().splitlines()[0]
            driver_value, gpu_value = [part.strip() for part in first_line.split(",", 1)]
            nvidia_driver_version = driver_value
            nvidia_gpu_name = gpu_value
        except (subprocess.CalledProcessError, IndexError, ValueError):
            nvidia_driver_version = None
            nvidia_gpu_name = None
    note: str | None = None
    suggested_action: str | None = None
    if not cuda_available and torch_cuda_build:
        note = (
            "Torch CUDA build is present but unavailable; transcription will use CPU "
            "fallback."
        )
        if nvidia_smi_available and nvidia_driver_version is not None:
            note += (
                " nvidia-smi is available, so a Torch/driver CUDA mismatch or local "
                "CUDA initialization problem is likely."
            )
            suggested_action = (
                "Inspect the uv-managed Torch version and pin a driver-compatible "
                "build inside .venv before changing system drivers."
            )
        else:
            suggested_action = (
                "Check local CUDA initialization and Torch runtime configuration "
                "before relying on GPU transcription."
            )
    elif not cuda_available and nvidia_smi_available:
        note = (
            "NVIDIA GPU is visible through nvidia-smi, but the installed Torch build "
            "is CPU-only; transcription will use CPU fallback."
        )
        suggested_action = (
            "Install a PyTorch CUDA wheel inside this project's .venv, then rerun "
            "the doctor command with the project venv Python, or use "
            "`uv run --no-sync python -m src.main --doctor`."
        )
    return {
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "ffprobe_available": shutil.which("ffprobe") is not None,
        "nvidia_smi_available": nvidia_smi_available,
        "nvidia_driver_version": nvidia_driver_version,
        "nvidia_gpu_name": nvidia_gpu_name,
        "torch_version": torch.__version__,
        "torch_cuda_version": torch_cuda_version,
        "torch_cuda_build": torch_cuda_build,
        "torch_cuda_available": cuda_available,
        "transcription_device": device,
        "whisper_version": getattr(whisper, "__version__", None),
        "runtime_note": note,
        "suggested_action": suggested_action,
    }




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


def normalize_audio_for_transcription(
    input_path: Path,
    output_path: Path,
    timeout_seconds: float | None = 60,
) -> Path:
    """Normalize audio into a transcription-friendly wav with ffmpeg."""
    ensure_ffmpeg_available()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioEnvironmentError("audio normalization timed out") from exc
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise AudioEnvironmentError(f"audio normalization failed: {message}") from exc
    return output_path


def load_transcription_model(model_name: str = "small") -> Any:
    """Load a Whisper model from the local model directory."""
    validate_model_name(model_name)
    download_root = str(get_model_dir())

    try:
        return whisper.load_model(model_name, download_root=download_root)
    except Exception as exc:
        if should_retry_model_load_on_cpu(exc):
            try:
                return whisper.load_model(
                    model_name,
                    download_root=download_root,
                    device="cpu",
                )
            except Exception as cpu_exc:
                raise AudioEnvironmentError(
                    f"failed to load Whisper model '{model_name}': {cpu_exc}"
                ) from cpu_exc
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
