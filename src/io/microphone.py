"""Microphone recording helpers."""

from __future__ import annotations

import importlib
from pathlib import Path
import wave
import re
import shutil
import subprocess

from src.core.pipeline import AudioChunk
from src.io.audio import AudioEnvironmentError, AudioInputError


class WebRtcVadAdapter:
    """Minimal wrapper around the native _webrtcvad module."""

    def __init__(self, aggressiveness: int = 2) -> None:
        try:
            module = importlib.import_module("_webrtcvad")
        except ModuleNotFoundError as exc:
            raise AudioEnvironmentError("webrtcvad native module is not available") from exc
        self._module = module
        self._vad = module.create()
        module.init(self._vad)
        module.set_mode(self._vad, aggressiveness)

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        """Return whether a single PCM frame contains speech."""
        return self._module.process(self._vad, sample_rate, frame, int(len(frame) / 2))


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
    """Return a preferred arecord device string from detected capture devices."""
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


def iter_vad_frames(audio_bytes: bytes, sample_rate: int, frame_ms: int = 30) -> list[bytes]:
    """Split PCM bytes into fixed-size frames for VAD."""
    bytes_per_sample = 2
    frame_size = int(sample_rate * frame_ms / 1000) * bytes_per_sample
    if frame_size <= 0:
        return []
    return [
        audio_bytes[index:index + frame_size]
        for index in range(0, len(audio_bytes), frame_size)
        if len(audio_bytes[index:index + frame_size]) == frame_size
    ]


def has_detectable_speech(
    audio_path: Path,
    aggressiveness: int = 2,
) -> bool:
    """Return whether WebRTC VAD detects speech in a wav clip."""
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            channels = wav_file.getnchannels()
            audio_bytes = wav_file.readframes(wav_file.getnframes())
    except (wave.Error, OSError) as exc:
        raise AudioEnvironmentError(f"speech detection failed: {exc}") from exc

    if sample_width != 2:
        raise AudioEnvironmentError(
            f"speech detection expects 16-bit PCM wav, got sample width {sample_width}"
        )
    if channels != 1:
        raise AudioEnvironmentError(
            f"speech detection expects mono wav, got {channels} channels"
        )
    if sample_rate not in {8000, 16000, 32000, 48000}:
        raise AudioEnvironmentError(
            f"speech detection does not support sample rate {sample_rate}"
        )

    vad = WebRtcVadAdapter(aggressiveness=aggressiveness)
    for frame in iter_vad_frames(audio_bytes, sample_rate=sample_rate):
        if vad.is_speech(frame, sample_rate):
            return True
    return False


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
