"""Local web UI for audio transcription."""

from __future__ import annotations

from html import escape
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template_string, request
from werkzeug.utils import secure_filename

from src.core.handoff_bridge import (
    build_handoff_payload,
    get_default_handoff_output_path,
    get_default_handoff_text_path,
    load_handoff_bundle,
    save_handoff_bundle,
)
from src.core.pipeline import AudioChunk, TranscriptionPipeline
from src.io.audio import (
    AudioEnvironmentError,
    AudioInputError,
    AudioTranscriptionError,
    ensure_ffmpeg_available,
    normalize_audio_for_transcription,
    validate_model_name,
)


PAGE_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ai_core Web UI</title>
  <style>
    :root {
      --bg: #f5f1e8;
      --panel: #fffdf8;
      --line: #d8ccb6;
      --text: #1f1a14;
      --muted: #6d6257;
      --accent: #9f4d2f;
      --accent-2: #204b57;
    }
    body {
      margin: 0;
      font-family: "Noto Sans JP", "Hiragino Sans", sans-serif;
      background:
        radial-gradient(circle at top left, #fff7df 0%, transparent 32%),
        radial-gradient(circle at bottom right, #d9efe7 0%, transparent 28%),
        var(--bg);
      color: var(--text);
    }
    main {
      max-width: 960px;
      margin: 0 auto;
      padding: 40px 20px 64px;
    }
    h1 {
      margin: 0 0 12px;
      font-size: clamp(2rem, 4vw, 3rem);
    }
    p.lead {
      margin: 0 0 24px;
      color: var(--muted);
      max-width: 60ch;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 14px 40px rgba(36, 22, 10, 0.08);
    }
    .panel h2 {
      margin-top: 0;
      font-size: 1.2rem;
    }
    label {
      display: block;
      font-size: 0.92rem;
      margin: 14px 0 6px;
      color: var(--muted);
    }
    input[type="file"], input[type="text"], select {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      background: #fff;
      font: inherit;
    }
    button {
      margin-top: 16px;
      border: none;
      border-radius: 999px;
      padding: 12px 18px;
      font: inherit;
      cursor: pointer;
      background: var(--accent);
      color: #fff;
    }
    button.secondary {
      background: var(--accent-2);
    }
    button.ghost {
      background: #efe5d6;
      color: var(--text);
    }
    .status, .result, .error, .command, .meta {
      margin-top: 20px;
      padding: 16px;
      border-radius: 14px;
      white-space: pre-wrap;
    }
    .status[hidden], .result[hidden], .error[hidden], .command[hidden], .meta[hidden] {
      display: none;
    }
    .status {
      background: #eef5f5;
      border: 1px solid #bfd5d6;
    }
    .result {
      background: #fff6e6;
      border: 1px solid #e8c88c;
    }
    .error {
      background: #fff0ef;
      border: 1px solid #e8b2ad;
      color: #7d2314;
    }
    .command {
      background: #eef0ff;
      border: 1px solid #b8c1f1;
    }
    .meta {
      background: #f7f4ee;
      border: 1px solid #d9d0c0;
      color: var(--muted);
    }
    .row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    .hint {
      color: var(--muted);
      font-size: 0.9rem;
      margin-top: 8px;
    }
    .checkbox {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .checkbox input {
      width: auto;
      margin: 0;
    }
    .debug {
      margin-top: 16px;
      padding: 14px;
      border-radius: 14px;
      border: 1px dashed var(--line);
      background: #faf6ee;
      font-size: 0.88rem;
    }
    .debug strong {
      display: block;
      margin-bottom: 8px;
    }
    .debug pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--muted);
    }
  </style>
</head>
<body>
  <main>
    <h1>ai_core Web UI</h1>
    <p class="lead">ローカル音声ファイルのアップロード、またはブラウザのマイク録音から、Whisper で文字起こしします。</p>

    <div class="grid">
      <section class="panel">
        <h2>ファイルアップロード</h2>
        <form id="upload-form" action="{{ url_for('transcribe_upload') }}" method="post" enctype="multipart/form-data">
          <label for="audio_file">音声ファイル</label>
          <input id="audio_file" name="audio_file" type="file" accept=".mp3,.wav,.m4a,.mp4,.mpeg,.mpga,.webm" required>

          <label for="upload_model">モデル</label>
          <select id="upload_model" name="model">
            <option value="small">small</option>
            <option value="base">base</option>
            <option value="medium">medium</option>
          </select>

          <label for="upload_language">言語コード</label>
          <input id="upload_language" name="language" type="text" value="ja" placeholder="ja">

          <label class="checkbox" for="upload_command_only">
            <input id="upload_command_only" name="command_only" type="checkbox" value="true">
            指示草案を優先して返す
          </label>

          <label class="checkbox" for="upload_save_command">
            <input id="upload_save_command" name="save_command" type="checkbox" value="true">
            handoff payload を保存する
          </label>

          <button type="submit">文字起こしする</button>
        </form>
      </section>

      <section class="panel">
        <h2>ブラウザ録音</h2>
        <div class="row">
          <button id="start-record" class="secondary" type="button">録音開始</button>
          <button id="stop-record" class="ghost" type="button" disabled>録音停止</button>
        </div>

        <label for="record_model">モデル</label>
        <select id="record_model">
          <option value="small">small</option>
          <option value="base">base</option>
          <option value="medium">medium</option>
        </select>

        <label for="record_language">言語コード</label>
        <input id="record_language" type="text" value="ja" placeholder="ja">

        <label class="checkbox" for="record_command_only">
          <input id="record_command_only" type="checkbox" value="true">
          指示草案を優先して返す
        </label>

        <label class="checkbox" for="record_save_command">
          <input id="record_save_command" type="checkbox" value="true">
          handoff payload を保存する
        </label>

        <p class="hint">ブラウザ側でマイク許可が必要です。録音停止後に自動でアップロードします。</p>
        <div id="record-status" class="status" hidden></div>
        <div class="debug">
          <strong>Recorder Debug</strong>
          <pre id="record-debug">state=idle</pre>
        </div>
      </section>
    </div>

    <div id="page-status" class="status" {% if not message %}hidden{% endif %}>{{ message or "" }}</div>
    <div id="page-result" class="result" {% if not transcript %}hidden{% endif %}>{{ transcript or "" }}</div>
    <div id="page-command" class="command" {% if not command %}hidden{% endif %}>Instruction draft:
{{ command or "" }}</div>
    <div id="page-meta" class="meta" {% if not command_path and not command_text_path %}hidden{% endif %}>Saved payload:
{{ command_path or "" }}{% if command_text_path %}
Saved prompt:
{{ command_text_path }}{% endif %}</div>
    <div id="page-error" class="error" {% if not error %}hidden{% endif %}>{{ error or "" }}</div>
  </main>

  <script>
    const uploadForm = document.getElementById("upload-form");
    const startButton = document.getElementById("start-record");
    const stopButton = document.getElementById("stop-record");
    const statusBox = document.getElementById("record-status");
    const debugBox = document.getElementById("record-debug");
    const pageStatus = document.getElementById("page-status");
    const pageResult = document.getElementById("page-result");
    const pageCommand = document.getElementById("page-command");
    const pageMeta = document.getElementById("page-meta");
    const pageError = document.getElementById("page-error");
    let mediaRecorder = null;
    let activeStream = null;
    let recorderState = "idle";
    let chunks = [];
    let lastBlobSize = 0;

    const renderDebug = (note = "") => {
      const lines = [
        `state=${recorderState}`,
        `mediaRecorder=${mediaRecorder ? mediaRecorder.state : "none"}`,
        `chunks=${chunks.length}`,
        `lastBlobSize=${lastBlobSize}`,
      ];
      if (note) {
        lines.push(`note=${note}`);
      }
      debugBox.textContent = lines.join("\\n");
    };

    const setStatus = (text) => {
      statusBox.hidden = false;
      statusBox.textContent = text;
    };

    const setRecorderButtons = () => {
      startButton.disabled = recorderState !== "idle";
      stopButton.disabled = recorderState !== "recording";
      renderDebug("buttons updated");
    };

    const stopActiveStream = () => {
      if (!activeStream) {
        return;
      }
      activeStream.getTracks().forEach((track) => track.stop());
      activeStream = null;
    };

    const resetRecorderState = () => {
      stopActiveStream();
      if (mediaRecorder) {
        mediaRecorder.ondataavailable = null;
        mediaRecorder.onstop = null;
        mediaRecorder.onerror = null;
      }
      mediaRecorder = null;
      chunks = [];
      recorderState = "idle";
      setRecorderButtons();
    };

    const updateOutput = ({ message = "", transcript = "", command = "", command_path = "", command_text_path = "", error = "" }) => {
      pageStatus.hidden = !message;
      pageStatus.textContent = message;
      pageResult.hidden = !transcript;
      pageResult.textContent = transcript;
      pageCommand.hidden = !command;
      pageCommand.textContent = command;
      pageMeta.hidden = !command_path && !command_text_path;
      pageMeta.textContent = [
        command_path ? `Saved payload:\n${command_path}` : "",
        command_text_path ? `Saved prompt:\n${command_text_path}` : "",
      ].filter(Boolean).join("\n");
      pageError.hidden = !error;
      pageError.textContent = error;
    };

    const submitForTranscription = async (url, formData, processingText) => {
      recorderState = "uploading";
      setRecorderButtons();
      setStatus(processingText);
      updateOutput({ message: processingText, transcript: "", command: "", command_path: "", command_text_path: "", error: "" });
      renderDebug(`upload start -> ${url}`);
      try {
        const response = await fetch(url, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "fetch" },
        });
        const payload = await response.json();
        updateOutput(payload);
        setStatus(payload.error ? "処理に失敗しました。" : "処理完了");
        renderDebug(`upload done status=${response.status}`);
      } catch (error) {
        const message = "通信に失敗しました: " + error;
        updateOutput({ error: message });
        setStatus(message);
        renderDebug(`upload failed: ${error}`);
      } finally {
        recorderState = "idle";
        setRecorderButtons();
      }
    };

    uploadForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(uploadForm);
      await submitForTranscription(
        "{{ url_for('api_transcribe_upload') }}",
        formData,
        "アップロードした音声を処理中..."
      );
    });

    startButton?.addEventListener("click", async () => {
      if (recorderState !== "idle") {
        renderDebug("start ignored because recorder is not idle");
        return;
      }
      chunks = [];
      lastBlobSize = 0;
      try {
        activeStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(activeStream);
        mediaRecorder = recorder;
        renderDebug("getUserMedia ok; recorder created");
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            chunks.push(event.data);
          }
          renderDebug(`dataavailable size=${event.data.size}`);
        };
        recorder.onstop = async () => {
          if (mediaRecorder !== recorder) {
            renderDebug("onstop ignored because recorder changed");
            return;
          }
          const recordedChunks = [...chunks];
          lastBlobSize = recordedChunks.reduce((total, chunk) => total + chunk.size, 0);
          resetRecorderState();
          if (!recorder || recordedChunks.length === 0) {
            setStatus("録音データが空です。もう一度試してください。");
            renderDebug("no recorded chunks after stop");
            return;
          }
          const blob = new Blob(recordedChunks, { type: recorder.mimeType || "audio/webm" });
          lastBlobSize = blob.size;
          renderDebug(`blob ready size=${blob.size}`);
          const formData = new FormData();
          formData.append("audio_blob", blob, "browser_recording.webm");
          formData.append("model", document.getElementById("record_model").value);
          formData.append("language", document.getElementById("record_language").value);
          if (document.getElementById("record_command_only").checked) {
            formData.append("command_only", "true");
          }
          if (document.getElementById("record_save_command").checked) {
            formData.append("save_command", "true");
          }
          await submitForTranscription(
            "{{ url_for('api_transcribe_browser_recording') }}",
            formData,
            "録音データをアップロードして処理中..."
          );
        };
        recorder.onerror = () => {
          resetRecorderState();
          setStatus("録音中にエラーが発生しました。");
          renderDebug("recorder error");
        };
        recorder.start();
        recorderState = "recording";
        setRecorderButtons();
        setStatus("録音中...");
        renderDebug("recording started");
      } catch (error) {
        resetRecorderState();
        setStatus("録音開始に失敗しました: " + error);
        renderDebug(`start failed: ${error}`);
      }
    });

    stopButton?.addEventListener("click", () => {
      if (!mediaRecorder || mediaRecorder.state === "inactive" || recorderState !== "recording") {
        renderDebug("stop ignored because recorder is not active");
        return;
      }
      recorderState = "stopping";
      setRecorderButtons();
      mediaRecorder.stop();
      stopButton.disabled = true;
      setStatus("録音停止。処理中...");
      renderDebug("stop requested");
    });

    setRecorderButtons();
    renderDebug("ready");
  </script>
