"""Local web UI for audio transcription."""

from __future__ import annotations

from html import escape
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request
from werkzeug.utils import secure_filename

from src.core.pipeline import AudioChunk, TranscriptionPipeline
from src.io.audio import (
    AudioEnvironmentError,
    AudioInputError,
    AudioTranscriptionError,
    ensure_ffmpeg_available,
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
    .status, .result, .error {
      margin-top: 20px;
      padding: 16px;
      border-radius: 14px;
      white-space: pre-wrap;
    }
    .status[hidden], .result[hidden], .error[hidden] {
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
          <input id="upload_language" name="language" type="text" placeholder="ja">

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
        <input id="record_language" type="text" placeholder="ja">

        <p class="hint">ブラウザ側でマイク許可が必要です。録音停止後に自動でアップロードします。</p>
        <div id="record-status" class="status" hidden></div>
      </section>
    </div>

    <div id="page-status" class="status" {% if not message %}hidden{% endif %}>{{ message or "" }}</div>
    <div id="page-result" class="result" {% if not transcript %}hidden{% endif %}>{{ transcript or "" }}</div>
    <div id="page-error" class="error" {% if not error %}hidden{% endif %}>{{ error or "" }}</div>
  </main>

  <script>
    const uploadForm = document.getElementById("upload-form");
    const startButton = document.getElementById("start-record");
    const stopButton = document.getElementById("stop-record");
    const statusBox = document.getElementById("record-status");
    const pageStatus = document.getElementById("page-status");
    const pageResult = document.getElementById("page-result");
    const pageError = document.getElementById("page-error");
    let mediaRecorder = null;
    let chunks = [];

    const setStatus = (text) => {
      statusBox.hidden = false;
      statusBox.textContent = text;
    };

    const updateOutput = ({ message = "", transcript = "", error = "" }) => {
      pageStatus.hidden = !message;
      pageStatus.textContent = message;
      pageResult.hidden = !transcript;
      pageResult.textContent = transcript;
      pageError.hidden = !error;
      pageError.textContent = error;
    };

    const submitForTranscription = async (url, formData, processingText) => {
      setStatus(processingText);
      updateOutput({ message: processingText, transcript: "", error: "" });
      try {
        const response = await fetch(url, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "fetch" },
        });
        const payload = await response.json();
        updateOutput(payload);
        setStatus(payload.error ? "処理に失敗しました。" : "処理完了");
      } catch (error) {
        const message = "通信に失敗しました: " + error;
        updateOutput({ error: message });
        setStatus(message);
      }
    };

    uploadForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(uploadForm);
      await submitForTranscription(
        "{{ url_for('transcribe_upload') }}",
        formData,
        "アップロードした音声を処理中..."
      );
    });

    startButton?.addEventListener("click", async () => {
      chunks = [];
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            chunks.push(event.data);
          }
        };
        mediaRecorder.onstop = async () => {
          const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
          const formData = new FormData();
          formData.append("audio_blob", blob, "browser_recording.webm");
          formData.append("model", document.getElementById("record_model").value);
          formData.append("language", document.getElementById("record_language").value);
          await submitForTranscription(
            "{{ url_for('transcribe_browser_recording') }}",
            formData,
            "録音データをアップロードして処理中..."
          );
        };
        mediaRecorder.start();
        startButton.disabled = true;
        stopButton.disabled = false;
        setStatus("録音中...");
      } catch (error) {
        setStatus("録音開始に失敗しました: " + error);
      }
    });

    stopButton?.addEventListener("click", () => {
      if (!mediaRecorder) {
        return;
      }
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach((track) => track.stop());
      startButton.disabled = false;
      stopButton.disabled = true;
      setStatus("録音停止。処理中...");
    });
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

    @app.post("/transcribe-browser-recording")
    def transcribe_browser_recording() -> str:
        file_storage = request.files.get("audio_blob")
        if file_storage is None or file_storage.filename == "":
            return render_page(error="録音データを受け取れませんでした。")
        return handle_transcription(file_storage.read(), file_storage.filename, message="ブラウザ録音を処理しました。")

    return app


def render_page(
    transcript: str | None = None,
    error: str | None = None,
    message: str | None = None,
) -> str:
    """Render the single-page web UI."""
    return render_template_string(
        PAGE_TEMPLATE,
        transcript=transcript,
        error=error,
        message=message,
    )


def handle_transcription(
    raw_bytes: bytes,
    filename: str,
    message: str | None = None,
) -> str:
    """Persist uploaded audio temporarily and transcribe it."""
    model_name = request.form.get("model", "small").strip() or "small"
    language = request.form.get("language", "").strip() or None

    upload_dir = get_upload_dir()
    safe_name = secure_filename(filename) or "upload.wav"
    temp_path = upload_dir / safe_name

    transcript: str | None = None
    error: str | None = None

    try:
        validate_model_name(model_name)
        ensure_ffmpeg_available()
        temp_path.write_bytes(raw_bytes)
        pipeline = TranscriptionPipeline(model_name=model_name)
        transcript = pipeline.transcribe_chunk(
            AudioChunk(path=temp_path, source="web"),
            language=language,
        )
    except AudioInputError as exc:
        error = f"Input error: {escape(str(exc))}"
    except AudioEnvironmentError as exc:
        error = f"Environment error: {escape(str(exc))}"
    except AudioTranscriptionError as exc:
        error = f"Transcription error: {escape(str(exc))}"
    finally:
        if temp_path.exists():
            temp_path.unlink()

    resolved_message = message or "文字起こしが完了しました。"
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(
            {
                "message": "" if error else resolved_message,
                "transcript": transcript or "",
                "error": error or "",
            }
        )
    if error:
        return render_page(error=error)
    return render_page(transcript=transcript, message=resolved_message)


def main() -> int:
    """Run the local Flask development server."""
    app = create_app()
    app.run(host="127.0.0.1", port=8000, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
