"""Microphone recording helpers."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

from src.io.audio import AudioEnvironmentError, AudioInputError


def get_temp_recording_path() -> Path:
    """Return the temporary wav path used for microphone recordings."""
    project_root = Path(__file__).resolve().parents[2]
    temp_dir = project_root / ".cache" / "recordings"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir / "mic_input.wav"


def ensure_arecord_available() -> None:
    """Ensure arecord is available in the local environment."""
    if shutil.which("arecord") is None:
        raise AudioEnvironmentError("arecord is not installed or not found in PATH")


def get_default_microphone_device() -> str:
    """Return a preferred arecord device string for this machine."""
    ensure_arecord_available()

    try:
        result = subprocess.run(
            ["arecord", "-l"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise AudioEnvironmentError(f"failed to list microphone devices: {message}") from exc

    for line in result.stdout.splitlines():
        if "HD Pro Webcam C920" not in line:
            continue
        match = re.search(r"card\s+(\d+).+device\s+(\d+)", line)
        if match:
            card_index, device_index = match.groups()
            return f"plughw:{card_index},{device_index}"

    return "default"


def validate_duration(duration: int) -> None:
    """Validate microphone recording duration."""
    if duration <= 0:
        raise AudioInputError("microphone duration must be greater than 0 seconds")


def record_microphone_audio(
    output_path: Path,
    duration: int,
    device: str = "default",
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    """Record a fixed-duration wav file from the microphone."""
    validate_duration(duration)
    ensure_arecord_available()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_device = get_default_microphone_device() if device == "default" else device

    command = [
        "arecord",
        "-D",
        resolved_device,
        "-f",
        "S16_LE",
        "-c",
        str(channels),
        "-r",
        str(sample_rate),
        "-d",
        str(duration),
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise AudioEnvironmentError(f"microphone recording failed: {message}") from exc

    return output_path
