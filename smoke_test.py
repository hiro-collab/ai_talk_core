"""Minimal smoke tests for the CLI."""

from __future__ import annotations

import io
from pathlib import Path
import subprocess
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
