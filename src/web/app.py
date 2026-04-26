"""Local web UI for audio transcription."""

from __future__ import annotations

from flask import Flask, Response, jsonify, render_template, request

from src.core.status_report import build_doctor_status
from src.core.handoff_bridge import load_handoff_bundle
from src.web.transcription_service import WebTranscriptionRequest, process_web_transcription


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="8" fill="#0f766e"/>
<path d="M9 20.5h14v3H9zM11 8.5h10a4 4 0 0 1 0 8H11z" fill="#f8fafc"/>
<circle cx="21" cy="12.5" r="1.6" fill="#0f766e"/>
</svg>"""


def create_app() -> Flask:
    """Create the local Flask application."""
    app = Flask(__name__)

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
            return jsonify({"message": "", "transcript": "", "error": "音声ファイルを選択してください。"}), 400
        return handle_transcription_api(file_storage.read(), file_storage.filename)

    @app.post("/transcribe-browser-recording")
    def transcribe_browser_recording() -> str | Response:
        file_storage = request.files.get("audio_blob")
        if file_storage is None or file_storage.filename == "":
            return render_page(error="録音データを受け取れませんでした。")
        return handle_transcription(file_storage.read(), file_storage.filename, message="ブラウザ録音を処理しました。")

    @app.post("/api/transcribe-browser-recording")
    def api_transcribe_browser_recording() -> tuple[object, int]:
        file_storage = request.files.get("audio_blob")
        if file_storage is None or file_storage.filename == "":
            return jsonify({"message": "", "transcript": "", "error": "録音データを受け取れませんでした。"}), 400
        return handle_transcription_api(
            file_storage.read(),
            file_storage.filename,
            message="ブラウザ録音を処理しました。",
        )

    def build_handoff_response() -> tuple[object, int]:
        """Return the latest saved handoff bundle as JSON."""
        source = request.args.get("source", "web").strip() or "web"
        handoff = load_handoff_bundle(source=source)
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

    return app


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
    )


def process_transcription_request(
    raw_bytes: bytes,
    filename: str,
    message: str | None = None,
) -> tuple[dict[str, str], int]:
    """Run one transcription request and normalize the response payload."""
    def read_bool_flag(*names: str) -> bool:
        for name in names:
            value = request.form.get(name, "").strip().lower()
            if value in {"1", "true", "yes", "on"}:
                return True
        return False

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


def main() -> int:
    """Run the local Flask development server."""
    app = create_app()
    app.run(host="127.0.0.1", port=8000, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
