"""Minimal smoke tests for the CLI."""

from __future__ import annotations

import io
import contextlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest import mock

from src.core.handoff_bridge import (
    build_handoff_payload,
    get_default_handoff_output_path,
    get_default_handoff_text_path,
    load_handoff_bundle,
    normalize_handoff_source,
    render_handoff_prompt,
    save_handoff_bundle,
    save_handoff_payload,
)
from src.core.agent_instruction import build_agent_instruction
from src.core.dependency_status import (
    format_dependency_status,
    get_dependency_status,
)
from src.core.finalization import (
    has_stable_duration_for_final,
    maybe_finalize_on_interrupt,
    maybe_finalize_on_silence,
    normalize_transcript_text,
    required_repeat_count_for_final,
    should_mark_result_final,
)
from src.core.input_gate import (
    InputGate,
    InputGateError,
    InputGateEvent,
    parse_input_gate_payload,
)
from src.core.torch_pin_plan import format_torch_pin_plan, get_torch_pin_plan
from src.main import (
    build_input_gate_data,
    build_doctor_status,
    build_mic_profile_list_data,
    build_mic_tuning_data,
    build_torch_pin_status,
    format_doctor_status,
    format_input_gate_state,
    format_mic_profile_list,
    format_mic_loop_tuning,
    format_runtime_status,
    format_transcription_result,
    print_agent_instruction_only,
    print_runtime_note,
    resolve_mic_loop_tuning,
    validate_final_stable_seconds,
    validate_mic_profile,
)
from src.io.audio import should_retry_model_load_on_cpu
from src.io.audio import AudioInputError
from src.io.audio import AudioEnvironmentError
from src.io.audio import get_runtime_status
from src.io.microphone import (
    get_microphone_runtime_status,
    list_ffmpeg_dshow_audio_devices,
    record_microphone_audio,
    resolve_microphone_backend,
    validate_vad_aggressiveness,
)
from src.codex_handoff import render_handoff_output
from src.codex_runner import (
    build_template_command,
    normalize_command_args,
    resolve_runner_command,
    validate_runner_command_available,
)
from src.ollama_runner import build_ollama_command
from src.core.pipeline import AudioChunk, TranscriptionResult
from src.core.session import MicLoopSession, MicLoopTuning
from src.drivers import DriverRequest, DriverResponse, DriverResult, dispatch_driver_request
from src.runners.common import emit_driver_result, execute_runner_command
from src.web.app import build_input_gate_response, create_app, render_page
from src.web.transcription_service import WebTranscriptionRequest, process_web_transcription


PROJECT_ROOT = Path(__file__).resolve().parent

build_codex_payload = build_handoff_payload
build_codex_instruction = build_agent_instruction
get_default_codex_output_path = get_default_handoff_output_path
get_default_codex_text_path = get_default_handoff_text_path
load_codex_handoff_bundle = load_handoff_bundle
render_codex_prompt = render_handoff_prompt
save_codex_handoff_bundle = save_handoff_bundle
save_codex_payload = save_handoff_payload


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


