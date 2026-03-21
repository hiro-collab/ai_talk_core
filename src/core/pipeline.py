"""Shared transcription pipeline primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.io.audio import AudioInputError, load_transcription_model, transcribe_file


@dataclass(frozen=True)
class AudioChunk:
    """A captured audio chunk ready for transcription."""

    path: Path
    source: str


@dataclass(frozen=True)
class TranscriptionResult:
    """A normalized transcription result for realtime-style flows."""

    source: str
    text: str
    is_final: bool
    chunk_count: int
    is_silence: bool = False


@dataclass
class AudioBuffer:
    """A simple ordered buffer of captured audio chunks."""

    source: str
    chunks: list[AudioChunk] = field(default_factory=list)

    def append(self, chunk: AudioChunk) -> None:
        """Append a chunk to the buffer."""
        if chunk.source != self.source:
            raise AudioInputError(
                f"audio chunk source mismatch: expected {self.source}, got {chunk.source}"
            )
        self.chunks.append(chunk)

    def latest_chunk(self) -> AudioChunk:
        """Return the latest chunk in the buffer."""
        if not self.chunks:
            raise AudioInputError("audio buffer is empty")
        return self.chunks[-1]


class TranscriptionPipeline:
    """Keep a loaded Whisper model and transcribe audio chunks."""

    def __init__(self, model_name: str = "small") -> None:
        self.model_name = model_name
        self.model: Any = load_transcription_model(model_name=model_name)

    def transcribe_chunk(self, chunk: AudioChunk, language: str | None = None) -> str:
        """Transcribe a captured audio chunk."""
        return transcribe_file(audio_path=chunk.path, model=self.model, language=language)

    def transcribe_buffer(self, buffer: AudioBuffer, language: str | None = None) -> str:
        """Transcribe the latest chunk from a buffer."""
        return self.transcribe_chunk(buffer.latest_chunk(), language=language)

    def transcribe_buffer_result(
        self,
        buffer: AudioBuffer,
        language: str | None = None,
        is_final: bool = False,
    ) -> TranscriptionResult:
        """Transcribe the latest chunk and return a realtime-style result."""
        text = self.transcribe_buffer(buffer, language=language)
        return TranscriptionResult(
            source=buffer.source,
            text=text,
            is_final=is_final,
            chunk_count=len(buffer.chunks),
        )
