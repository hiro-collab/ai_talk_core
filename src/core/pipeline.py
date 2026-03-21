"""Shared transcription pipeline primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.io.audio import load_transcription_model, transcribe_file


@dataclass(frozen=True)
class AudioChunk:
    """A captured audio chunk ready for transcription."""

    path: Path
    source: str


class TranscriptionPipeline:
    """Keep a loaded Whisper model and transcribe audio chunks."""

    def __init__(self, model_name: str = "small") -> None:
        self.model_name = model_name
        self.model: Any = load_transcription_model(model_name=model_name)

    def transcribe_chunk(self, chunk: AudioChunk, language: str | None = None) -> str:
        """Transcribe a captured audio chunk."""
        return transcribe_file(audio_path=chunk.path, model=self.model, language=language)
