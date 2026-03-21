"""CLI entrypoint for local audio transcription."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from src.core.pipeline import AudioBuffer, AudioChunk, TranscriptionPipeline, TranscriptionResult
from src.io.audio import (
    AudioEnvironmentError,
    AudioInputError,
    AudioTranscriptionError,
    ensure_ffmpeg_available,
    validate_audio_file,
    validate_model_name,
)
from src.io.microphone import capture_microphone_chunk, get_temp_recording_path, record_microphone_audio


def format_transcription_result(result: object) -> str:
    """Format a realtime transcription result for terminal output."""
    result_type = "final" if getattr(result, "is_final", False) else "partial"
    chunk_count = getattr(result, "chunk_count", "?")
    text = getattr(result, "text", "")
    return f"[{result_type} {chunk_count}] {text}"


def normalize_transcript_text(text: str) -> str:
    """Normalize transcript text for lightweight repeat detection."""
    return " ".join(text.strip().split())


def should_mark_result_final(
    result: TranscriptionResult,
    previous_text: str | None,
    is_last_iteration: bool,
) -> bool:
    """Decide whether a mic-loop result can be treated as final."""
    if is_last_iteration:
        return True
    current_text = normalize_transcript_text(result.text)
    if not current_text:
        return False
    return current_text == previous_text


def run_mic_loop(
    duration: int,
    mic_device: str,
    model_name: str,
    language: str | None,
    iterations: int | None,
    trim_silence_enabled: bool,
) -> int:
    """Record and transcribe microphone chunks until interrupted."""
    pipeline = TranscriptionPipeline(model_name=model_name)
    buffer = AudioBuffer(source="microphone")
    completed_iterations = 0
    previous_text: str | None = None

    try:
        while iterations is None or completed_iterations < iterations:
            chunk = capture_microphone_chunk(
                output_path=get_temp_recording_path(),
                duration=duration,
                device=mic_device,
                trim_silence_enabled=trim_silence_enabled,
            )
            buffer.append(chunk)
            next_iteration = completed_iterations + 1
            is_last_iteration = iterations is not None and next_iteration == iterations
            result = pipeline.transcribe_buffer_result(
                buffer,
                language=language,
                is_final=False,
            )
            if should_mark_result_final(result, previous_text, is_last_iteration):
                result = replace(result, is_final=True)
            print(format_transcription_result(result))
            normalized_text = normalize_transcript_text(result.text)
            if normalized_text:
                previous_text = normalized_text
            completed_iterations += 1
    except KeyboardInterrupt:
        print("Stopped microphone loop.")
        return 0

    return 0


def validate_iterations(iterations: int | None) -> None:
    """Validate optional mic-loop iteration count."""
    if iterations is not None and iterations <= 0:
        raise AudioInputError("--iterations must be greater than 0")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Transcribe a local audio file with Whisper."
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        help="Path to the local audio file.",
    )
    parser.add_argument(
        "--mic",
        action="store_true",
        help="Record from the microphone for a fixed duration.",
    )
    parser.add_argument(
        "--mic-loop",
        action="store_true",
        help="Repeat fixed-duration microphone recording until interrupted.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Recording duration in seconds for --mic or --mic-loop. Default: 5",
    )
    parser.add_argument(
        "--mic-device",
        default="default",
        help="Microphone device for arecord. Default: default",
    )
    parser.add_argument(
        "--model",
        default="small",
        help="Whisper model name to use. Default: small",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional language code such as ja or en.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Optional iteration count for --mic-loop. Default: run until Ctrl+C",
    )
    parser.add_argument(
        "--no-trim-silence",
        action="store_true",
        help="Disable ffmpeg-based silence trimming for microphone recordings.",
    )
    return parser


def main() -> int:
    """Run the transcription CLI."""
    args = build_parser().parse_args()

    try:
        validate_model_name(args.model)
        ensure_ffmpeg_available()
        if args.mic and args.mic_loop:
            raise AudioInputError("--mic and --mic-loop cannot be used together")
        validate_iterations(args.iterations)
        if args.iterations is not None and not args.mic_loop:
            raise AudioInputError("--iterations can only be used with --mic-loop")
        if args.mic_loop:
            if args.audio_file is not None:
                raise AudioInputError("audio_file cannot be used together with --mic-loop")
            return run_mic_loop(
                duration=args.duration,
                mic_device=args.mic_device,
                model_name=args.model,
                language=args.language,
                iterations=args.iterations,
                trim_silence_enabled=not args.no_trim_silence,
            )
        if args.mic:
            if args.audio_file is not None:
                raise AudioInputError("audio_file cannot be used together with --mic")
            audio_path = record_microphone_audio(
                output_path=get_temp_recording_path(),
                duration=args.duration,
                device=args.mic_device,
                trim_silence_enabled=not args.no_trim_silence,
            )
        else:
            if not args.audio_file:
                raise AudioInputError(
                    "audio_file is required unless --mic or --mic-loop is used"
                )
            audio_path = Path(args.audio_file).expanduser().resolve()
            validate_audio_file(audio_path)
        pipeline = TranscriptionPipeline(model_name=args.model)
        text = pipeline.transcribe_chunk(
            AudioChunk(
                path=audio_path,
                source="microphone" if args.mic else "file",
            ),
            language=args.language,
        )
    except AudioInputError as exc:
        print(f"Input error: {exc}")
        return 1
    except AudioEnvironmentError as exc:
        print(f"Environment error: {exc}")
        return 1
    except AudioTranscriptionError as exc:
        print(f"Transcription error: {exc}")
        return 1

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
