"""Local web UI for audio transcription."""

from __future__ import annotations

import _thread
import hmac
import os
import secrets
import shutil
import threading
from urllib.parse import urlsplit

from flask import (
    Flask,
    Response,
    current_app,
    has_app_context,
    jsonify,
    render_template,
    request,
)
from werkzeug.exceptions import RequestEntityTooLarge

from src.core.input_gate import InputGate, InputGateError, InputGateState
from src.core.status_report import build_doctor_status
from src.core.handoff_bridge import build_handoff_metadata, load_handoff_bundle
from src.web.transcription_service import (
    WEB_MAX_UPLOAD_BYTES,
    WebTranscriptionRequest,
    process_web_transcription,
)


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="8" fill="#0f766e"/>
<path d="M9 20.5h14v3H9zM11 8.5h10a4 4 0 0 1 0 8H11z" fill="#f8fafc"/>
<circle cx="21" cy="12.5" r="1.6" fill="#0f766e"/>
</svg>"""
LOCAL_API_TOKEN_HEADER = "X-AI-Core-Token"
LOCAL_API_TOKEN_CONFIG = "LOCAL_API_TOKEN"
ENABLE_PROCESS_SHUTDOWN_CONFIG = "ENABLE_PROCESS_SHUTDOWN"
WEB_PRESET_CONFIG = "WEB_PRESET"
WEB_PRESET_ENV = "AI_TALK_CORE_WEB_PRESET"
WEB_RUNTIME_STATE_CONFIG = "WEB_RUNTIME_STATE"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TOKEN_PROTECTED_ENDPOINTS = {
    "api_agent_handoff_latest",
    "api_codex_handoff_latest",
    "api_shutdown",
}


class WebRuntimeState:
    """Track in-flight Web transcription work and shutdown requests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_transcriptions = 0
        self._shutdown_requested = False
        self._shutdown_reason = ""
        self._shutdown_scheduled = False

    def begin_transcription(self) -> bool:
        """Reserve one transcription slot unless shutdown has started."""
        with self._lock:
            if self._shutdown_requested:
                return False
            self._active_transcriptions += 1
            return True

    def end_transcription(self) -> bool:
        """Release one transcription slot and report whether shutdown can run."""
        with self._lock:
            if self._active_transcriptions > 0:
                self._active_transcriptions -= 1
            return (
                self._shutdown_requested
                and self._active_transcriptions == 0
                and not self._shutdown_scheduled
            )

    def request_shutdown(
        self,
        reason: str = "",
        *,
        force: bool = False,
    ) -> tuple[dict[str, object], bool]:
        """Request shutdown and return a state snapshot plus scheduling decision."""
        with self._lock:
            self._shutdown_requested = True
            self._shutdown_reason = (reason or "api_request").strip() or "api_request"
            should_schedule = (
                force or self._active_transcriptions == 0
            ) and not self._shutdown_scheduled
            return self._snapshot_unlocked(), should_schedule

    def mark_shutdown_scheduled(self) -> dict[str, object]:
        """Mark that the process shutdown timer has been scheduled."""
        with self._lock:
            self._shutdown_scheduled = True
            return self._snapshot_unlocked()

    def snapshot(self) -> dict[str, object]:
        """Return a thread-safe runtime state snapshot."""
        with self._lock:
            return self._snapshot_unlocked()

    def _snapshot_unlocked(self) -> dict[str, object]:
        return {
            "active_transcriptions": self._active_transcriptions,
            "shutdown_requested": self._shutdown_requested,
            "shutdown_reason": self._shutdown_reason,
            "shutdown_scheduled": self._shutdown_scheduled,
        }


