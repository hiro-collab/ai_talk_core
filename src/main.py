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
from src.io.microphone import get_temp_recording_path, record_microphone_audio


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
        "--duration",
        type=int,
        default=5,
        help="Recording duration in seconds for --mic. Default: 5",
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
    return parser


def main() -> int:
    """Run the transcription CLI."""
    args = build_parser().parse_args()

    try:
        validate_model_name(args.model)
        ensure_ffmpeg_available()
        if args.mic:
            if args.audio_file is not None:
                raise AudioInputError("audio_file cannot be used together with --mic")
            audio_path = record_microphone_audio(
                output_path=get_temp_recording_path(),
                duration=args.duration,
                device=args.mic_device,
            )
        else:
            if not args.audio_file:
                raise AudioInputError("audio_file is required unless --mic is used")
            audio_path = Path(args.audio_file).expanduser().resolve()
            validate_audio_file(audio_path)
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
