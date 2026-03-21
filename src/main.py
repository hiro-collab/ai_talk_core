"""CLI entrypoint for local audio transcription."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from src.core.agent_instruction import build_agent_instruction
from src.core.finalization import (
    has_stable_duration_for_final,
    maybe_finalize_on_interrupt,
    maybe_finalize_on_silence,
    normalize_transcript_text,
    required_repeat_count_for_final,
    should_mark_result_final,
)
from src.core.handoff_bridge import save_handoff_bundle
from src.core.pipeline import AudioBuffer, AudioChunk, TranscriptionPipeline, TranscriptionResult
from src.io.audio import (
    AudioEnvironmentError,
    AudioInputError,
    AudioTranscriptionError,
    ensure_ffmpeg_available,
    get_runtime_status,
    validate_audio_file,
    validate_model_name,
)
from src.io.microphone import (
    capture_microphone_chunk,
    get_temp_recording_path,
    has_detectable_speech,
    record_microphone_audio,
    validate_vad_aggressiveness,
)


MIC_LOOP_PROFILES: dict[str, tuple[int, int, str]] = {
    "responsive": (1, 5, "反応を優先し、早めに partial/final を出す"),
    "balanced": (2, 8, "既定のバランス設定"),
    "strict": (3, 10, "無音と誤認識を減らす代わりに確定を遅くする"),
}


def format_transcription_result(result: object) -> str:
    """Format a realtime transcription result for terminal output."""
    if getattr(result, "is_silence", False):
        chunk_count = getattr(result, "chunk_count", "?")
        result_type = "final" if getattr(result, "is_final", False) else "silence"
        return f"[{result_type} {chunk_count}] silence detected"
    result_type = "final" if getattr(result, "is_final", False) else "partial"
    chunk_count = getattr(result, "chunk_count", "?")
    text = getattr(result, "text", "")
    return f"[{result_type} {chunk_count}] {text}"


def print_agent_instruction_if_requested(text: str, emit_command: bool) -> None:
    """Print an agent-ready instruction draft when requested."""
    if not emit_command:
        return
    draft = build_agent_instruction(text)
    if draft is None:
        print("[command] no instruction draft available")
        return
    print(f"[command] {draft.instruction}")


def print_agent_instruction_only(text: str) -> None:
    """Print only the agent-ready instruction draft."""
    draft = build_agent_instruction(text)
    if draft is None:
        print("no instruction draft available")
        return
    print(draft.instruction)


def save_handoff_if_requested(text: str, output_path: str | None) -> None:
    """Save a handoff bundle to disk when requested."""
    if not output_path:
        return
    json_path = Path(output_path).expanduser().resolve()
    text_path = json_path.with_suffix(".txt")
    saved_paths = save_handoff_bundle(text, json_path=json_path, text_path=text_path)
    if saved_paths is None:
        print(f"[command-file] no instruction draft available for {output_path}")
        return
    print(f"[command-file] {saved_paths.json_path}")
    print(f"[command-text] {saved_paths.text_path}")


def print_runtime_note(message: str) -> None:
    """Print operational notes to stderr without polluting stdout payloads."""
    print(message, file=sys.stderr)


def format_mic_loop_tuning(
    profile: str,
    vad_aggressiveness: int,
    final_stable_seconds: int,
) -> str:
    """Format the resolved mic-loop tuning values for terminal output."""
    return (
        "[mic-tuning] "
        f"profile={profile} "
        f"vad_aggressiveness={vad_aggressiveness} "
        f"final_stable_seconds={final_stable_seconds}"
    )


def run_mic_loop(
    duration: int,
    mic_device: str,
    model_name: str,
    language: str | None,
    iterations: int | None,
    trim_silence_enabled: bool,
    emit_command: bool,
    command_only: bool,
    command_output: str | None,
    mic_profile: str,
    vad_aggressiveness: int,
    final_stable_seconds: int,
) -> int:
    """Record and transcribe microphone chunks until interrupted."""
    pipeline = TranscriptionPipeline(model_name=model_name)
    buffer = AudioBuffer(source="microphone")
    completed_iterations = 0
    previous_text: str | None = None
    repeat_count = 0
    last_spoken_result: TranscriptionResult | None = None
    finalized_text: str | None = None

    print_runtime_note(
        format_mic_loop_tuning(
            profile=mic_profile,
            vad_aggressiveness=vad_aggressiveness,
            final_stable_seconds=final_stable_seconds,
        )
    )

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
            if has_detectable_speech(chunk.path, aggressiveness=vad_aggressiveness):
                result = pipeline.transcribe_buffer_result(
                    buffer,
                    language=language,
                    is_final=False,
                )
            else:
                result = TranscriptionResult(
                    source=buffer.source,
                    text="",
                    is_final=False,
                    chunk_count=len(buffer.chunks),
                    is_silence=True,
                )
            result = maybe_finalize_on_silence(
                result=result,
                last_spoken_result=last_spoken_result,
                repeat_count=repeat_count,
                finalized_text=finalized_text,
            )
            normalized_text = normalize_transcript_text(result.text)
            if normalized_text and not result.is_silence:
                if normalized_text == previous_text:
                    repeat_count += 1
                else:
                    repeat_count = 1
                previous_text = normalized_text
                last_spoken_result = result
            else:
                repeat_count = 0
            if should_mark_result_final(
                result,
                repeat_count,
                is_last_iteration,
                duration,
                final_stable_seconds,
            ):
                result = replace(result, is_final=True)
            if result.is_final and not result.is_silence and normalized_text:
                finalized_text = normalized_text
            if command_only:
                print_agent_instruction_only(result.text)
            else:
                print(format_transcription_result(result))
                print_agent_instruction_if_requested(result.text, emit_command=emit_command)
            save_handoff_if_requested(result.text, command_output)
            completed_iterations += 1
    except KeyboardInterrupt:
        final_result = maybe_finalize_on_interrupt(
            last_spoken_result=last_spoken_result,
            finalized_text=finalized_text,
            chunk_count=len(buffer.chunks),
        )
        if final_result is not None:
            if command_only:
                print_agent_instruction_only(final_result.text)
            else:
                print(format_transcription_result(final_result))
                print_agent_instruction_if_requested(
                    final_result.text,
                    emit_command=emit_command,
                )
            save_handoff_if_requested(final_result.text, command_output)
        print_runtime_note("Stopped microphone loop.")
        return 0

    return 0


def validate_iterations(iterations: int | None) -> None:
    """Validate optional mic-loop iteration count."""
    if iterations is not None and iterations <= 0:
        raise AudioInputError("--iterations must be greater than 0")


def validate_mic_loop_options(vad_aggressiveness: int) -> None:
    """Validate mic-loop specific options."""
    validate_vad_aggressiveness(vad_aggressiveness)


def validate_mic_profile(profile: str) -> None:
    """Validate the selected mic-loop tuning profile."""
    if profile not in MIC_LOOP_PROFILES:
        raise AudioInputError(
            "--mic-profile must be one of: responsive, balanced, strict"
        )


def validate_final_stable_seconds(final_stable_seconds: int) -> None:
    """Validate the stable-duration threshold for finalization."""
    if final_stable_seconds <= 0:
        raise AudioInputError("--final-stable-seconds must be greater than 0")


def resolve_mic_loop_tuning(
    profile: str,
    vad_aggressiveness: int | None,
    final_stable_seconds: int | None,
) -> tuple[int, int]:
    """Resolve mic-loop tuning from a named profile and optional overrides."""
    preset_vad, preset_final_seconds, _description = MIC_LOOP_PROFILES[profile]
    resolved_vad = preset_vad if vad_aggressiveness is None else vad_aggressiveness
    resolved_final_seconds = (
        preset_final_seconds
        if final_stable_seconds is None
        else final_stable_seconds
    )
    return resolved_vad, resolved_final_seconds


def format_mic_profile_list() -> str:
    """Render the available mic-loop tuning profiles."""
    lines = ["Available mic-loop profiles:"]
    for profile, (vad, stable_seconds, description) in MIC_LOOP_PROFILES.items():
        lines.append(
            f"- {profile}: vad_aggressiveness={vad}, "
            f"final_stable_seconds={stable_seconds} ({description})"
        )
    return "\n".join(lines)


def build_mic_profile_list_data() -> list[dict[str, str | int]]:
    """Return the available mic-loop profiles as structured data."""
    return [
        {
            "profile": profile,
            "vad_aggressiveness": vad,
            "final_stable_seconds": stable_seconds,
            "description": description,
        }
        for profile, (vad, stable_seconds, description) in MIC_LOOP_PROFILES.items()
    ]


def build_mic_tuning_data(
    profile: str,
    vad_aggressiveness: int,
    final_stable_seconds: int,
) -> dict[str, str | int]:
    """Return the resolved mic-loop tuning as structured data."""
    return {
        "profile": profile,
        "vad_aggressiveness": vad_aggressiveness,
        "final_stable_seconds": final_stable_seconds,
    }


def format_runtime_status(status: dict[str, str | bool | None]) -> str:
    """Format the local runtime status for terminal output."""
    lines = ["Runtime status:"]
    for key, value in status.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


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
    parser.add_argument(
        "--mic-profile",
        default="balanced",
        help="Mic-loop tuning profile: responsive, balanced, or strict. Default: balanced",
    )
    parser.add_argument(
        "--list-mic-profiles",
        action="store_true",
        help="Print available mic-loop tuning profiles and exit.",
    )
    parser.add_argument(
        "--show-mic-tuning",
        action="store_true",
        help="Print the resolved mic-loop tuning values and exit.",
    )
    parser.add_argument(
        "--mic-tuning-format",
        choices=("text", "json"),
        default="text",
        help="Output format for --list-mic-profiles or --show-mic-tuning. Default: text",
    )
    parser.add_argument(
        "--show-runtime-status",
        action="store_true",
        help="Print the local Whisper / Torch / ffmpeg runtime status and exit.",
    )
    parser.add_argument(
        "--runtime-status-format",
        choices=("text", "json"),
        default="text",
        help="Output format for --show-runtime-status. Default: text",
    )
    parser.add_argument(
        "--vad-aggressiveness",
        type=int,
        default=None,
        help="WebRTC VAD aggressiveness for --mic-loop (0-3). Overrides --mic-profile.",
    )
    parser.add_argument(
        "--final-stable-seconds",
        type=int,
        default=None,
        help="Stable duration threshold in seconds for mic-loop finalization. Overrides --mic-profile.",
    )
    parser.add_argument(
        "--emit-command",
        "--emit-instruction",
        dest="emit_command",
        action="store_true",
        help="Print an agent-ready instruction draft from the transcript.",
    )
    parser.add_argument(
        "--command-only",
        "--instruction-only",
        dest="command_only",
        action="store_true",
        help="Print only the agent-ready instruction draft.",
    )
    parser.add_argument(
        "--command-output",
        "--handoff-output",
        dest="command_output",
        default=None,
        help="Optional path to save a handoff payload JSON file.",
    )
    return parser


def main() -> int:
    """Run the transcription CLI."""
    args = build_parser().parse_args()

    try:
        if args.list_mic_profiles:
            if args.mic_tuning_format == "json":
                print(json.dumps(build_mic_profile_list_data(), ensure_ascii=False, indent=2))
            else:
                print(format_mic_profile_list())
            return 0
        if args.show_mic_tuning:
            validate_mic_profile(args.mic_profile)
            resolved_vad_aggressiveness, resolved_final_stable_seconds = (
                resolve_mic_loop_tuning(
                    profile=args.mic_profile,
                    vad_aggressiveness=args.vad_aggressiveness,
                    final_stable_seconds=args.final_stable_seconds,
                )
            )
            validate_mic_loop_options(resolved_vad_aggressiveness)
            validate_final_stable_seconds(resolved_final_stable_seconds)
            if args.mic_tuning_format == "json":
                print(
                    json.dumps(
                        build_mic_tuning_data(
                            profile=args.mic_profile,
                            vad_aggressiveness=resolved_vad_aggressiveness,
                            final_stable_seconds=resolved_final_stable_seconds,
                        ),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print(
                    format_mic_loop_tuning(
                        profile=args.mic_profile,
                        vad_aggressiveness=resolved_vad_aggressiveness,
                        final_stable_seconds=resolved_final_stable_seconds,
                    )
                )
            return 0
        if args.show_runtime_status:
            status = get_runtime_status()
            if args.runtime_status_format == "json":
                print(json.dumps(status, ensure_ascii=False, indent=2))
            else:
                print(format_runtime_status(status))
            return 0
        validate_model_name(args.model)
        ensure_ffmpeg_available()
        if args.command_only:
            args.emit_command = True
        if args.mic and args.mic_loop:
            raise AudioInputError("--mic and --mic-loop cannot be used together")
        validate_iterations(args.iterations)
        if args.iterations is not None and not args.mic_loop:
            raise AudioInputError("--iterations can only be used with --mic-loop")
        if args.mic_loop:
            validate_mic_profile(args.mic_profile)
            resolved_vad_aggressiveness, resolved_final_stable_seconds = (
                resolve_mic_loop_tuning(
                    profile=args.mic_profile,
                    vad_aggressiveness=args.vad_aggressiveness,
                    final_stable_seconds=args.final_stable_seconds,
                )
            )
            validate_mic_loop_options(resolved_vad_aggressiveness)
            validate_final_stable_seconds(resolved_final_stable_seconds)
            if args.audio_file is not None:
                raise AudioInputError("audio_file cannot be used together with --mic-loop")
            return run_mic_loop(
                duration=args.duration,
                mic_device=args.mic_device,
                model_name=args.model,
                language=args.language,
                iterations=args.iterations,
                trim_silence_enabled=not args.no_trim_silence,
                emit_command=args.emit_command,
                command_only=args.command_only,
                command_output=args.command_output,
                mic_profile=args.mic_profile,
                vad_aggressiveness=resolved_vad_aggressiveness,
                final_stable_seconds=resolved_final_stable_seconds,
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

    if args.command_only:
        print_agent_instruction_only(text)
    else:
        print(text)
        print_agent_instruction_if_requested(text, emit_command=args.emit_command)
    save_handoff_if_requested(text, args.command_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