def create_app() -> Flask:
    """Create the local Flask application."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = WEB_MAX_UPLOAD_BYTES
    app.config[LOCAL_API_TOKEN_CONFIG] = secrets.token_urlsafe(32)
    app.config[ENABLE_PROCESS_SHUTDOWN_CONFIG] = True
    app.config[WEB_PRESET_CONFIG] = os.environ.get(WEB_PRESET_ENV, "").strip()
    app.config[WEB_RUNTIME_STATE_CONFIG] = WebRuntimeState()
    input_gate = InputGate()

    @app.before_request
    def enforce_local_request_policy() -> tuple[object, int] | None:
        if not is_allowed_local_host(request.host):
            return build_error_response("このローカル UI では許可されていない Host です。", 403)
        if request.method in UNSAFE_METHODS and not has_trusted_origin():
            return build_error_response("このローカル UI では許可されていない送信元です。", 403)
        if (
            request.endpoint in TOKEN_PROTECTED_ENDPOINTS
            and not has_valid_local_api_token()
        ):
            return build_error_response("local API token が不正です。", 403)
        return None

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(_: RequestEntityTooLarge) -> tuple[object, int]:
        return build_error_response(
            "音声ファイルが大きすぎます。25MB 以下のファイルを指定してください。",
            413,
        )

    @app.get("/")
    def index() -> str:
        return render_page()

    @app.get("/favicon.ico")
    def favicon() -> Response:
        return Response(FAVICON_SVG, mimetype="image/svg+xml")

    @app.post("/transcribe-upload")
    def transcribe_upload() -> str | Response:
        file_storage = request.files.get("audio_file")
        if file_storage is None or file_storage.filename == "":
            return render_page(error="音声ファイルを選択してください。")
        return handle_transcription(file_storage.read(), file_storage.filename)

    @app.post("/api/transcribe-upload")
    def api_transcribe_upload() -> tuple[object, int]:
        file_storage = request.files.get("audio_file")
        if file_storage is None or file_storage.filename == "":
            return jsonify(
                {
                    "message": "",
                    "transcript": "",
                    "error": "音声ファイルを選択してください。",
                }
            ), 400
        return handle_transcription_api(file_storage.read(), file_storage.filename)

    @app.post("/transcribe-browser-recording")
    def transcribe_browser_recording() -> str | Response:
        file_storage = request.files.get("audio_blob")
        if file_storage is None or file_storage.filename == "":
            return render_page(error="録音データを受け取れませんでした。")
        return handle_transcription(
            file_storage.read(),
            file_storage.filename,
            message="ブラウザ録音を処理しました。",
        )

    @app.post("/api/transcribe-browser-recording")
    def api_transcribe_browser_recording() -> tuple[object, int]:
        file_storage = request.files.get("audio_blob")
        if file_storage is None or file_storage.filename == "":
            return jsonify(
                {
                    "message": "",
                    "transcript": "",
                    "error": "録音データを受け取れませんでした。",
                }
            ), 400
        return handle_transcription_api(
            file_storage.read(),
            file_storage.filename,
            message="ブラウザ録音を処理しました。",
        )

    def build_handoff_response() -> tuple[object, int]:
        """Return the latest saved handoff bundle as JSON."""
        source = request.args.get("source", "web").strip() or "web"
        try:
            handoff = load_handoff_bundle(source=source)
        except ValueError:
            return jsonify({"error": "invalid handoff source"}), 400
        if handoff is None:
            return jsonify({"error": f"handoff not found for source: {source}"}), 404
        return jsonify(
            {
                "transcript": handoff.transcript,
                "command": handoff.command,
                "prompt_text": handoff.prompt_text,
                "command_path": str(handoff.json_path),
                "command_text_path": str(handoff.text_path),
                "source": source,
                "handoff_id": handoff.metadata.get("handoff_id", ""),
                "updated_at": handoff.metadata.get("updated_at", ""),
                "metadata": handoff.metadata,
            }
        ), 200

    @app.get("/api/codex-handoff-latest")
    def api_codex_handoff_latest() -> tuple[object, int]:
        return build_handoff_response()

    @app.get("/api/agent-handoff-latest")
    def api_agent_handoff_latest() -> tuple[object, int]:
        return build_handoff_response()

    @app.get("/api/doctor")
    def api_doctor() -> tuple[object, int]:
        return jsonify(build_doctor_status()), 200

    @app.get("/api/input-gate")
    def api_input_gate_get() -> tuple[object, int]:
        return jsonify(build_input_gate_response(input_gate.state)), 200

    @app.post("/api/input-gate")
    def api_input_gate_post() -> tuple[object, int]:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "error": "request body must be a JSON object"}), 400
        try:
            state = input_gate.update_from_payload(payload)
        except InputGateError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify(build_input_gate_response(state)), 200

    @app.get("/api/health")
    def api_health() -> tuple[object, int]:
        return jsonify(
            build_health_response(
                input_gate_state=input_gate.state,
                runtime_state=get_web_runtime_state(),
                source=request.args.get("source", "web"),
            )
        ), 200

    @app.get("/api/status")
    def api_status() -> tuple[object, int]:
        return api_health()

    @app.post("/api/shutdown")
    def api_shutdown() -> tuple[object, int]:
        runtime_state = get_web_runtime_state()
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            payload = {}
        reason = str(
            payload.get("reason") or request.args.get("reason") or "api_request"
        )
        force_value = (
            payload["force"] if "force" in payload else request.args.get("force")
        )
        force = parse_boolish(force_value) is True
        shutdown_state, should_schedule = runtime_state.request_shutdown(
            reason=reason,
            force=force,
        )
        if should_schedule and current_app.config.get(
            ENABLE_PROCESS_SHUTDOWN_CONFIG,
            True,
        ):
            shutdown_state = runtime_state.mark_shutdown_scheduled()
            schedule_server_shutdown(request.environ.get("werkzeug.server.shutdown"))
        return jsonify(
            {
                "ok": True,
                "shutdown": shutdown_state,
                "message": (
                    "shutdown scheduled"
                    if shutdown_state["shutdown_scheduled"]
                    else "shutdown requested"
                ),
            }
        ), 202

    return app


def build_error_response(message: str, status_code: int) -> tuple[object, int]:
    """Return a local-policy error in the response shape expected by the caller."""
    if wants_json_response():
        return jsonify({"message": "", "transcript": "", "error": message}), status_code
    return render_page(error=message), status_code


def wants_json_response() -> bool:
    """Return whether the current request expects a JSON-style API response."""
    return (
        request.path.startswith("/api/")
        or request.headers.get("X-Requested-With") == "fetch"
    )


def get_local_api_token() -> str:
    """Return the per-process token used by the local Web UI."""
    if not has_app_context():
        return ""
    return str(current_app.config.get(LOCAL_API_TOKEN_CONFIG, ""))


def get_web_preset() -> str:
    """Return the configured Web UI startup preset name."""
    if has_app_context():
        return str(current_app.config.get(WEB_PRESET_CONFIG, "")).strip()
    return os.environ.get(WEB_PRESET_ENV, "").strip()


def get_web_runtime_state() -> WebRuntimeState:
    """Return the per-process Web runtime state."""
    state = current_app.config.get(WEB_RUNTIME_STATE_CONFIG)
    if not isinstance(state, WebRuntimeState):
        state = WebRuntimeState()
        current_app.config[WEB_RUNTIME_STATE_CONFIG] = state
    return state


def has_valid_local_api_token() -> bool:
    """Return whether the request carries the per-process local API token."""
    expected = get_local_api_token()
    provided = (
        request.headers.get(LOCAL_API_TOKEN_HEADER, "")
        or request.args.get("api_token", "")
    )
    return bool(expected and provided and hmac.compare_digest(provided, expected))


def is_allowed_local_host(host_header: str) -> bool:
    """Return whether the Host header targets a loopback browser origin."""
    hostname = parse_hostname(host_header)
    return hostname in LOCAL_HOSTS


def has_trusted_origin() -> bool:
    """Validate Origin/Referer when a browser sends one for a local request."""
    origin = request.headers.get("Origin")
    if origin:
        return origin_matches_request(origin)
    referer = request.headers.get("Referer")
    if referer:
        return origin_matches_request(referer)
    return True


def origin_matches_request(origin: str) -> bool:
    """Return whether an Origin/Referer value matches the current local origin."""
    parsed_origin = urlsplit(origin)
    parsed_request = urlsplit(request.host_url)
    return (
        parsed_origin.scheme == parsed_request.scheme
        and parsed_origin.hostname == parsed_request.hostname
        and parsed_origin.hostname in LOCAL_HOSTS
        and parsed_origin.port == parsed_request.port
    )


def parse_hostname(host_value: str) -> str:
    """Parse a Host or Origin host component into a lowercase hostname."""
    try:
        return (urlsplit(f"//{host_value}").hostname or "").lower()
    except ValueError:
        return ""


def build_input_gate_response(state: InputGateState) -> dict[str, object]:
    return {
        "ok": True,
        "input_gate": state.to_payload(),
    }


def build_health_response(
    input_gate_state: InputGateState,
    runtime_state: WebRuntimeState,
    source: str = "web",
) -> dict[str, object]:
    """Return a generic status payload for integration supervisors."""
    safe_source = (source or "web").strip() or "web"
    ffmpeg_available = shutil.which("ffmpeg") is not None
    ffprobe_available = shutil.which("ffprobe") is not None
    runtime = runtime_state.snapshot()
    try:
        latest_handoff = build_handoff_metadata(source=safe_source)
    except ValueError:
        latest_handoff = {
            "source": safe_source,
            "exists": False,
            "error": "invalid handoff source",
        }
    return {
        "ok": True,
        "ready": not runtime["shutdown_requested"],
        "server": runtime,
        "stt": {
            "ready": ffmpeg_available and ffprobe_available,
            "ffmpeg_available": ffmpeg_available,
            "ffprobe_available": ffprobe_available,
        },
        "recording": {
            "ready": ffmpeg_available,
            "max_upload_bytes": WEB_MAX_UPLOAD_BYTES,
        },
        "input_gate": input_gate_state.to_payload(),
        "latest_handoff": latest_handoff,
        "web_preset": get_web_preset(),
    }


def render_page(
    transcript: str | None = None,
    command: str | None = None,
    command_path: str | None = None,
    command_text_path: str | None = None,
    error: str | None = None,
    message: str | None = None,
) -> str:
    """Render the single-page web UI."""
    return render_template(
        "index.html",
        transcript=transcript,
        command=command,
        command_path=command_path,
        command_text_path=command_text_path,
        error=error,
        message=message,
        api_token=get_local_api_token(),
        web_preset=get_web_preset(),
    )


def process_transcription_request(
    raw_bytes: bytes,
    filename: str,
    message: str | None = None,
) -> tuple[dict[str, object], int]:
    """Run one transcription request and normalize the response payload."""
    runtime_state = get_web_runtime_state()
    if not runtime_state.begin_transcription():
        return {
            "message": "",
            "transcript": "",
            "command": "",
            "command_path": "",
            "command_text_path": "",
            "error": "シャットダウン要求中のため新しい文字起こしは受け付けません。",
            "debug": {
                "server": runtime_state.snapshot(),
                "whisper_invoked": False,
                "whisper_skipped": True,
                "skip_reason": "shutdown_requested",
            },
        }, 503

    def read_bool_flag(*names: str) -> bool:
        for name in names:
            value = request.form.get(name, "").strip().lower()
            if value in {"1", "true", "yes", "on"}:
                return True
        return False

    try:
        response = process_web_transcription(
            WebTranscriptionRequest(
                raw_bytes=raw_bytes,
                filename=filename,
                model_name=request.form.get("model", "small").strip() or "small",
                language=request.form.get("language", "").strip() or None,
                command_only=read_bool_flag("instruction_only", "command_only"),
                save_handoff=read_bool_flag("save_handoff", "save_command"),
                source="web",
                success_message=message,
            )
        )
        return response.to_payload(), response.status_code
    finally:
        should_shutdown = runtime_state.end_transcription()
        if should_shutdown and current_app.config.get(
            ENABLE_PROCESS_SHUTDOWN_CONFIG,
            True,
        ):
            runtime_state.mark_shutdown_scheduled()
            schedule_server_shutdown(request.environ.get("werkzeug.server.shutdown"))


def handle_transcription(
    raw_bytes: bytes,
    filename: str,
    message: str | None = None,
) -> str | Response:
    """Persist uploaded audio temporarily and transcribe it."""
    payload, status_code = process_transcription_request(
        raw_bytes,
        filename,
        message=message,
    )
    if request.headers.get("X-Requested-With") == "fetch":
        response = jsonify(payload)
        response.status_code = status_code
        return response
    if payload["error"]:
        return render_page(error=payload["error"])
    return render_page(
        transcript=payload["transcript"],
        command=payload["command"],
        command_path=payload["command_path"],
        command_text_path=payload["command_text_path"],
        message=payload["message"],
    )


def handle_transcription_api(
    raw_bytes: bytes,
    filename: str,
    message: str | None = None,
) -> tuple[object, int]:
    """Handle uploaded audio and return a dedicated JSON API response."""
    payload, status_code = process_transcription_request(
        raw_bytes,
        filename,
        message=message,
    )
    return jsonify(payload), status_code


def parse_boolish(value: object) -> bool | None:
    """Parse common bool-like request values."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def schedule_server_shutdown(werkzeug_shutdown: object | None = None) -> None:
    """Schedule local development server shutdown outside the request thread."""
    def shutdown() -> None:
        if callable(werkzeug_shutdown):
            werkzeug_shutdown()
            return
        _thread.interrupt_main()

    timer = threading.Timer(0.2, shutdown)
    timer.daemon = True
    timer.start()


def main() -> int:
    """Run the local Flask development server."""
    app = create_app()
    try:
        app.run(host="127.0.0.1", port=8000, debug=False)
    finally:
        print("ai_core Web UI stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
