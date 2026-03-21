"""Microphone recording helpers."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

from src.core.pipeline import AudioChunk
from src.io.audio import AudioEnvironmentError, AudioInputError


def get_temp_recording_path() -> Path:
    """Return the temporary wav path used for microphone recordings."""
    project_root = Path(__file__).resolve().parents[2]
    temp_dir = project_root / ".cache" / "recordings"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir / "mic_input.wav"


def get_trimmed_recording_path() -> Path:
    """Return the temporary wav path used for trimmed microphone recordings."""
    project_root = Path(__file__).resolve().parents[2]
    temp_dir = project_root / ".cache" / "recordings"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir / "mic_input_trimmed.wav"


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


def trim_silence(
    input_path: Path,
    output_path: Path,
    silence_duration: float = 0.3,
    silence_threshold_db: float = -40.0,
) -> Path:
    """Trim leading and trailing silence from a wav file with ffmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filter_value = (
        "silenceremove="
        f"start_periods=1:start_duration={silence_duration}:start_threshold={silence_threshold_db}dB:"
        f"stop_periods=1:stop_duration={silence_duration}:stop_threshold={silence_threshold_db}dB"
    )
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-af",
        filter_value,
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise AudioEnvironmentError(f"silence trimming failed: {message}") from exc

    if not output_path.exists() or output_path.stat().st_size <= 1024:
        return input_path

    return output_path


def get_audio_duration_seconds(audio_path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise AudioEnvironmentError(f"audio duration probe failed: {message}") from exc

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise AudioEnvironmentError(
            f"audio duration probe returned invalid output: {result.stdout.strip()}"
        ) from exc


def has_detectable_speech(
    audio_path: Path,
    silence_threshold_db: float = -35.0,
    silence_duration: float = 0.2,
) -> bool:
    """Return whether ffmpeg detects non-silent audio in the clip."""
    duration = get_audio_duration_seconds(audio_path)
    if duration <= 0.0:
        return False

    command = [
        "ffmpeg",
        "-i",
        str(audio_path),
        "-af",
        f"silencedetect=noise={silence_threshold_db}dB:d={silence_duration}",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise AudioEnvironmentError(f"speech detection failed: {message}") from exc

    stderr = result.stderr
    match_start = re.search(r"silence_start:\s*0(?:\.0+)?", stderr)
    match_end = re.search(r"silence_end:\s*([0-9.]+)", stderr)
    if match_start and match_end:
        silence_end = float(match_end.group(1))
        if silence_end >= max(duration - 0.1, 0.0):
            return False

    return True


def record_microphone_audio(
    output_path: Path,
    duration: int,
    device: str = "default",
    sample_rate: int = 16000,
    channels: int = 1,
    trim_silence_enabled: bool = True,
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

    if trim_silence_enabled:
        return trim_silence(input_path=output_path, output_path=get_trimmed_recording_path())

    return output_path


def capture_microphone_chunk(
    output_path: Path,
    duration: int,
    device: str = "default",
    sample_rate: int = 16000,
    channels: int = 1,
    trim_silence_enabled: bool = True,
) -> AudioChunk:
    """Capture one microphone chunk and wrap it for the pipeline."""
    audio_path = record_microphone_audio(
        output_path=output_path,
        duration=duration,
        device=device,
        sample_rate=sample_rate,
        channels=channels,
        trim_silence_enabled=trim_silence_enabled,
    )
    return AudioChunk(path=audio_path, source="microphone")
