"""Minimal smoke tests for the CLI."""

from __future__ import annotations

import io
import contextlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from src.core.codex_bridge import (
    build_codex_payload,
    get_default_codex_output_path,
    get_default_codex_text_path,
    load_codex_handoff_bundle,
    render_codex_prompt,
    save_codex_handoff_bundle,
    save_codex_payload,
)
from src.core.llm import build_codex_instruction
from src.main import (
    format_transcription_result,
    maybe_finalize_on_silence,
    normalize_transcript_text,
    print_codex_instruction_only,
    should_mark_result_final,
)
from src.codex_handoff import render_handoff_output
from src.codex_runner import normalize_command_args
from src.core.pipeline import TranscriptionResult
from src.web.app import create_app


PROJECT_ROOT = Path(__file__).resolve().parent


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the CLI and capture its output."""
    command = [sys.executable, "-m", "src.main", *args]
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_handoff_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the Codex handoff CLI and capture its output."""
    command = [sys.executable, "-m", "src.codex_handoff", *args]
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_runner_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the Codex runner CLI and capture its output."""
    command = [sys.executable, "-m", "src.codex_runner", *args]
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class SmokeTests(unittest.TestCase):
    """Smoke tests for the current CLI behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_sample_audio_succeeds(self) -> None:
        """Sample audio should transcribe successfully."""
        result = run_cli("data/sample_audio.mp3", "--language", "ja")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("こんにちは", result.stdout)

    def test_missing_file_fails_with_input_error(self) -> None:
        """Missing files should return an input error."""
        result = run_cli("no_such_file.wav")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: audio file not found", result.stdout)

    def test_invalid_model_fails_with_input_error(self) -> None:
        """Invalid model names should return an input error."""
        result = run_cli("data/sample_audio.mp3", "--model", "notamodel")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: invalid Whisper model name", result.stdout)

    def test_command_only_outputs_instruction_text(self) -> None:
        """command-only mode should print only the normalized instruction."""
        result = run_cli("data/sample_audio.mp3", "--language", "ja", "--command-only")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("こんにちは", result.stdout)
        self.assertNotIn("[command]", result.stdout)

    def test_command_output_writes_payload_json(self) -> None:
        """command-output should save a Codex payload JSON file."""
        output_path = PROJECT_ROOT / ".cache" / "tests" / "command_payload.json"
        text_path = output_path.with_suffix(".txt")
        if output_path.exists():
            output_path.unlink()
        if text_path.exists():
            text_path.unlink()
        result = run_cli(
            "data/sample_audio.mp3",
            "--language",
            "ja",
            "--command-output",
            str(output_path),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(output_path.exists())
        self.assertTrue(text_path.exists())
        payload_json = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertIn("こんにちは", payload_json["transcript"])
        self.assertEqual(payload_json["command"], payload_json["transcript"].strip())
        output_path.unlink()
        text_path.unlink()

    def test_iterations_requires_mic_loop(self) -> None:
        """Iterations should only be accepted with mic-loop."""
        result = run_cli("--iterations", "2", "data/sample_audio.mp3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: --iterations can only be used with --mic-loop", result.stdout)

    def test_iterations_must_be_positive(self) -> None:
        """Mic-loop iterations must be greater than zero."""
        result = run_cli("--mic-loop", "--duration", "1", "--iterations", "0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: --iterations must be greater than 0", result.stdout)

    def test_no_trim_silence_argument_is_accepted(self) -> None:
        """no-trim-silence should parse and follow normal validation flow."""
        result = run_cli("--mic", "--duration", "1", "--no-trim-silence", "data/sample_audio.mp3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: audio_file cannot be used together with --mic", result.stdout)

    def test_web_index_loads(self) -> None:
        """Web UI index page should load."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ai_core Web UI", response.get_data(as_text=True))
        self.assertIn("upload_command_only", response.get_data(as_text=True))
        self.assertIn("record_command_only", response.get_data(as_text=True))
        self.assertIn("upload_save_command", response.get_data(as_text=True))
        self.assertIn("record_save_command", response.get_data(as_text=True))

    def test_webrtcvad_dependency_is_available(self) -> None:
        """webrtcvad should be importable after dependency sync."""
        import importlib

        module = importlib.import_module("_webrtcvad")
        self.assertTrue(hasattr(module, "create"))

    def test_web_upload_transcribes_sample_audio(self) -> None:
        """Web UI upload route should transcribe sample audio."""
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_file": (io.BytesIO(sample_path.read_bytes()), "sample_audio.mp3"),
            "model": "small",
            "language": "ja",
        }
        response = self.client.post(
            "/transcribe-upload",
            data=payload,
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("こんにちは", response.get_data(as_text=True))

    def test_web_upload_fetch_returns_json(self) -> None:
        """Fetch-style upload should return JSON for partial page updates."""
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_file": (io.BytesIO(sample_path.read_bytes()), "sample_audio.mp3"),
            "model": "small",
            "language": "ja",
        }
        response = self.client.post(
            "/transcribe-upload",
            data=payload,
            content_type="multipart/form-data",
            headers={"X-Requested-With": "fetch"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertIn("こんにちは", payload_json["transcript"])
        self.assertEqual(payload_json["command"], payload_json["transcript"].strip())

    def test_web_upload_fetch_command_only_returns_command_without_transcript(self) -> None:
        """Fetch-style upload should support command-only responses."""
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_file": (io.BytesIO(sample_path.read_bytes()), "sample_audio.mp3"),
            "model": "small",
            "language": "ja",
            "command_only": "true",
        }
        response = self.client.post(
            "/transcribe-upload",
            data=payload,
            content_type="multipart/form-data",
            headers={"X-Requested-With": "fetch"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertEqual(payload_json["transcript"], "")
        self.assertIn("こんにちは", payload_json["command"])

    def test_api_upload_returns_json(self) -> None:
        """Dedicated API upload route should return JSON."""
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_file": (io.BytesIO(sample_path.read_bytes()), "sample_audio.mp3"),
            "model": "small",
            "language": "ja",
        }
        response = self.client.post(
            "/api/transcribe-upload",
            data=payload,
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertIn("こんにちは", payload_json["transcript"])
        self.assertEqual(payload_json["command"], payload_json["transcript"].strip())

    def test_api_upload_command_only_returns_command_without_transcript(self) -> None:
        """Dedicated API upload route should support command-only responses."""
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_file": (io.BytesIO(sample_path.read_bytes()), "sample_audio.mp3"),
            "model": "small",
            "language": "ja",
            "command_only": "true",
        }
        response = self.client.post(
            "/api/transcribe-upload",
            data=payload,
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertEqual(payload_json["transcript"], "")
        self.assertIn("こんにちは", payload_json["command"])

    def test_api_upload_can_save_command_payload(self) -> None:
        """API upload route should optionally save the Codex payload."""
        output_path = get_default_codex_output_path(source="web")
        text_path = get_default_codex_text_path(source="web")
        if output_path.exists():
            output_path.unlink()
        if text_path.exists():
            text_path.unlink()
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_file": (io.BytesIO(sample_path.read_bytes()), "sample_audio.mp3"),
            "model": "small",
            "language": "ja",
            "save_command": "true",
        }
        response = self.client.post(
            "/api/transcribe-upload",
            data=payload,
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertEqual(payload_json["command_path"], str(output_path))
        self.assertEqual(payload_json["command_text_path"], str(text_path))
        self.assertTrue(output_path.exists())
        self.assertTrue(text_path.exists())
        output_path.unlink()
        text_path.unlink()

    def test_api_codex_handoff_latest_returns_saved_bundle(self) -> None:
        """Latest handoff API should return saved prompt bundle contents."""
        output_path = get_default_codex_output_path(source="web")
        text_path = get_default_codex_text_path(source="web")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=output_path,
            text_path=text_path,
        )
        response = self.client.get("/api/codex-handoff-latest?source=web")
        self.assertEqual(response.status_code, 200)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertEqual(payload_json["command"], "依存関係を確認して")
        self.assertIn("Voice transcript:", payload_json["prompt_text"])
        output_path.unlink()
        text_path.unlink()

    def test_api_codex_handoff_latest_returns_404_without_bundle(self) -> None:
        """Latest handoff API should return 404 when no bundle exists."""
        output_path = get_default_codex_output_path(source="missing")
        text_path = get_default_codex_text_path(source="missing")
        if output_path.exists():
            output_path.unlink()
        if text_path.exists():
            text_path.unlink()
        response = self.client.get("/api/codex-handoff-latest?source=missing")
        self.assertEqual(response.status_code, 404)

    def test_handoff_cli_reads_latest_prompt(self) -> None:
        """Handoff CLI should print the saved prompt text."""
        json_path = get_default_codex_output_path(source="cli_test")
        text_path = get_default_codex_text_path(source="cli_test")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_handoff_cli("--source", "cli_test", "--format", "prompt")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Voice transcript:", result.stdout)
        json_path.unlink()
        text_path.unlink()

    def test_handoff_cli_reads_latest_command(self) -> None:
        """Handoff CLI should print the saved command text."""
        json_path = get_default_codex_output_path(source="cli_command")
        text_path = get_default_codex_text_path(source="cli_command")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_handoff_cli("--source", "cli_command", "--format", "command")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "依存関係を確認して")
        json_path.unlink()
        text_path.unlink()

    def test_runner_cli_print_only_outputs_prompt(self) -> None:
        """Runner CLI should print the latest prompt in print-only mode."""
        json_path = get_default_codex_output_path(source="runner_print")
        text_path = get_default_codex_text_path(source="runner_print")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_runner_cli("--source", "runner_print", "--print-only")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Voice transcript:", result.stdout)
        json_path.unlink()
        text_path.unlink()

    def test_runner_cli_pipes_prompt_to_command(self) -> None:
        """Runner CLI should pass the rendered prompt to stdin."""
        json_path = get_default_codex_output_path(source="runner_pipe")
        text_path = get_default_codex_text_path(source="runner_pipe")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_runner_cli(
            "--source",
            "runner_pipe",
            "--",
            "python",
            "-c",
            "import sys; print(sys.stdin.read())",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Requested task:", result.stdout)
        json_path.unlink()
        text_path.unlink()

    def test_api_upload_missing_file_returns_400(self) -> None:
        """Dedicated API upload route should validate missing files."""
        response = self.client.post("/api/transcribe-upload", data={}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.is_json)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertIn("音声ファイルを選択してください", payload_json["error"])

    def test_api_browser_recording_returns_json(self) -> None:
        """Dedicated browser-recording API route should return JSON."""
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_blob": (io.BytesIO(sample_path.read_bytes()), "browser_recording.mp3"),
            "model": "small",
            "language": "ja",
        }
        response = self.client.post(
            "/api/transcribe-browser-recording",
            data=payload,
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertIn("こんにちは", payload_json["transcript"])
        self.assertEqual(payload_json["command"], payload_json["transcript"].strip())

    def test_repeat_transcript_marks_result_final(self) -> None:
        """Three consecutive matching transcripts should be treated as final."""
        result = TranscriptionResult(
            source="microphone",
            text="こんにちは",
            is_final=False,
            chunk_count=2,
        )
        self.assertTrue(should_mark_result_final(result, 3, False))

    def test_blank_transcript_does_not_mark_result_final(self) -> None:
        """Blank transcripts should not become final unless loop ends."""
        result = TranscriptionResult(
            source="microphone",
            text="   ",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, 2, False))

    def test_short_transcript_does_not_mark_result_final(self) -> None:
        """Very short repeated transcripts should remain partial."""
        result = TranscriptionResult(
            source="microphone",
            text="はい",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, 3, False))

    def test_single_repeat_does_not_mark_result_final(self) -> None:
        """Two consecutive matching transcripts should still remain partial."""
        result = TranscriptionResult(
            source="microphone",
            text="こんにちは",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, 2, False))

    def test_normalize_transcript_text_collapses_whitespace(self) -> None:
        """Transcript normalization should collapse redundant whitespace."""
        self.assertEqual(normalize_transcript_text("  こんにちは   世界 "), "こんにちは 世界")

    def test_last_iteration_marks_blank_result_final(self) -> None:
        """Last mic-loop iteration should still become final."""
        result = TranscriptionResult(
            source="microphone",
            text="",
            is_final=False,
            chunk_count=3,
        )
        self.assertTrue(should_mark_result_final(result, 0, True))

    def test_format_transcription_result_marks_silence(self) -> None:
        """Silence results should be labeled explicitly."""
        result = TranscriptionResult(
            source="microphone",
            text="",
            is_final=False,
            chunk_count=4,
            is_silence=True,
        )
        self.assertEqual(format_transcription_result(result), "[silence 4] silence detected")

    def test_maybe_finalize_on_silence_returns_final_result(self) -> None:
        """A silence chunk after repeated speech should finalize the last speech."""
        silence_result = TranscriptionResult(
            source="microphone",
            text="",
            is_final=False,
            chunk_count=5,
            is_silence=True,
        )
        last_spoken_result = TranscriptionResult(
            source="microphone",
            text="依存関係を確認して",
            is_final=False,
            chunk_count=4,
        )
        final_result = maybe_finalize_on_silence(
            result=silence_result,
            last_spoken_result=last_spoken_result,
            repeat_count=2,
            finalized_text=None,
        )
        self.assertTrue(final_result.is_final)
        self.assertFalse(final_result.is_silence)
        self.assertEqual(final_result.text, "依存関係を確認して")

    def test_maybe_finalize_on_silence_keeps_silence_without_repeat(self) -> None:
        """Silence should remain silence when speech was not yet stable."""
        silence_result = TranscriptionResult(
            source="microphone",
            text="",
            is_final=False,
            chunk_count=5,
            is_silence=True,
        )
        last_spoken_result = TranscriptionResult(
            source="microphone",
            text="依存関係を確認して",
            is_final=False,
            chunk_count=4,
        )
        final_result = maybe_finalize_on_silence(
            result=silence_result,
            last_spoken_result=last_spoken_result,
            repeat_count=1,
            finalized_text=None,
        )
        self.assertTrue(final_result.is_silence)

    def test_build_codex_instruction_returns_none_for_blank(self) -> None:
        """Blank transcripts should not produce instruction drafts."""
        self.assertIsNone(build_codex_instruction("   "))

    def test_build_codex_instruction_normalizes_whitespace(self) -> None:
        """Instruction drafts should normalize whitespace."""
        draft = build_codex_instruction("  依存関係を   確認して ")
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertEqual(draft.instruction, "依存関係を 確認して")

    def test_build_codex_payload_returns_none_for_blank(self) -> None:
        """Blank transcripts should not produce Codex payloads."""
        self.assertIsNone(build_codex_payload("   "))

    def test_render_codex_prompt_includes_transcript_and_task(self) -> None:
        """Prompt text should include both transcript and requested task."""
        prompt = render_codex_prompt("  依存関係を   確認して ")
        self.assertEqual(
            prompt,
            "Voice transcript:\n依存関係を 確認して\n\nRequested task:\n依存関係を 確認して\n",
        )

    def test_save_codex_payload_writes_json(self) -> None:
        """Codex payload helper should save normalized JSON output."""
        output_path = PROJECT_ROOT / ".cache" / "tests" / "payload_helper.json"
        if output_path.exists():
            output_path.unlink()
        saved_path = save_codex_payload("  依存関係を   確認して ", output_path)
        self.assertEqual(saved_path, output_path)
        payload_json = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(
            payload_json,
            {
                "transcript": "依存関係を 確認して",
                "command": "依存関係を 確認して",
            },
        )
        output_path.unlink()

    def test_save_codex_handoff_bundle_writes_json_and_text(self) -> None:
        """Codex handoff helper should save both JSON and text outputs."""
        json_path = PROJECT_ROOT / ".cache" / "tests" / "handoff_bundle.json"
        text_path = PROJECT_ROOT / ".cache" / "tests" / "handoff_bundle.txt"
        if json_path.exists():
            json_path.unlink()
        if text_path.exists():
            text_path.unlink()
        saved_paths = save_codex_handoff_bundle(
            "  依存関係を   確認して ",
            json_path=json_path,
            text_path=text_path,
        )
        self.assertIsNotNone(saved_paths)
        assert saved_paths is not None
        self.assertEqual(saved_paths.json_path, json_path)
        self.assertEqual(saved_paths.text_path, text_path)
        self.assertEqual(
            text_path.read_text(encoding="utf-8"),
            "Voice transcript:\n依存関係を 確認して\n\nRequested task:\n依存関係を 確認して\n",
        )
        json_path.unlink()
        text_path.unlink()

    def test_load_codex_handoff_bundle_returns_saved_contents(self) -> None:
        """Handoff loader should return saved JSON and prompt text."""
        json_path = get_default_codex_output_path(source="loader_test")
        text_path = get_default_codex_text_path(source="loader_test")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        handoff = load_codex_handoff_bundle(source="loader_test")
        self.assertIsNotNone(handoff)
        assert handoff is not None
        self.assertEqual(handoff.command, "依存関係を確認して")
        self.assertIn("Requested task:", handoff.prompt_text)
        json_path.unlink()
        text_path.unlink()

    def test_render_handoff_output_returns_json(self) -> None:
        """Handoff renderer should support JSON output."""
        json_path = get_default_codex_output_path(source="render_json")
        text_path = get_default_codex_text_path(source="render_json")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        payload_json = json.loads(render_handoff_output("render_json", "json"))
        self.assertEqual(payload_json["command"], "依存関係を確認して")
        json_path.unlink()
        text_path.unlink()

    def test_normalize_command_args_strips_separator(self) -> None:
        """Runner CLI should strip a leading '--' from command args."""
        self.assertEqual(
            normalize_command_args(["--", "python", "-c", "print('ok')"]),
            ["python", "-c", "print('ok')"],
        )

    def test_print_codex_instruction_only_handles_blank(self) -> None:
        """command-only printer should handle blank transcripts."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            print_codex_instruction_only("   ")
        self.assertEqual(buffer.getvalue().strip(), "no instruction draft available")


if __name__ == "__main__":
    unittest.main()