def run_agent_handoff_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the generic agent handoff CLI and capture its output."""
    command = [sys.executable, "-m", "src.agent_handoff", *args]
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


def run_agent_runner_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the generic agent runner CLI and capture its output."""
    command = [sys.executable, "-m", "src.agent_runner", *args]
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

    def local_api_headers(self) -> dict[str, str]:
        return {"X-AI-Core-Token": self.app.config["LOCAL_API_TOKEN"]}

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

    def test_instruction_only_alias_outputs_instruction_text(self) -> None:
        """instruction-only alias should behave like command-only."""
        result = run_cli("data/sample_audio.mp3", "--language", "ja", "--instruction-only")
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

    def test_handoff_output_alias_writes_payload_json(self) -> None:
        """handoff-output alias should save the same payload bundle."""
        output_path = PROJECT_ROOT / ".cache" / "tests" / "handoff_payload.json"
        text_path = output_path.with_suffix(".txt")
        if output_path.exists():
            output_path.unlink()
        if text_path.exists():
            text_path.unlink()
        result = run_cli(
            "data/sample_audio.mp3",
            "--language",
            "ja",
            "--handoff-output",
            str(output_path),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(output_path.exists())
        self.assertTrue(text_path.exists())
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

    def test_vad_aggressiveness_must_be_in_supported_range(self) -> None:
        """Mic-loop VAD aggressiveness should be validated."""
        result = run_cli("--mic-loop", "--duration", "1", "--vad-aggressiveness", "9")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: VAD aggressiveness must be one of: 0, 1, 2, 3", result.stdout)

    def test_mic_profile_must_be_supported_value(self) -> None:
        """Mic-loop profile should reject unknown values."""
        result = run_cli("--mic-loop", "--duration", "1", "--mic-profile", "fastish")
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Input error: --mic-profile must be one of: responsive, balanced, strict",
            result.stdout,
        )

    def test_list_mic_profiles_prints_available_profiles(self) -> None:
        """Profile listing should print all available tuning presets."""
        result = run_cli("--list-mic-profiles")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Available mic-loop profiles:", result.stdout)
        self.assertIn("responsive", result.stdout)
        self.assertIn("balanced", result.stdout)
        self.assertIn("strict", result.stdout)

    def test_list_mic_profiles_can_return_json(self) -> None:
        """Profile listing should support JSON output."""
        result = run_cli("--list-mic-profiles", "--mic-tuning-format", "json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["profile"], "responsive")
        self.assertIn("description", payload[0])

    def test_show_mic_tuning_uses_profile_defaults(self) -> None:
        """show-mic-tuning should print the resolved default preset values."""
        result = run_cli("--show-mic-tuning", "--mic-profile", "strict")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(
            "[mic-tuning] profile=strict vad_aggressiveness=3 final_stable_seconds=10",
            result.stdout,
        )

    def test_show_mic_tuning_applies_explicit_overrides(self) -> None:
        """show-mic-tuning should reflect CLI overrides over preset defaults."""
        result = run_cli(
            "--show-mic-tuning",
            "--mic-profile",
            "responsive",
            "--vad-aggressiveness",
            "3",
            "--final-stable-seconds",
            "9",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(
            "[mic-tuning] profile=responsive vad_aggressiveness=3 final_stable_seconds=9",
            result.stdout,
        )

    def test_show_mic_tuning_can_return_json(self) -> None:
        """Resolved tuning should support JSON output."""
        result = run_cli(
            "--show-mic-tuning",
            "--mic-profile",
            "balanced",
            "--mic-tuning-format",
            "json",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["profile"], "balanced")
        self.assertEqual(payload["vad_aggressiveness"], 2)
        self.assertEqual(payload["final_stable_seconds"], 8)

    def test_show_input_gate_can_return_json(self) -> None:
        """Input-gate status should be inspectable without starting audio capture."""
        result = run_cli(
            "--show-input-gate",
            "--input-disabled",
            "--input-gate-reason",
            "sword_sign",
            "--input-gate-format",
            "json",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["input_enabled"])
        self.assertEqual(payload["reason"], "sword_sign")
        self.assertEqual(payload["source"], "cli")

    def test_show_runtime_status_can_return_json(self) -> None:
        """Runtime status should support JSON output."""
        result = run_cli("--show-runtime-status", "--runtime-status-format", "json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("ffmpeg_available", payload)
        self.assertIn("ffprobe_available", payload)
        self.assertIn("nvidia_smi_available", payload)
        self.assertIn("torch_cuda_available", payload)
        self.assertIn("transcription_device", payload)
        self.assertIn("suggested_action", payload)

    def test_show_dependency_status_can_return_json(self) -> None:
        """Dependency status should support JSON output."""
        result = run_cli("--show-dependency-status", "--dependency-status-format", "json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("direct_dependencies", payload)
        self.assertIn("installed_versions", payload)
        self.assertIn("torch_direct_dependency", payload)

    def test_doctor_can_return_json(self) -> None:
        """Doctor output should support JSON output."""
        result = run_cli("--doctor", "--doctor-format", "json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("runtime", payload)
        self.assertIn("microphone", payload)
        self.assertIn("dependencies", payload)

    def test_torch_pin_plan_can_return_json(self) -> None:
        """Torch pin plan output should support JSON output."""
        result = run_cli("--show-torch-pin-plan", "--torch-pin-plan-format", "json")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("steps", payload)
        self.assertIn("command_examples", payload)

    def test_final_stable_seconds_must_be_positive(self) -> None:
        """Mic-loop stable duration threshold should be validated."""
        result = run_cli("--mic-loop", "--duration", "1", "--final-stable-seconds", "0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: --final-stable-seconds must be greater than 0", result.stdout)

    def test_no_trim_silence_argument_is_accepted(self) -> None:
        """no-trim-silence should parse and follow normal validation flow."""
        result = run_cli("--mic", "--duration", "1", "--no-trim-silence", "data/sample_audio.mp3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error: audio_file cannot be used together with --mic", result.stdout)

    def test_web_index_loads(self) -> None:
        """Web UI index page should load."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("ai_core Web UI", page)
        self.assertIn("upload_instruction_only", page)
        self.assertIn("record_instruction_only", page)
        self.assertIn("record_gate_auto", page)
        self.assertIn("upload_save_handoff", page)
        self.assertIn("record_save_handoff", page)
        self.assertIn("data-api-doctor", page)
        self.assertIn("data-api-input-gate", page)
        self.assertIn("data-api-token", page)
        self.assertIn("app.css", page)
        self.assertIn("app.js", page)
        self.assertIn("待機中", page)
        self.assertIn("active-microphone", page)
        self.assertIn("開発者向けデバッグ情報", page)
        self.assertIn("diag-input-gate", page)

    def test_web_static_assets_load(self) -> None:
        """Web UI CSS and JS assets should be served separately."""
        css_response = self.client.get("/static/app.css")
        js_response = self.client.get("/static/app.js")
        try:
            self.assertEqual(css_response.status_code, 200)
            self.assertEqual(js_response.status_code, 200)
            self.assertIn("text/css", css_response.content_type)
            self.assertIn("javascript", js_response.content_type)
            js_text = js_response.get_data(as_text=True)
            self.assertNotIn("指示草案:\\\\n", js_text)
            self.assertNotIn('join("\\\\n")', js_text)
            self.assertIn("handleInputGateRecording", js_text)
            self.assertIn("startRecording", js_text)
        finally:
            css_response.close()
            js_response.close()

    def test_web_favicon_loads(self) -> None:
        """Web UI should not emit a missing favicon request."""
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/svg+xml", response.content_type)

    def test_api_doctor_returns_runtime_sections(self) -> None:
        """Web UI should expose doctor status for diagnostics display."""
        response = self.client.get("/api/doctor")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        self.assertIn("runtime", payload)
        self.assertIn("microphone", payload)
        self.assertIn("dependencies", payload)
        self.assertIn("selected_microphone_device", payload["microphone"])

    def test_api_input_gate_returns_current_state(self) -> None:
        """Web UI should expose current input-gate state."""
        response = self.client.get("/api/input-gate")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        self.assertTrue(payload["ok"])
        self.assertIn("input_enabled", payload["input_gate"])

    def test_api_input_gate_updates_state(self) -> None:
        """Web UI should accept backend-neutral input-gate payloads."""
        response = self.client.post(
            "/api/input-gate",
            json={
                "input_enabled": False,
                "reason": "sword_sign",
                "source": "sword_voice_agent",
                "timestamp": 12.5,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        self.assertFalse(payload["input_gate"]["input_enabled"])
        self.assertEqual(payload["input_gate"]["reason"], "sword_sign")
        self.assertEqual(payload["input_gate"]["source"], "sword_voice_agent")

    def test_api_input_gate_rejects_invalid_payload(self) -> None:
        """Web UI should reject malformed input-gate payloads."""
        response = self.client.post("/api/input-gate", json={"input_enabled": "yes"})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        self.assertFalse(payload["ok"])

    def test_build_input_gate_response_wraps_state_payload(self) -> None:
        """Input-gate response helper should return a stable envelope."""
        response = build_input_gate_response(InputGate(initially_enabled=False).state)
        self.assertTrue(response["ok"])
        self.assertFalse(response["input_gate"]["input_enabled"])

    def test_render_page_with_prompt_only_omits_empty_handoff_label(self) -> None:
        """Prompt-only results should not render an empty handoff label."""
        with self.app.test_request_context("/"):
            page = render_page(command_text_path="/tmp/web_latest.txt")
        self.assertIn("プロンプト保存先:\n/tmp/web_latest.txt", page)
        self.assertNotIn("handoff 保存先:\n\nプロンプト保存先", page)

    def test_render_page_places_handoff_paths_after_result_actions(self) -> None:
        """Handoff paths should sit directly after the related action buttons."""
        with self.app.test_request_context("/"):
            page = render_page(
                transcript="hello",
                command="say hello",
                command_path=r"C:\tmp\web_latest.json",
                command_text_path=r"C:\tmp\web_latest.txt",
            )
        self.assertLess(page.index('id="result-actions"'), page.index('id="page-meta"'))
        self.assertIn("handoff 保存先:\nC:\\tmp\\web_latest.json", page)
        self.assertIn("プロンプト保存先:\nC:\\tmp\\web_latest.txt", page)

    def test_webrtcvad_dependency_is_available(self) -> None:
        """webrtcvad should be importable after dependency sync."""
        import importlib

        module = importlib.import_module("_webrtcvad")
        self.assertTrue(hasattr(module, "create"))

    def test_validate_vad_aggressiveness_accepts_supported_values(self) -> None:
        """Supported VAD aggressiveness values should pass validation."""
        for value in (0, 1, 2, 3):
            validate_vad_aggressiveness(value)

    def test_resolve_microphone_backend_uses_os_default(self) -> None:
        """Auto microphone backend should select the OS-specific recorder."""
        with mock.patch("src.io.microphone.platform.system", return_value="Windows"):
            self.assertEqual(resolve_microphone_backend("auto"), "ffmpeg-dshow")
        with mock.patch("src.io.microphone.platform.system", return_value="Linux"):
            self.assertEqual(resolve_microphone_backend("auto"), "arecord")

    def test_list_ffmpeg_dshow_audio_devices_parses_audio_section(self) -> None:
        """DirectShow device parsing should extract only audio device names."""
        dshow_output = "\n".join(
            [
                "[dshow @ 000] DirectShow video devices",
                '[dshow @ 000]  "HD Pro Webcam C920"',
                "[dshow @ 000] DirectShow audio devices",
                '[dshow @ 000]  "Microphone Array (Realtek(R) Audio)"',
                '[dshow @ 000]     Alternative name "@device_cm_{abc}"',
            ]
        )
        with mock.patch(
            "src.io.microphone.platform.system",
            return_value="Windows",
        ), mock.patch(
            "src.io.microphone.ensure_ffmpeg_available",
        ), mock.patch(
            "src.io.microphone.subprocess.run"
        ) as subprocess_run:
            subprocess_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr=dshow_output,
            )
            self.assertEqual(
                list_ffmpeg_dshow_audio_devices(),
                ["Microphone Array (Realtek(R) Audio)"],
            )

    def test_list_ffmpeg_dshow_audio_devices_parses_typed_lines(self) -> None:
        """DirectShow parsing should support ffmpeg lines marked with (audio)."""
        dshow_output = "\n".join(
            [
                '[dshow @ 000] "OBS Virtual Camera" (video)',
                '[dshow @ 000] "Webcam 4 (NDI Webcam Audio)" (audio)',
                '[dshow @ 000] "HD Pro Webcam C920" (none)',
            ]
        )
        with mock.patch(
            "src.io.microphone.platform.system",
            return_value="Windows",
        ), mock.patch(
            "src.io.microphone.ensure_ffmpeg_available",
        ), mock.patch(
            "src.io.microphone.subprocess.run"
        ) as subprocess_run:
            subprocess_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=dshow_output,
                stderr="",
            )
            self.assertEqual(
                list_ffmpeg_dshow_audio_devices(),
                ["Webcam 4 (NDI Webcam Audio)"],
            )

    def test_record_microphone_audio_uses_arecord_backend(self) -> None:
        """Linux microphone backend should keep the existing arecord command shape."""
        output_path = PROJECT_ROOT / ".cache" / "tests" / "mic_arecord.wav"
        with mock.patch(
            "src.io.microphone.ensure_arecord_available"
        ), mock.patch(
            "src.io.microphone.get_default_arecord_microphone_device",
            return_value="plughw:1,0",
        ), mock.patch(
            "src.io.microphone.subprocess.run"
        ) as subprocess_run:
            subprocess_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            result = record_microphone_audio(
                output_path=output_path,
                duration=2,
                backend="arecord",
                trim_silence_enabled=False,
            )
        command = subprocess_run.call_args.args[0]
        self.assertEqual(result, output_path)
        self.assertEqual(command[:2], ["arecord", "-D"])
        self.assertIn("plughw:1,0", command)

    def test_record_microphone_audio_uses_ffmpeg_dshow_backend(self) -> None:
        """Windows microphone backend should record through ffmpeg DirectShow."""
        output_path = PROJECT_ROOT / ".cache" / "tests" / "mic_dshow.wav"
        with mock.patch(
            "src.io.microphone.platform.system",
            return_value="Windows",
        ), mock.patch(
            "src.io.microphone.ensure_ffmpeg_available"
        ), mock.patch(
            "src.io.microphone.subprocess.run"
        ) as subprocess_run:
            subprocess_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            result = record_microphone_audio(
                output_path=output_path,
                duration=2,
                device="Microphone Array (Realtek(R) Audio)",
                backend="ffmpeg-dshow",
                trim_silence_enabled=False,
            )
        command = subprocess_run.call_args.args[0]
        self.assertEqual(result, output_path)
        self.assertEqual(command[:4], ["ffmpeg", "-y", "-f", "dshow"])
        self.assertIn("audio=Microphone Array (Realtek(R) Audio)", command)
        self.assertIn("pcm_s16le", command)

    def test_get_microphone_runtime_status_reports_backend_availability(self) -> None:
        """Microphone status should expose OS defaults and backend availability."""
        with mock.patch(
            "src.io.microphone.platform.system",
            return_value="Windows",
        ), mock.patch(
            "src.io.microphone.shutil.which",
            side_effect=lambda name: "C:\\ffmpeg\\bin\\ffmpeg.exe"
            if name == "ffmpeg"
            else None,
        ):
            status = get_microphone_runtime_status()
        self.assertEqual(status["default_microphone_backend"], "ffmpeg-dshow")
        self.assertTrue(status["selected_microphone_backend_available"])
        self.assertIn("ffmpeg-dshow", status["available_microphone_backends"])

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

    def test_api_upload_instruction_only_alias_returns_command_without_transcript(self) -> None:
        """Dedicated API upload route should also accept instruction_only."""
        sample_path = PROJECT_ROOT / "data" / "sample_audio.mp3"
        payload = {
            "audio_file": (io.BytesIO(sample_path.read_bytes()), "sample_audio.mp3"),
            "model": "small",
            "language": "ja",
            "instruction_only": "true",
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

    def test_api_upload_can_save_handoff_alias(self) -> None:
        """API upload route should also accept save_handoff."""
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
            "save_handoff": "true",
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
        response = self.client.get(
            "/api/codex-handoff-latest?source=web",
            headers=self.local_api_headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertEqual(payload_json["command"], "依存関係を確認して")
        self.assertIn("Voice transcript:", payload_json["prompt_text"])
        output_path.unlink()
        text_path.unlink()

    def test_api_agent_handoff_latest_returns_saved_bundle(self) -> None:
        """Agent handoff API alias should return saved prompt bundle contents."""
        output_path = get_default_codex_output_path(source="web")
        text_path = get_default_codex_text_path(source="web")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=output_path,
            text_path=text_path,
        )
        response = self.client.get(
            "/api/agent-handoff-latest?source=web",
            headers=self.local_api_headers(),
        )
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
        response = self.client.get(
            "/api/codex-handoff-latest?source=missing",
            headers=self.local_api_headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_api_agent_handoff_latest_returns_404_without_bundle(self) -> None:
        """Agent handoff API alias should return 404 when no bundle exists."""
        output_path = get_default_codex_output_path(source="missing")
        text_path = get_default_codex_text_path(source="missing")
        if output_path.exists():
            output_path.unlink()
        if text_path.exists():
            text_path.unlink()
        response = self.client.get(
            "/api/agent-handoff-latest?source=missing",
            headers=self.local_api_headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_api_handoff_latest_requires_local_token(self) -> None:
        """Latest handoff API should require the local per-process token."""
        response = self.client.get("/api/agent-handoff-latest?source=web")
        self.assertEqual(response.status_code, 403)

    def test_api_handoff_latest_rejects_invalid_source(self) -> None:
        """Latest handoff API should reject path-like source values."""
        response = self.client.get(
            "/api/agent-handoff-latest?source=../web",
            headers=self.local_api_headers(),
        )
        self.assertEqual(response.status_code, 400)

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

    def test_handoff_source_rejects_path_segments(self) -> None:
        """Handoff source labels should not be usable as path components."""
        with self.assertRaises(ValueError):
            normalize_handoff_source("../web")
        with self.assertRaises(ValueError):
            get_default_codex_output_path(source="../web")

    def test_handoff_cli_rejects_invalid_source(self) -> None:
        """Handoff CLI should return a normal input error for invalid sources."""
        result = run_agent_handoff_cli("--source", "../web", "--format", "prompt")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input error:", result.stdout)

    def test_agent_handoff_cli_reads_latest_prompt(self) -> None:
        """Generic agent handoff CLI should print the saved prompt text."""
        json_path = get_default_codex_output_path(source="agent_cli_test")
        text_path = get_default_codex_text_path(source="agent_cli_test")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_agent_handoff_cli("--source", "agent_cli_test", "--format", "prompt")
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

    def test_agent_handoff_cli_reads_latest_command(self) -> None:
        """Generic agent handoff CLI should print the saved command text."""
        json_path = get_default_codex_output_path(source="agent_cli_command")
        text_path = get_default_codex_text_path(source="agent_cli_command")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_agent_handoff_cli("--source", "agent_cli_command", "--format", "command")
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

    def test_agent_runner_cli_print_only_outputs_prompt(self) -> None:
        """Generic agent runner CLI should print the latest prompt in print-only mode."""
        json_path = get_default_codex_output_path(source="agent_runner_print")
        text_path = get_default_codex_text_path(source="agent_runner_print")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_agent_runner_cli("--source", "agent_runner_print", "--print-only")
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

    def test_runner_cli_template_cat_outputs_prompt(self) -> None:
        """Runner CLI should support built-in command templates."""
        json_path = get_default_codex_output_path(source="runner_template")
        text_path = get_default_codex_text_path(source="runner_template")
        save_codex_handoff_bundle(
            "依存関係を確認して",
            json_path=json_path,
            text_path=text_path,
        )
        result = run_runner_cli("--source", "runner_template", "--template", "cat")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Voice transcript:", result.stdout)
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

    def test_api_upload_rejects_cross_origin_post(self) -> None:
        """Local Web API should reject browser posts from another origin."""
        response = self.client.post(
            "/api/transcribe-upload",
            data={},
            content_type="multipart/form-data",
            headers={"Origin": "http://example.com"},
        )
        self.assertEqual(response.status_code, 403)

    def test_api_upload_rejects_oversized_request(self) -> None:
        """Flask should reject uploads that exceed the configured byte limit."""
        original_limit = self.app.config["MAX_CONTENT_LENGTH"]
        self.app.config["MAX_CONTENT_LENGTH"] = 128
        try:
            response = self.client.post(
                "/api/transcribe-upload",
                data={
                    "audio_file": (io.BytesIO(b"x" * 1024), "sample.wav"),
                },
                content_type="multipart/form-data",
            )
        finally:
            self.app.config["MAX_CONTENT_LENGTH"] = original_limit
        self.assertEqual(response.status_code, 413)
        payload_json = response.get_json()
        self.assertIsNotNone(payload_json)
        self.assertIn("大きすぎます", payload_json["error"])

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
        self.assertTrue(should_mark_result_final(result, 3, False, 3, 8))

    def test_blank_transcript_does_not_mark_result_final(self) -> None:
        """Blank transcripts should not become final unless loop ends."""
        result = TranscriptionResult(
            source="microphone",
            text="   ",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, 2, False, 3, 8))

    def test_short_transcript_does_not_mark_result_final(self) -> None:
        """Very short repeated transcripts should remain partial."""
        result = TranscriptionResult(
            source="microphone",
            text="はい",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, 3, False, 3, 8))

    def test_single_repeat_does_not_mark_result_final(self) -> None:
        """Two consecutive matching transcripts should still remain partial."""
        result = TranscriptionResult(
            source="microphone",
            text="こんにちは",
            is_final=False,
            chunk_count=2,
        )
        self.assertFalse(should_mark_result_final(result, 2, False, 3, 8))

    def test_long_transcript_marks_result_final_with_two_repeats(self) -> None:
        """Longer stable transcripts may finalize after two repeats."""
        result = TranscriptionResult(
            source="microphone",
            text="依存関係を確認してから進めてください",
            is_final=False,
            chunk_count=2,
        )
        self.assertTrue(should_mark_result_final(result, 2, False, 3, 8))

    def test_normalize_transcript_text_collapses_whitespace(self) -> None:
        """Transcript normalization should collapse redundant whitespace."""
        self.assertEqual(normalize_transcript_text("  こんにちは   世界 "), "こんにちは 世界")

    def test_required_repeat_count_for_final_relaxes_for_long_text(self) -> None:
        """Longer transcripts should require fewer repeats."""
        self.assertEqual(required_repeat_count_for_final("依存関係を確認してから進めてください"), 2)
        self.assertEqual(required_repeat_count_for_final("こんにちは"), 3)

    def test_stable_duration_for_final_accepts_medium_text_after_longer_time(self) -> None:
        """Time stability should help medium-length transcripts become final."""
        self.assertTrue(has_stable_duration_for_final("依存関係を確認して", 2, 4, 8))

    def test_stable_duration_for_final_ignores_short_text(self) -> None:
        """Very short text should not finalize only from elapsed time."""
        self.assertFalse(has_stable_duration_for_final("はい", 4, 3, 8))

    def test_stable_duration_for_final_uses_configured_threshold(self) -> None:
        """Stable-duration finalization should respect the configured threshold."""
        self.assertFalse(has_stable_duration_for_final("依存関係を確認して", 2, 3, 8))
        self.assertTrue(has_stable_duration_for_final("依存関係を確認して", 2, 3, 6))

    def test_stable_duration_for_final_requires_more_than_one_repeat(self) -> None:
        """A single long chunk should not finalize only from chunk duration."""
        self.assertFalse(has_stable_duration_for_final("依存関係を確認して", 1, 8, 8))

    def test_validate_final_stable_seconds_accepts_positive_values(self) -> None:
        """Positive stable-duration thresholds should pass validation."""
        validate_final_stable_seconds(1)
        validate_final_stable_seconds(8)

    def test_validate_mic_profile_accepts_supported_values(self) -> None:
        """Supported mic profiles should pass validation."""
        for value in ("responsive", "balanced", "strict"):
            validate_mic_profile(value)

    def test_resolve_mic_loop_tuning_uses_profile_defaults(self) -> None:
        """Mic profile should resolve default VAD and final thresholds."""
        self.assertEqual(resolve_mic_loop_tuning("responsive", None, None), (1, 5))
        self.assertEqual(resolve_mic_loop_tuning("balanced", None, None), (2, 8))
        self.assertEqual(resolve_mic_loop_tuning("strict", None, None), (3, 10))

    def test_resolve_mic_loop_tuning_preserves_explicit_overrides(self) -> None:
        """Explicit CLI overrides should win over profile defaults."""
        self.assertEqual(resolve_mic_loop_tuning("strict", 0, None), (0, 10))
        self.assertEqual(resolve_mic_loop_tuning("responsive", None, 12), (1, 12))
        self.assertEqual(resolve_mic_loop_tuning("balanced", 3, 6), (3, 6))

    def test_format_mic_loop_tuning_reports_resolved_values(self) -> None:
        """Mic-loop tuning formatter should expose the active settings."""
        self.assertEqual(
            format_mic_loop_tuning("balanced", 2, 8),
            "[mic-tuning] profile=balanced vad_aggressiveness=2 final_stable_seconds=8",
        )

    def test_format_mic_profile_list_mentions_profile_details(self) -> None:
        """Profile list formatter should describe the preset values."""
        listing = format_mic_profile_list()
        self.assertIn("responsive", listing)
        self.assertIn("vad_aggressiveness=1", listing)
        self.assertIn("final_stable_seconds=10", listing)

    def test_build_mic_profile_list_data_returns_structured_profiles(self) -> None:
        """Structured profile listing should expose all expected keys."""
        payload = build_mic_profile_list_data()
        self.assertEqual(payload[0]["profile"], "responsive")
        self.assertEqual(payload[1]["vad_aggressiveness"], 2)
        self.assertIn("description", payload[2])

    def test_build_mic_tuning_data_returns_structured_values(self) -> None:
        """Structured tuning data should match the resolved values."""
        self.assertEqual(
            build_mic_tuning_data("strict", 3, 10),
            {
                "profile": "strict",
                "vad_aggressiveness": 3,
                "final_stable_seconds": 10,
            },
        )

    def test_format_runtime_status_mentions_core_fields(self) -> None:
        """Runtime status formatter should expose core runtime keys."""
        text = format_runtime_status(
            {
                "ffmpeg_available": True,
                "ffprobe_available": True,
                "nvidia_smi_available": True,
                "nvidia_driver_version": "535.288.01",
                "nvidia_gpu_name": "NVIDIA GeForce RTX 3070",
                "torch_version": "2.10.0+cu128",
                "torch_cuda_version": "12.8",
                "torch_cuda_available": False,
                "transcription_device": "cpu",
                "whisper_version": "20250625",
                "runtime_note": (
                    "Torch CUDA build is present but unavailable; transcription will use CPU "
                    "fallback. nvidia-smi is available, so a Torch/driver CUDA mismatch or "
                    "local CUDA initialization problem is likely."
                ),
                "suggested_action": (
                    "Inspect the uv-managed Torch version and pin a driver-compatible "
                    "build inside .venv before changing system drivers."
                ),
            }
        )
        self.assertIn("Runtime status:", text)
        self.assertIn("torch_cuda_available: False", text)
        self.assertIn("nvidia_driver_version: 535.288.01", text)
        self.assertIn("transcription_device: cpu", text)
        self.assertIn("ffmpeg_available: True", text)
        self.assertIn("Torch/driver CUDA mismatch", text)
        self.assertIn("uv-managed Torch version", text)

    def test_get_runtime_status_returns_expected_keys(self) -> None:
        """Runtime status helper should return the expected status fields."""
        status = get_runtime_status()
        self.assertIn("ffmpeg_available", status)
        self.assertIn("ffprobe_available", status)
        self.assertIn("nvidia_smi_available", status)
        self.assertIn("nvidia_driver_version", status)
        self.assertIn("nvidia_gpu_name", status)
        self.assertIn("torch_version", status)
        self.assertIn("torch_cuda_build", status)
        self.assertIn("torch_cuda_available", status)
        self.assertIn("transcription_device", status)
        self.assertIn("runtime_note", status)
        self.assertIn("suggested_action", status)

    def test_get_runtime_status_notes_cpu_torch_when_nvidia_is_visible(self) -> None:
        """Runtime status should explain CPU-only Torch when an NVIDIA GPU is visible."""
        def fake_which(name: str) -> str | None:
            if name in {"ffmpeg", "ffprobe", "nvidia-smi"}:
                return name
            return None

        completed = subprocess.CompletedProcess(
            args=["nvidia-smi"],
            returncode=0,
            stdout="596.21, NVIDIA GeForce RTX 3070\n",
            stderr="",
        )
        with (
            mock.patch("src.io.audio.shutil.which", side_effect=fake_which),
            mock.patch("src.io.audio.subprocess.run", return_value=completed),
            mock.patch("src.io.audio.torch.cuda.is_available", return_value=False),
            mock.patch("src.io.audio.torch.version.cuda", None),
            mock.patch("src.io.audio.torch.__version__", "2.10.0+cpu"),
        ):
            status = get_runtime_status()

        self.assertTrue(status["nvidia_smi_available"])
        self.assertFalse(status["torch_cuda_build"])
        self.assertIn("CPU-only", str(status["runtime_note"]))
        self.assertIn(".venv", str(status["suggested_action"]))

    def test_format_dependency_status_mentions_torch_source(self) -> None:
        """Dependency formatter should explain how torch is resolved."""
        text = format_dependency_status(
            {
                "pyproject_path": "/tmp/pyproject.toml",
                "direct_dependencies": ["flask>=3.1.3", "openai-whisper>=20250625"],
                "direct_dependency_names": ["flask", "openai-whisper"],
                "torch_direct_dependency": False,
                "installed_versions": {
                    "flask": "3.1.3",
                    "openai-whisper": "20250625",
                    "setuptools": "82.0.1",
                    "torch": "2.10.0+cu128",
                    "webrtcvad": "2.0.10",
                },
                "dependency_note": (
                    "torch is currently resolved transitively via openai-whisper unless it "
                    "is added explicitly to pyproject.toml."
                ),
            }
        )
        self.assertIn("Dependency status:", text)
        self.assertIn("torch_direct_dependency: False", text)
        self.assertIn("openai-whisper>=20250625", text)
        self.assertIn("transitively via openai-whisper", text)

    def test_get_dependency_status_returns_expected_keys(self) -> None:
        """Dependency status helper should expose direct and installed package state."""
        status = get_dependency_status()
        self.assertIn("direct_dependencies", status)
        self.assertIn("direct_dependency_names", status)
        self.assertIn("torch_direct_dependency", status)
        self.assertIn("installed_versions", status)
        self.assertIn("dependency_note", status)

    def test_format_doctor_status_includes_runtime_and_dependency_sections(self) -> None:
        """Doctor formatter should combine runtime and dependency summaries."""
        text = format_doctor_status(
            {
                "runtime": {
                    "ffmpeg_available": True,
                    "ffprobe_available": True,
                    "nvidia_smi_available": True,
                    "nvidia_driver_version": "535.288.01",
                    "nvidia_gpu_name": "NVIDIA GeForce RTX 3070",
                    "torch_version": "2.10.0+cu128",
                    "torch_cuda_version": "12.8",
                    "torch_cuda_available": False,
                    "transcription_device": "cpu",
                    "whisper_version": "20250625",
                    "runtime_note": "cpu fallback",
                    "suggested_action": "pin torch locally",
                },
                "microphone": {
                    "platform_system": "Windows",
                    "default_microphone_backend": "ffmpeg-dshow",
                    "selected_microphone_backend": "ffmpeg-dshow",
                    "selected_microphone_backend_available": True,
                    "available_microphone_backends": ["ffmpeg-dshow"],
                    "arecord_available": False,
                    "ffmpeg_dshow_available": True,
                    "microphone_note": None,
                },
                "dependencies": {
                    "pyproject_path": "/tmp/pyproject.toml",
                    "direct_dependencies": ["flask>=3.1.3", "openai-whisper>=20250625"],
                    "direct_dependency_names": ["flask", "openai-whisper"],
                    "torch_direct_dependency": False,
                    "installed_versions": {
                        "flask": "3.1.3",
                        "openai-whisper": "20250625",
                        "setuptools": "82.0.1",
                        "torch": "2.10.0+cu128",
                        "webrtcvad": "2.0.10",
                    },
                    "dependency_note": "torch is transitive",
                },
            }
        )
        self.assertIn("Doctor summary:", text)
        self.assertIn("Runtime status:", text)
        self.assertIn("Microphone status:", text)
        self.assertIn("default_microphone_backend: ffmpeg-dshow", text)
        self.assertIn("Dependency status:", text)
        self.assertIn("torch_direct_dependency: False", text)

    def test_build_doctor_status_returns_expected_sections(self) -> None:
        """Doctor status helper should include runtime and dependency sections."""
        status = build_doctor_status()
        self.assertIn("runtime", status)
        self.assertIn("microphone", status)
        self.assertIn("dependencies", status)

    def test_format_torch_pin_plan_includes_steps_and_commands(self) -> None:
        """Torch pin formatter should render plan details."""
        text = format_torch_pin_plan(
            {
                "torch_direct_dependency": False,
                "current_torch_version": "2.10.0+cu128",
                "current_torch_base_version": "2.10.0",
                "current_torch_build_suffix": "cu128",
                "current_torch_cuda_version": "12.8",
                "current_driver_version": "535.288.01",
                "recommended_torch_spec": "torch==2.10.0",
                "recommended_cuda_family": "cu121",
                "pytorch_index_url": "https://download.pytorch.org/whl/cu121",
                "uv_pip_install_command": (
                    "uv pip install --upgrade torch "
                    "--index-url https://download.pytorch.org/whl/cu121"
                ),
                "setup_script_command": ".\\setup_gpu_windows.ps1 -Cuda cu121",
                "explicit_build_selection_needed": True,
                "pyproject_dependency_entry": "torch==2.10.0",
                "uv_add_command": "uv add 'torch==2.10.0'",
                "steps": ["step one", "step two"],
                "command_examples": ["uv add 'torch==<base-version>'", "uv lock"],
                "plan_note": "project-local only",
            }
        )
        self.assertIn("Torch pin plan:", text)
        self.assertIn("recommended_cuda_family: cu121", text)
        self.assertIn("setup_gpu_windows.ps1", text)
        self.assertIn("pytorch_index_url: https://download.pytorch.org/whl/cu121", text)
        self.assertIn("uv lock", text)
        self.assertIn("explicit_build_selection_needed: True", text)
        self.assertIn("uv_add_command: uv add 'torch==2.10.0'", text)

    def test_build_torch_pin_status_returns_expected_keys(self) -> None:
        """Torch pin status helper should include planning details."""
        status = build_torch_pin_status()
        self.assertIn("torch_direct_dependency", status)
        self.assertIn("current_torch_version", status)
        self.assertIn("current_torch_build_suffix", status)
        self.assertIn("steps", status)
        self.assertIn("command_examples", status)
        self.assertIn("uv_add_command", status)
        self.assertIn("setup_script_command", status)
        self.assertIn("uv_pip_install_command", status)
        self.assertIn("venv_doctor_command", status)
        self.assertIn("uv_run_no_sync_doctor_command", status)

    def test_get_torch_pin_plan_recommends_project_local_steps(self) -> None:
        """Torch pin plan should emphasize a project-local adjustment path."""
        plan = get_torch_pin_plan()
        self.assertIn("steps", plan)
        self.assertIn("command_examples", plan)
        self.assertIn(".venv", str(plan["plan_note"]))

    def test_get_torch_pin_plan_marks_explicit_build_selection_when_suffix_exists(self) -> None:
        """Torch pin plan should flag version-only pinning as insufficient when a local CUDA suffix exists."""
        plan = get_torch_pin_plan()
        self.assertIn("explicit_build_selection_needed", plan)

    def test_windows_helper_scripts_exist(self) -> None:
        """Windows startup and GPU helpers should be present at the repo root."""
        self.assertTrue((PROJECT_ROOT / "start_web.ps1").is_file())
        self.assertTrue((PROJECT_ROOT / "setup_gpu_windows.ps1").is_file())

    def test_windows_gpu_helper_avoids_uv_run_resync_after_torch_install(self) -> None:
        """GPU helper should verify with venv Python so uv does not restore CPU Torch."""
        script = (PROJECT_ROOT / "setup_gpu_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("$projectPython", script)
        self.assertIn("& $projectPython -c", script)
        self.assertIn("& $projectPython -m src.main --doctor", script)
        self.assertIn("setuptools>=82.0.1", script)
        self.assertNotIn("& uv run python -c", script)
        self.assertNotIn("& uv run python -m src.main --doctor", script)

    def test_windows_startup_uses_venv_python_to_preserve_gpu_torch(self) -> None:
        """Startup helper should not trigger uv sync through uv run after setup."""
        script = (PROJECT_ROOT / "start_web.ps1").read_text(encoding="utf-8")
        self.assertIn("$projectPython", script)
        self.assertIn("& $projectPython -m src.main --doctor", script)
        self.assertIn("& $projectPython -m src.web.app", script)
        self.assertNotIn("& uv run python -m src.main --doctor", script)
        self.assertNotIn("& uv run python -m src.web.app", script)

    def test_last_iteration_marks_blank_result_final(self) -> None:
        """Last mic-loop iteration should still become final."""
        result = TranscriptionResult(
            source="microphone",
            text="",
            is_final=False,
            chunk_count=3,
        )
        self.assertTrue(should_mark_result_final(result, 0, True, 3, 8))

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

    def test_format_transcription_result_marks_input_disabled(self) -> None:
        """Input-gated results should not be presented as silence."""
        result = TranscriptionResult(
            source="microphone",
            text="",
            is_final=False,
            chunk_count=0,
            input_enabled=False,
            input_gate_reason="sword_sign",
        )
        self.assertEqual(
            format_transcription_result(result),
            "[disabled] input disabled: sword_sign",
        )

    def test_parse_input_gate_payload_accepts_mic_enabled_alias(self) -> None:
        """Input-gate protocol should accept mic_enabled for integration adapters."""
        event = parse_input_gate_payload(
            {
                "type": "input_gate_state",
                "mic_enabled": True,
                "reason": "sword_sign",
                "source": "gesture_bridge",
                "timestamp": 1710000000.0,
            }
        )
        self.assertTrue(event.input_enabled)
        self.assertEqual(event.reason, "sword_sign")
        self.assertEqual(event.source, "gesture_bridge")
        self.assertEqual(event.timestamp, 1710000000.0)

    def test_parse_input_gate_payload_rejects_non_boolean_enabled_value(self) -> None:
        """Input-gate protocol should reject ambiguous string booleans."""
        with self.assertRaises(InputGateError):
            parse_input_gate_payload({"mic_enabled": "true"})

    def test_input_gate_state_formats_and_serializes(self) -> None:
        """Input-gate state should have stable text and JSON-friendly views."""
        gate = InputGate(initially_enabled=False, reason="sword_sign", source="test")
        self.assertEqual(
            format_input_gate_state(gate.state),
            "[input-gate] input_enabled=False reason=sword_sign source=test",
        )
        payload = build_input_gate_data(gate.state)
        self.assertEqual(payload["type"], "input_gate_state")
        self.assertFalse(payload["input_enabled"])

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

    def test_maybe_finalize_on_interrupt_returns_final_result(self) -> None:
        """Interrupt should flush the latest spoken result when not yet finalized."""
        last_spoken_result = TranscriptionResult(
            source="microphone",
            text="依存関係を確認して",
            is_final=False,
            chunk_count=4,
        )
        final_result = maybe_finalize_on_interrupt(
            last_spoken_result=last_spoken_result,
            finalized_text=None,
            chunk_count=5,
        )
        self.assertIsNotNone(final_result)
        assert final_result is not None
        self.assertTrue(final_result.is_final)
        self.assertEqual(final_result.chunk_count, 5)
        self.assertEqual(final_result.text, "依存関係を確認して")

    def test_maybe_finalize_on_interrupt_skips_already_finalized_text(self) -> None:
        """Interrupt should not re-emit already finalized speech."""
        last_spoken_result = TranscriptionResult(
            source="microphone",
            text="依存関係を確認して",
            is_final=False,
            chunk_count=4,
        )
        final_result = maybe_finalize_on_interrupt(
            last_spoken_result=last_spoken_result,
            finalized_text="依存関係を確認して",
            chunk_count=5,
        )
        self.assertIsNone(final_result)

    def test_mic_loop_session_tracks_repeat_state_and_finalizes(self) -> None:
        """Mic-loop session should promote repeated speech to final."""
        pipeline = mock.Mock()
        pipeline.transcribe_buffer_result.side_effect = [
            TranscriptionResult(
                source="microphone",
                text="依存関係を確認して",
                is_final=False,
                chunk_count=1,
            ),
            TranscriptionResult(
                source="microphone",
                text="依存関係を確認して",
                is_final=False,
                chunk_count=2,
            ),
        ]
        session = MicLoopSession(
            pipeline=pipeline,
            tuning=MicLoopTuning(vad_aggressiveness=2, final_stable_seconds=8),
        )
        first = session.process_chunk(
            AudioChunk(path=Path("chunk1.wav"), source="microphone"),
            has_speech=True,
            language="ja",
            chunk_duration=4,
            is_last_iteration=False,
        )
        second = session.process_chunk(
            AudioChunk(path=Path("chunk2.wav"), source="microphone"),
            has_speech=True,
            language="ja",
            chunk_duration=4,
            is_last_iteration=False,
        )
        self.assertFalse(first.is_final)
        self.assertTrue(second.is_final)
        self.assertEqual(session.state.repeat_count, 2)
        self.assertEqual(session.state.finalized_text, "依存関係を確認して")

    def test_mic_loop_session_exposes_input_gate_decision(self) -> None:
        """Mic-loop session should expose input gating without gesture details."""
        pipeline = mock.Mock()
        session = MicLoopSession(
            pipeline=pipeline,
            tuning=MicLoopTuning(vad_aggressiveness=2, final_stable_seconds=8),
            input_gate=InputGate(initially_enabled=False, reason="sword_sign"),
        )
        self.assertFalse(session.should_accept_input())
        disabled_result = session.process_input_disabled()
        self.assertFalse(disabled_result.input_enabled)
        self.assertEqual(disabled_result.input_gate_reason, "sword_sign")
        blocked_result = session.process_chunk(
            AudioChunk(path=Path("blocked.wav"), source="microphone"),
            has_speech=True,
            language="ja",
            chunk_duration=3,
            is_last_iteration=False,
        )
        self.assertFalse(blocked_result.input_enabled)
        pipeline.transcribe_buffer_result.assert_not_called()
        session.update_input_gate(
            InputGateEvent(
                input_enabled=True,
                reason="sword_sign",
                source="gesture_bridge",
            )
        )
        self.assertTrue(session.should_accept_input())
        self.assertEqual(session.input_gate_state().source, "gesture_bridge")
        pipeline.transcribe_buffer_result.return_value = TranscriptionResult(
            source="microphone",
            text="依存関係を確認して",
            is_final=False,
            chunk_count=1,
        )
        result = session.process_chunk(
            AudioChunk(path=Path("chunk1.wav"), source="microphone"),
            has_speech=True,
            language="ja",
            chunk_duration=3,
            is_last_iteration=True,
        )
        self.assertTrue(result.input_enabled)
        self.assertEqual(result.text, "依存関係を確認して")

    def test_mic_loop_session_finalize_on_interrupt_uses_internal_state(self) -> None:
        """Interrupt finalization should use the session's tracked last speech."""
        pipeline = mock.Mock()
        pipeline.transcribe_buffer_result.return_value = TranscriptionResult(
            source="microphone",
            text="依存関係を確認して",
            is_final=False,
            chunk_count=1,
        )
        session = MicLoopSession(
            pipeline=pipeline,
            tuning=MicLoopTuning(vad_aggressiveness=2, final_stable_seconds=8),
        )
        session.process_chunk(
            AudioChunk(path=Path("chunk1.wav"), source="microphone"),
            has_speech=True,
            language="ja",
            chunk_duration=3,
            is_last_iteration=False,
        )
        final_result = session.finalize_on_interrupt()
        self.assertIsNotNone(final_result)
        assert final_result is not None
        self.assertTrue(final_result.is_final)
        self.assertEqual(final_result.chunk_count, 1)

    def test_process_web_transcription_supports_command_only(self) -> None:
        """Web transcription service should hide transcript in command-only mode."""
        with mock.patch(
            "src.web.transcription_service.TranscriptionPipeline"
        ) as pipeline_cls, mock.patch(
            "src.web.transcription_service.ensure_ffmpeg_available"
        ), mock.patch(
            "src.web.transcription_service.validate_model_name"
        ), mock.patch(
            "src.web.transcription_service.validate_uploaded_audio_content",
            return_value=2.0,
        ):
            pipeline_cls.return_value.transcribe_chunk.return_value = "依存関係を確認して"
            response = process_web_transcription(
                WebTranscriptionRequest(
                    raw_bytes=b"fake-audio",
                    filename="sample.wav",
                    model_name="small",
                    language="ja",
                    command_only=True,
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.transcript, "")
        self.assertEqual(response.command, "依存関係を確認して")

    def test_process_web_transcription_can_save_handoff_paths(self) -> None:
        """Web transcription service should return saved handoff paths."""
        saved_paths = mock.Mock(
            json_path=Path("/tmp/web_latest.json"),
            text_path=Path("/tmp/web_latest.txt"),
        )
        with mock.patch(
            "src.web.transcription_service.TranscriptionPipeline"
        ) as pipeline_cls, mock.patch(
            "src.web.transcription_service.ensure_ffmpeg_available"
        ), mock.patch(
            "src.web.transcription_service.validate_model_name"
        ), mock.patch(
            "src.web.transcription_service.validate_uploaded_audio_content",
            return_value=2.0,
        ), mock.patch(
            "src.web.transcription_service.save_handoff_bundle",
            return_value=saved_paths,
        ):
            pipeline_cls.return_value.transcribe_chunk.return_value = "依存関係を確認して"
            response = process_web_transcription(
                WebTranscriptionRequest(
                    raw_bytes=b"fake-audio",
                    filename="sample.wav",
                    model_name="small",
                    save_handoff=True,
                )
            )
        self.assertEqual(response.command_path, str(saved_paths.json_path))
        self.assertEqual(response.command_text_path, str(saved_paths.text_path))

    def test_process_web_transcription_skips_short_audio_before_whisper(self) -> None:
        """Very short recordings should not be sent to Whisper."""
        with mock.patch(
            "src.web.transcription_service.TranscriptionPipeline"
        ) as pipeline_cls, mock.patch(
            "src.web.transcription_service.ensure_ffmpeg_available"
        ), mock.patch(
            "src.web.transcription_service.validate_model_name"
        ), mock.patch(
            "src.web.transcription_service.validate_uploaded_audio_content",
            return_value=0.1,
        ):
            response = process_web_transcription(
                WebTranscriptionRequest(
                    raw_bytes=b"fake-audio",
                    filename="short.wav",
                    model_name="small",
                    language="ja",
                )
            )
        pipeline_cls.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.message, "音声を認識できませんでした。")
        self.assertEqual(response.transcript, "")
        self.assertEqual(response.debug["skip_reason"], "duration_below_minimum")
        self.assertFalse(response.debug["whisper_invoked"])
        self.assertTrue(response.debug["whisper_skipped"])
        self.assertEqual(response.debug["model"], "small")
        self.assertEqual(response.debug["language"], "ja")

    def test_process_web_transcription_skips_vad_no_speech_before_whisper(self) -> None:
        """Recordings with no VAD-detectable speech should not be sent to Whisper."""
        with mock.patch(
            "src.web.transcription_service.TranscriptionPipeline"
        ) as pipeline_cls, mock.patch(
            "src.web.transcription_service.ensure_ffmpeg_available"
        ), mock.patch(
            "src.web.transcription_service.validate_model_name"
        ), mock.patch(
            "src.web.transcription_service.validate_uploaded_audio_content",
            return_value=2.0,
        ), mock.patch(
            "src.web.transcription_service.has_detectable_speech",
            return_value=False,
        ):
            response = process_web_transcription(
                WebTranscriptionRequest(
                    raw_bytes=b"fake-audio",
                    filename="silent.wav",
                    model_name="small",
                    language="ja",
                )
            )
        pipeline_cls.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.message, "音声を認識できませんでした。")
        self.assertEqual(response.debug["skip_reason"], "vad_no_speech")
        self.assertEqual(response.debug["vad"]["reason"], "no_speech_detected")
        self.assertFalse(response.debug["whisper_invoked"])

    def test_process_web_transcription_records_webm_normalization_debug(self) -> None:
        """WebM recordings should expose normalized file facts in debug output."""
        def fake_normalize(input_path: Path, output_path: Path, timeout_seconds: int) -> Path:
            output_path.write_bytes(b"fake-normalized-wav")
            return output_path

        with mock.patch(
            "src.web.transcription_service.TranscriptionPipeline"
        ) as pipeline_cls, mock.patch(
            "src.web.transcription_service.ensure_ffmpeg_available"
        ), mock.patch(
            "src.web.transcription_service.validate_model_name"
        ), mock.patch(
            "src.web.transcription_service.validate_uploaded_audio_content",
            return_value=2.0,
        ), mock.patch(
            "src.web.transcription_service.normalize_audio_for_transcription",
            side_effect=fake_normalize,
        ), mock.patch(
            "src.web.transcription_service.probe_audio_duration",
            return_value=1.9,
        ), mock.patch(
            "src.web.transcription_service.has_detectable_speech",
            return_value=False,
        ):
            response = process_web_transcription(
                WebTranscriptionRequest(
                    raw_bytes=b"fake-webm",
                    filename="browser_recording.webm",
                    model_name="small",
                    language="ja",
                )
            )
        pipeline_cls.assert_not_called()
        self.assertTrue(response.debug["webm_normalized"])
        self.assertEqual(response.debug["normalized_audio"]["suffix"], ".wav")
        self.assertGreater(response.debug["normalized_audio"]["size_bytes"], 0)
        self.assertEqual(response.debug["normalized_audio"]["duration_seconds"], 1.9)
        self.assertEqual(response.debug["skip_reason"], "vad_no_speech")

    def test_process_web_transcription_rejects_unsupported_extension(self) -> None:
        """Web transcription service should reject non-audio upload extensions."""
        response = process_web_transcription(
            WebTranscriptionRequest(
                raw_bytes=b"fake-audio",
                filename="notes.txt",
                model_name="small",
            )
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("ファイル形式", response.error)

    def test_process_web_transcription_hides_environment_details(self) -> None:
        """Web transcription errors should not expose internal exception details."""
        with mock.patch(
            "src.web.transcription_service.validate_model_name"
        ), mock.patch(
            "src.web.transcription_service.ensure_ffmpeg_available",
            side_effect=AudioEnvironmentError(r"secret path C:\internal\ffmpeg"),
        ), mock.patch(
            "src.web.transcription_service.LOGGER.exception"
        ):
            response = process_web_transcription(
                WebTranscriptionRequest(
                    raw_bytes=b"fake-audio",
                    filename="sample.wav",
                    model_name="small",
                )
            )
        self.assertEqual(response.status_code, 500)
        self.assertIn("サーバー側", response.error)
        self.assertNotIn("secret path", response.error)
        self.assertNotIn("C:\\internal", response.error)

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

    def test_resolve_runner_command_prefers_template(self) -> None:
        """Runner command resolution should prefer templates when requested."""
        self.assertEqual(
            resolve_runner_command(
                "cat",
                ["--", "python", "-c", "print('ignored')"],
                PROJECT_ROOT,
            ),
            build_template_command("cat", PROJECT_ROOT),
        )

    def test_build_template_command_supports_codex_exec(self) -> None:
        """Runner templates should include a Codex exec bridge."""
        self.assertEqual(
            build_template_command("codex-exec", PROJECT_ROOT),
            ["codex", "exec", "-C", str(PROJECT_ROOT), "-"],
        )

    def test_drivers_package_exports_public_contract(self) -> None:
        """Drivers package should expose the public driver contract surface."""
        response = DriverResponse(
            backend_name="agent",
            command_name="codex",
            command_line="codex exec -",
            returncode=0,
            status="ok",
            succeeded=True,
            has_output=True,
            stdout_text="ok\n",
            stderr_text="",
            stream="stdout",
            text="ok\n",
        )

        self.assertEqual(response.command_name, "codex")
        self.assertEqual(response.status, "ok")

    def test_validate_runner_command_available_accepts_existing_path_command(self) -> None:
        """Absolute path commands should pass when they exist."""
        validate_runner_command_available([sys.executable, "--version"])

    def test_validate_runner_command_available_rejects_missing_path_command(self) -> None:
        """Missing absolute path commands should fail early."""
        with self.assertRaisesRegex(AudioInputError, "runner command not found"):
            validate_runner_command_available([str(PROJECT_ROOT / "missing-command")])

    def test_validate_runner_command_available_rejects_missing_path_entry(self) -> None:
        """PATH lookups should fail early for missing commands."""
        with mock.patch("src.drivers.base.shutil.which", return_value=None):
            with self.assertRaisesRegex(AudioInputError, "runner command not found in PATH: codex"):
                validate_runner_command_available(["codex", "exec"])

    def test_dispatch_driver_request_returns_normalized_result(self) -> None:
        """Driver dispatch should return backend metadata and subprocess output."""
        with mock.patch(
            "src.drivers.base.validate_driver_command_available"
        ), mock.patch(
            "src.drivers.base.subprocess.run"
        ) as subprocess_run:
            subprocess_run.return_value = subprocess.CompletedProcess(
                args=["cat"],
                returncode=0,
                stdout="ok\n",
                stderr="",
            )
            result = dispatch_driver_request(
                DriverRequest(
                    backend_name="agent",
                    command=["cat"],
                    payload="hello",
                )
            )
        self.assertEqual(result.backend_name, "agent")
        self.assertEqual(result.command, ["cat"])
        self.assertEqual(result.payload, "hello")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "ok\n")

    def test_dispatch_driver_request_wraps_missing_command(self) -> None:
        """Driver dispatch should surface missing commands as input errors."""
        with mock.patch(
            "src.drivers.base.validate_driver_command_available"
        ), mock.patch(
            "src.drivers.base.subprocess.run",
            side_effect=FileNotFoundError(2, "No such file or directory", "codex"),
        ):
            with self.assertRaisesRegex(AudioInputError, "runner command not found: codex"):
                dispatch_driver_request(
                    DriverRequest(
                        backend_name="agent",
                        command=["codex", "exec"],
                        payload="hello",
                    )
                )

    def test_dispatch_driver_request_returns_timeout_result(self) -> None:
        """Driver dispatch should bound external runner execution time."""
        with mock.patch(
            "src.drivers.base.validate_driver_command_available"
        ), mock.patch(
            "src.drivers.base.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["codex", "exec"], timeout=1),
        ):
            result = dispatch_driver_request(
                DriverRequest(
                    backend_name="agent",
                    command=["codex", "exec"],
                    payload="hello",
                    timeout_seconds=1,
                )
            )
        self.assertEqual(result.returncode, 124)
        self.assertIn("timed out", result.stderr)

    def test_driver_result_response_returns_backend_neutral_view(self) -> None:
        """Driver results should expose a backend-neutral response view."""
        result = DriverResult(
            backend_name="agent",
            command=["codex", "exec", "-"],
            payload="hello",
            returncode=0,
            stdout="ok\n",
            stderr="warn\n",
            command_name="codex",
        )

        response = result.response
        self.assertEqual(response.backend_name, "agent")
        self.assertEqual(response.command_name, "codex")
        self.assertEqual(response.command_line, "codex exec -")
        quoted = DriverResult(
            backend_name="agent",
            command=["python", "-c", "print('hello world')"],
            payload="",
            returncode=0,
            stdout="",
            stderr="",
            command_name="python",
        )
        self.assertEqual(quoted.command_line, shlex.join(quoted.command))
        self.assertEqual(response.returncode, 0)
        self.assertEqual(response.status, "ok")
        self.assertTrue(response.succeeded)
        self.assertTrue(response.has_output)
        self.assertEqual(response.stdout_text, "ok\n")
        self.assertEqual(response.stderr_text, "warn\n")
        self.assertEqual(response.stream, "stdout")
        self.assertEqual(response.text, "ok\n")

    def test_driver_result_status_distinguishes_output_cases(self) -> None:
        """Driver status labels should distinguish output/no-output success and failure."""
        success_no_output = DriverResult(
            backend_name="agent",
            command=["true"],
            payload="",
            returncode=0,
            stdout="",
            stderr="",
            command_name="true",
        )
        failure_no_output = DriverResult(
            backend_name="agent",
            command=["false"],
            payload="",
            returncode=1,
            stdout="",
            stderr="",
            command_name="false",
        )

        self.assertEqual(success_no_output.status, "ok_no_output")
        self.assertEqual(success_no_output.response.status, "ok_no_output")
        self.assertEqual(failure_no_output.status, "error_no_output")
        self.assertEqual(failure_no_output.response.status, "error_no_output")

    def test_execute_runner_command_dispatches_normalized_request(self) -> None:
        """Runner helpers should build driver requests consistently."""
        expected = DriverResult(
            backend_name="agent",
            command=["cat"],
            payload="hello",
            returncode=0,
            stdout="ok\n",
            stderr="",
            command_name="cat",
        )
        with mock.patch("src.runners.common.dispatch_driver_request", return_value=expected) as dispatch:
            result = execute_runner_command("agent", ["cat"], "hello")

        dispatch.assert_called_once()
        request = dispatch.call_args.args[0]
        self.assertEqual(request.backend_name, "agent")
        self.assertEqual(request.command, ["cat"])
        self.assertEqual(request.payload, "hello")
        self.assertIs(result, expected)

    def test_emit_driver_result_uses_response_stream(self) -> None:
        """Runner output emission should respect the normalized response stream."""
        result = DriverResult(
            backend_name="ollama",
            command=["ollama", "run", "llama3"],
            payload="hello",
            returncode=1,
            stdout="partial\n",
            stderr="failed\n",
            command_name="ollama",
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = emit_driver_result(result)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "partial\n")
        self.assertEqual(stderr.getvalue(), "failed\n")

    def test_build_ollama_command_normalizes_model_name(self) -> None:
        """Ollama runner should trim the model name."""
        self.assertEqual(build_ollama_command(" llama3 "), ["ollama", "run", "llama3"])

    def test_build_ollama_command_rejects_blank_model_name(self) -> None:
        """Ollama runner should reject blank model names."""
        with self.assertRaisesRegex(AudioInputError, "Ollama model name must not be blank"):
            build_ollama_command("   ")

    def test_retry_model_load_on_cpu_matches_busy_cuda_error(self) -> None:
        """CUDA busy errors should trigger a CPU retry."""
        exc = RuntimeError("CUDA error: CUDA-capable device(s) is/are busy or unavailable")
        self.assertTrue(should_retry_model_load_on_cpu(exc))

    def test_retry_model_load_on_cpu_ignores_unrelated_errors(self) -> None:
        """Non-CUDA model load errors should not trigger a CPU retry."""
        exc = RuntimeError("unknown Whisper load failure")
        self.assertFalse(should_retry_model_load_on_cpu(exc))

    def test_print_agent_instruction_only_handles_blank(self) -> None:
        """command-only printer should handle blank transcripts."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            print_agent_instruction_only("   ")
        self.assertEqual(buffer.getvalue().strip(), "no instruction draft available")

    def test_print_runtime_note_writes_to_stderr(self) -> None:
        """Operational notes should go to stderr."""
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            print_runtime_note("[mic-tuning] profile=balanced")
        self.assertEqual(buffer.getvalue().strip(), "[mic-tuning] profile=balanced")


if __name__ == "__main__":
    unittest.main()
