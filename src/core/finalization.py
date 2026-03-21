"""Heuristics for promoting mic-loop transcripts from partial to final."""

from __future__ import annotations

from src.core.pipeline import TranscriptionResult


def normalize_transcript_text(text: str) -> str:
    """Normalize transcript text for lightweight repeat detection."""
    return " ".join(text.strip().split())


def required_repeat_count_for_final(text: str) -> int:
    """Return the repeat threshold for a given normalized transcript."""
    if len(text) >= 12:
        return 2
    return 3


def has_stable_duration_for_final(
    text: str,
    repeat_count: int,
    chunk_duration: int,
    final_stable_seconds: int,
) -> bool:
    """Return whether a transcript stayed stable long enough to finalize."""
    if len(text) < 6:
        return False
    if repeat_count < 2:
        return False
    stable_seconds = repeat_count * chunk_duration
    return stable_seconds >= final_stable_seconds


def should_mark_result_final(
    result: TranscriptionResult,
    repeat_count: int,
    is_last_iteration: bool,
    chunk_duration: int,
    final_stable_seconds: int,
) -> bool:
    """Decide whether a mic-loop result can be treated as final."""
    if is_last_iteration:
        return True
    current_text = normalize_transcript_text(result.text)
    if not current_text:
        return False
    if len(current_text) < 3:
        return False
    if repeat_count >= required_repeat_count_for_final(current_text):
        return True
    return has_stable_duration_for_final(
        current_text,
        repeat_count,
        chunk_duration,
        final_stable_seconds,
    )


def maybe_finalize_on_silence(
    result: TranscriptionResult,
    last_spoken_result: TranscriptionResult | None,
    repeat_count: int,
    finalized_text: str | None,
) -> TranscriptionResult:
    """Convert a silence chunk into a final result when speech just ended."""
    if not result.is_silence:
        return result
    if last_spoken_result is None:
        return result
    spoken_text = normalize_transcript_text(last_spoken_result.text)
    if not spoken_text or len(spoken_text) < 3:
        return result
    if spoken_text == finalized_text:
        return result
    if repeat_count < 2:
        return result
    return TranscriptionResult(
        source=last_spoken_result.source,
        text=last_spoken_result.text,
        is_final=True,
        chunk_count=result.chunk_count,
        is_silence=False,
    )


def maybe_finalize_on_interrupt(
    last_spoken_result: TranscriptionResult | None,
    finalized_text: str | None,
    chunk_count: int,
) -> TranscriptionResult | None:
    """Finalize the latest spoken result when mic-loop is interrupted."""
    if last_spoken_result is None:
        return None
    spoken_text = normalize_transcript_text(last_spoken_result.text)
    if not spoken_text or len(spoken_text) < 3:
        return None
    if spoken_text == finalized_text:
        return None
    return TranscriptionResult(
        source=last_spoken_result.source,
        text=last_spoken_result.text,
        is_final=True,
        chunk_count=chunk_count,
        is_silence=False,
    )