</body>
</html>
"""


def get_upload_dir() -> Path:
    """Return the upload directory for the web UI."""
    project_root = Path(__file__).resolve().parents[2]
    upload_dir = project_root / ".cache" / "web_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def build_temp_upload_path(filename: str) -> Path:
    """Return a unique temporary path for an uploaded audio file."""
    upload_dir = get_upload_dir()
    safe_name = secure_filename(filename) or "upload.wav"
    stem = Path(safe_name).stem or "upload"
    suffix = Path(safe_name).suffix or ".wav"
    return upload_dir / f"{stem}_{uuid4().hex}{suffix}"


def create_app() -> Flask:
    """Create the local Flask application."""
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return render_page()

    @app.post("/transcribe-upload")
    def transcribe_upload() -> str:
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
    def transcribe_browser_recording() -> str:
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
    return render_template_string(
        PAGE_TEMPLATE,
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
    model_name = request.form.get("model", "small").strip() or "small"
    language = request.form.get("language", "").strip() or None
    command_only = request.form.get("command_only", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    save_command = request.form.get("save_command", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    temp_path = build_temp_upload_path(filename)
    normalized_path = temp_path.with_suffix(".normalized.wav")

    transcript = ""
    command = ""
    command_path = ""
    command_text_path = ""
    error = ""
    status_code = 200

    try:
        validate_model_name(model_name)
        ensure_ffmpeg_available()
        temp_path.write_bytes(raw_bytes)
        audio_path = temp_path
        if temp_path.suffix.lower() == ".webm":
            audio_path = normalize_audio_for_transcription(temp_path, normalized_path)
        pipeline = TranscriptionPipeline(model_name=model_name)
        transcript = pipeline.transcribe_chunk(
            AudioChunk(path=audio_path, source="web"),
            language=language,
        )
        payload = build_handoff_payload(transcript)
        command = "" if payload is None else payload.command
        if save_command:
            saved_paths = save_handoff_bundle(
                transcript,
                json_path=get_default_handoff_output_path(source="web"),
                text_path=get_default_handoff_text_path(source="web"),
            )
            if saved_paths is not None:
                command_path = str(saved_paths.json_path)
                command_text_path = str(saved_paths.text_path)
    except AudioInputError as exc:
        error = f"Input error: {escape(str(exc))}"
        status_code = 400
    except AudioEnvironmentError as exc:
        error = f"Environment error: {escape(str(exc))}"
        status_code = 500
    except AudioTranscriptionError as exc:
        error = f"Transcription error: {escape(str(exc))}"
        status_code = 500
    finally:
        if temp_path.exists():
            temp_path.unlink()
        if normalized_path.exists():
            normalized_path.unlink()

    payload = {
        "message": (
            ""
            if error
            else (
                "音声を認識できませんでした。"
                if not transcript
                else (message or "文字起こしが完了しました。")
            )
        ),
        "transcript": "" if command_only else transcript,
        "command": command,
        "command_path": command_path,
        "command_text_path": command_text_path,
        "error": error,
    }
    return payload, status_code


def handle_transcription(
    raw_bytes: bytes,
    filename: str,
    message: str | None = None,
) -> str:
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
