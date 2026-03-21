"""Minimal smoke tests for the CLI."""

from __future__ import annotations

import io
import contextlib
from pathlib import Path
import subprocess
import sys
import unittest

from src.core.llm import build_codex_instruction
from src.main import (
    format_transcription_result,
    normalize_transcript_text,
    print_codex_instruction_only,
    should_mark_result_final,
)
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
        """Repeated mic-loop transcripts should be treated as final."""
        result = TranscriptionResult(
            source="microphone",
            text="こんにちは",
            is_final=False,
            chunk_count=2,
        )
        self.assertTrue(should_mark_result_final(result, "こんにちは", False))

    def test_blank_transcript_does_not_mark_result_final(self) -> None:
        """Blank transcripts should not become final unless loop ends."""
        result = TranscriptionResult(
            source="microphone",
            text="   ",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, "こんにちは", False))

    def test_short_transcript_does_not_mark_result_final(self) -> None:
        """Very short repeated transcripts should remain partial."""
        result = TranscriptionResult(
            source="microphone",
            text="はい",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, "はい", False))

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
        self.assertTrue(should_mark_result_final(result, None, True))

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

    def test_build_codex_instruction_returns_none_for_blank(self) -> None:
        """Blank transcripts should not produce instruction drafts."""
        self.assertIsNone(build_codex_instruction("   "))

    def test_build_codex_instruction_normalizes_whitespace(self) -> None:
        """Instruction drafts should normalize whitespace."""
        draft = build_codex_instruction("  依存関係を   確認して ")
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertEqual(draft.instruction, "依存関係を 確認して")

    def test_print_codex_instruction_only_handles_blank(self) -> None:
        """command-only printer should handle blank transcripts."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            print_codex_instruction_only("   ")
        self.assertEqual(buffer.getvalue().strip(), "no instruction draft available")


if __name__ == "__main__":
    unittest.main()
