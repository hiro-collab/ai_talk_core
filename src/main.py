"""CLI entrypoint for local audio transcription."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.io.audio import (
    AudioEnvironmentError,
    AudioInputError,
    AudioTranscriptionError,
    ensure_ffmpeg_available,
    load_transcription_model,
    transcribe_file,
    validate_audio_file,
    validate_model_name,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Transcribe a local audio file with Whisper."
    )
    parser.add_argument("audio_file", help="Path to the local audio file.")
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
    return parser


def main() -> int:
    """Run the transcription CLI."""
    args = build_parser().parse_args()
    audio_path = Path(args.audio_file).expanduser().resolve()

    try:
        validate_audio_file(audio_path)
        validate_model_name(args.model)
        ensure_ffmpeg_available()
        model = load_transcription_model(model_name=args.model)
        text = transcribe_file(audio_path=audio_path, model=model, language=args.language)
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
