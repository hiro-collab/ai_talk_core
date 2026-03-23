"""Local web UI for audio transcription."""

from __future__ import annotations

from flask import Flask, jsonify, render_template_string, request

from src.core.handoff_bridge import load_handoff_bundle
from src.web.transcription_service import WebTranscriptionRequest, process_web_transcription


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
      margin: 0;
      color: var(--muted);
      max-width: 68ch;
      line-height: 1.7;
    }
    .hero {
      display: grid;
      gap: 18px;
      margin-bottom: 24px;
    }
    .hero-copy {
      display: grid;
      gap: 10px;
    }
    .hero-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }
    .hero-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      box-shadow: 0 14px 40px rgba(36, 22, 10, 0.08);
    }
    .eyebrow {
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .hero-card strong {
      display: block;
      font-size: 1rem;
    }
    .hero-card span {
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.5;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 16px;
    }
    .panel-header h2 {
      margin: 0;
      font-size: 1.2rem;
    }
    .panel-header p {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.55;
    }
    .mode-badge {
      border-radius: 999px;
      padding: 7px 12px;
      background: #f0e5d3;
      color: #7d3e21;
      font-size: 0.8rem;
      white-space: nowrap;
    }
    .mode-switch {
      display: inline-flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }
    .mode-switch button {
      margin: 0;
      min-width: 104px;
      padding: 10px 14px;
      background: #efe5d6;
      color: var(--text);
    }
    .mode-switch button.active {
      background: var(--accent);
      color: #fff;
    }
    .mode-panel[hidden] {
      display: none;
    }
    .quick-stack,
    .advanced-stack {
      display: grid;
      gap: 14px;
    }
    .quick-card,
    .advanced-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: #fffaf1;
    }
    .step-head {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 6px;
    }
    .step-head strong {
      margin: 0;
    }
    .step-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 999px;
      background: #f0e5d3;
      color: #7d3e21;
      font-size: 0.82rem;
      font-weight: 700;
      flex: 0 0 auto;
    }
    .quick-card strong,
    .advanced-card strong {
      display: block;
      margin-bottom: 6px;
      font-size: 0.98rem;
    }
    .quick-card p,
    .advanced-card p {
      margin: 0;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.55;
    }
    .label-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin: 14px 0 6px;
    }
    .label-row label {
      margin: 0;
    }
    .microcopy {
      color: var(--muted);
      font-size: 0.82rem;
    }
    .helper-note {
      margin-top: 14px;
      padding: 12px 14px;
      border: 1px dashed var(--line);
      border-radius: 14px;
      background: #f7f1e6;
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.55;
    }
    .helper-note strong {
      color: var(--text);
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
    details.debug-shell {
      margin-top: 16px;
    }
    details.debug-shell summary {
      cursor: pointer;
      color: var(--muted);
      font-size: 0.9rem;
    }
    .status-current {
      margin-top: 16px;
      display: grid;
      gap: 12px;
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      width: fit-content;
      padding: 8px 14px;
      border-radius: 999px;
      background: var(--accent-2);
      color: #fff;
      font-size: 0.88rem;
      font-weight: 700;
    }
    .status-pill::before {
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      opacity: 0.75;
    }
    .result-shell {
      margin-top: 24px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 14px 40px rgba(36, 22, 10, 0.08);
    }
    .result-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }
    .result-actions[hidden] {
      display: none;
    }
    .inline-action {
      margin-top: 0;
      padding: 10px 14px;
      font-size: 0.9rem;
    }
    .action-feedback {
      min-height: 1.4em;
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.88rem;
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-copy">
        <h1>ai_core Web UI</h1>
        <p class="lead">音声を入れて文字起こしし、必要なら handoff 保存先まで確認します。通常は `かんたん` だけを使います。</p>
      </div>
      <div class="hero-strip">
        <div class="hero-card">
          <p class="eyebrow">流れ</p>
          <strong>入れる -> 結果を見る -> handoff を確認</strong>
          <span>主導線を先に見せ、設定変更だけを後ろへ分けます。</span>
        </div>
        <div class="hero-card">
          <p class="eyebrow">既定</p>
          <strong>`ja` / `small` でそのまま使う</strong>
          <span>通常はそのまま使い、変更時だけ `詳細` を開きます。</span>
        </div>
        <div class="hero-card">
          <p class="eyebrow">デバッグ</p>
          <strong>通常導線から分離</strong>
          <span>録音デバッグは折りたたみ、通常の操作面から分けています。</span>
        </div>
      </div>
    </section>

    <div class="grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>ファイルアップロード</h2>
            <p>通常は `かんたん` だけで実行できます。</p>
          </div>
          <span class="mode-badge">アップロード</span>
        </div>
        <div class="mode-switch" role="tablist" aria-label="アップロード設定モード">
          <button type="button" class="tab-toggle active" data-target="upload-quick">かんたん</button>
          <button type="button" class="tab-toggle" data-target="upload-advanced">詳細</button>
        </div>
        <form id="upload-form" action="{{ url_for('transcribe_upload') }}" method="post" enctype="multipart/form-data">
          <div id="upload-quick" class="mode-panel quick-stack">
            <div class="quick-card">
              <div class="step-head">
                <span class="step-badge">1</span>
                <strong>ファイルを選ぶ</strong>
              </div>
              <p>通常はここから始めます。</p>
              <label for="audio_file">音声ファイル</label>
              <input id="audio_file" name="audio_file" type="file" accept=".mp3,.wav,.m4a,.mp4,.mpeg,.mpga,.webm" required>
              <div class="helper-note">
                <strong>このまま実行できます。</strong> `ja` / `small` を使います。
              </div>
            </div>
            <div class="quick-card">
              <div class="step-head">
                <span class="step-badge">2</span>
                <strong>文字起こしする</strong>
              </div>
              <p>結果は下に表示されます。</p>
              <button type="submit">文字起こしする</button>
            </div>
          </div>

          <div id="upload-advanced" class="mode-panel advanced-stack" hidden>
            <div class="advanced-card">
              <strong>処理パラメータ</strong>
              <div class="label-row">
                <label for="upload_model">モデル</label>
                <span class="microcopy">既定: small</span>
              </div>
              <select id="upload_model" name="model">
                <option value="small">small</option>
                <option value="base">base</option>
                <option value="medium">medium</option>
              </select>

              <div class="label-row">
                <label for="upload_language">言語コード</label>
                <span class="microcopy">既定: ja</span>
              </div>
              <input id="upload_language" name="language" type="text" value="ja" placeholder="ja">
            </div>
            <div class="advanced-card">
              <strong>出力オプション</strong>
              <label class="checkbox" for="upload_instruction_only">
                <input id="upload_instruction_only" name="instruction_only" type="checkbox" value="true">
                指示草案を優先表示する
              </label>
              <label class="checkbox" for="upload_save_handoff">
                <input id="upload_save_handoff" name="save_handoff" type="checkbox" value="true">
                handoff を保存する
              </label>
            </div>
          </div>
        </form>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>ブラウザ録音</h2>
            <p>通常は `かんたん` で録音開始と停止だけを使います。</p>
          </div>
          <span class="mode-badge">録音</span>
        </div>
        <div class="mode-switch" role="tablist" aria-label="録音設定モード">
          <button type="button" class="tab-toggle active" data-target="record-quick">かんたん</button>
          <button type="button" class="tab-toggle" data-target="record-advanced">詳細</button>
        </div>

        <div id="record-quick" class="mode-panel quick-stack">
          <div class="quick-card">
            <div class="step-head">
              <span class="step-badge">1</span>
              <strong>録音を始める</strong>
            </div>
              <p>停止すると自動で送信します。</p>
            <div class="row">
              <button id="start-record" class="secondary" type="button">録音開始</button>
              <button id="stop-record" class="ghost" type="button" disabled>録音停止</button>
            </div>
            <div class="helper-note">
                <strong>このまま録音できます。</strong> `ja` / `small` を使います。
            </div>
          </div>
          <div class="quick-card">
            <div class="step-head">
              <span class="step-badge">2</span>
              <strong>現在の状態</strong>
            </div>
            <p>いまの状態だけを表示します。</p>
            <div class="status-current" aria-label="録音状態">
              <div id="record-status-pill" class="status-pill">待機中</div>
            </div>
            <div id="record-status" class="status" hidden></div>
          </div>
        </div>

        <div id="record-advanced" class="mode-panel advanced-stack" hidden>
          <div class="advanced-card">
            <strong>処理パラメータ</strong>
            <div class="label-row">
              <label for="record_model">モデル</label>
              <span class="microcopy">既定: small</span>
            </div>
            <select id="record_model">
              <option value="small">small</option>
              <option value="base">base</option>
              <option value="medium">medium</option>
            </select>

            <div class="label-row">
              <label for="record_language">言語コード</label>
              <span class="microcopy">既定: ja</span>
            </div>
            <input id="record_language" type="text" value="ja" placeholder="ja">
          </div>
          <div class="advanced-card">
            <strong>出力オプション</strong>
            <label class="checkbox" for="record_instruction_only">
              <input id="record_instruction_only" type="checkbox" value="true">
              指示草案を優先表示する
            </label>
            <label class="checkbox" for="record_save_handoff">
              <input id="record_save_handoff" type="checkbox" value="true">
              handoff を保存する
            </label>
            <p class="hint">録音デバッグは通常導線から外し、下の開発者向けセクションに隔離しています。</p>
          </div>
        </div>

        <details class="debug-shell">
          <summary>開発者向けデバッグ情報</summary>
          <div class="debug">
            <strong>録音デバッグ</strong>
            <pre id="record-debug">state=idle</pre>
          </div>
        </details>
      </section>
    </div>

    <section class="result-shell">
      <div class="panel-header">
        <div>
          <h2>結果</h2>
          <p>結果を見て、必要ならコピーか保存先確認へ進みます。</p>
        </div>
        <span class="mode-badge">活用</span>
      </div>
      <div id="page-status" class="status" {% if not message %}hidden{% endif %}>{{ message or "" }}</div>
      <div id="page-result" class="result" {% if not transcript %}hidden{% endif %}>{{ transcript or "" }}</div>
      <div id="page-command" class="command" {% if not command %}hidden{% endif %}>指示草案:
{{ command or "" }}</div>
      <div id="page-meta" class="meta" {% if not command_path and not command_text_path %}hidden{% endif %}>{% if command_path %}handoff 保存先:
{{ command_path }}{% endif %}{% if command_text_path %}{% if command_path %}
{% endif %}プロンプト保存先:
{{ command_text_path }}{% endif %}</div>
      <div id="page-error" class="error" {% if not error %}hidden{% endif %}>{{ error or "" }}</div>
      <div id="result-actions" class="result-actions" {% if not transcript and not command and not command_path and not command_text_path %}hidden{% endif %}>
        <button id="copy-transcript" class="ghost inline-action" type="button">文字起こしをコピー</button>
        <button id="copy-command" class="ghost inline-action" type="button">指示草案をコピー</button>
        <button id="refresh-handoff" class="secondary inline-action" type="button" {% if not command_path and not command_text_path %}disabled{% endif %}>保存先を確認</button>
      </div>
      <div id="action-feedback" class="action-feedback"></div>
    </section>
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
    const resultActions = document.getElementById("result-actions");
    const copyTranscriptButton = document.getElementById("copy-transcript");
    const copyCommandButton = document.getElementById("copy-command");
    const refreshHandoffButton = document.getElementById("refresh-handoff");
    const actionFeedback = document.getElementById("action-feedback");
    const statusPill = document.getElementById("record-status-pill");
    let mediaRecorder = null;
    let activeStream = null;
    let recorderState = "idle";
    let chunks = [];
    let lastBlobSize = 0;

    const showActionFeedback = (text) => {
      actionFeedback.textContent = text;
    };

    document.querySelectorAll(".mode-switch").forEach((switchNode) => {
      const buttons = Array.from(switchNode.querySelectorAll(".tab-toggle"));
      buttons.forEach((button) => {
        button.addEventListener("click", () => {
          const targetId = button.dataset.target;
          const panel = document.getElementById(targetId);
          const panelGroup = switchNode.parentElement;
          buttons.forEach((candidate) => candidate.classList.toggle("active", candidate === button));
          panelGroup.querySelectorAll(".mode-panel").forEach((candidate) => {
            candidate.hidden = candidate !== panel;
          });
        });
      });
    });

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
      statusBox.hidden = !text;
      statusBox.textContent = text;
    };

    const setCurrentStatus = (stepName) => {
      const labels = {
        idle: "待機中",
        recording: "録音中",
        stopping: "停止処理中",
        uploading: "アップロード中",
        processing: "文字起こし中",
        done: "完了",
        error: "エラー",
      };
      statusPill.textContent = labels[stepName] || "待機中";
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
      setCurrentStatus("idle");
      setRecorderButtons();
    };

    const updateOutput = ({ message = "", transcript = "", command = "", command_path = "", command_text_path = "", error = "" }) => {
      pageStatus.hidden = !message;
      pageStatus.textContent = message;
      pageResult.hidden = !transcript;
      pageResult.textContent = transcript;
      pageCommand.hidden = !command;
      pageCommand.textContent = command ? `指示草案:\\n${command}` : "";
      pageMeta.hidden = !command_path && !command_text_path;
      pageMeta.textContent = [
        command_path ? `handoff 保存先:\\n${command_path}` : "",
        command_text_path ? `プロンプト保存先:\\n${command_text_path}` : "",
      ].filter(Boolean).join("\\n");
      pageError.hidden = !error;
      pageError.textContent = error;
      resultActions.hidden = !transcript && !command && !command_path && !command_text_path;
      copyTranscriptButton.disabled = !transcript;
      copyCommandButton.disabled = !command;
      refreshHandoffButton.disabled = !command_path && !command_text_path;
    };

    const submitForTranscription = async (url, formData, processingText) => {
      recorderState = "uploading";
      setCurrentStatus("uploading");
      setRecorderButtons();
      setStatus(processingText);
      updateOutput({ message: processingText, transcript: "", command: "", command_path: "", command_text_path: "", error: "" });
      showActionFeedback("");
      renderDebug(`upload start -> ${url}`);
      try {
        setCurrentStatus("processing");
        const response = await fetch(url, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "fetch" },
        });
        const payload = await response.json();
        updateOutput(payload);
        if (payload.error) {
          setStatus("処理に失敗しました。");
          setCurrentStatus("error");
        } else {
          setStatus("処理完了");
          setCurrentStatus("done");
        }
        renderDebug(`upload done status=${response.status}`);
      } catch (error) {
        const message = "通信に失敗しました: " + error;
        updateOutput({ error: message });
        setStatus(message);
        setCurrentStatus("error");
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
            setCurrentStatus("error");
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
          if (document.getElementById("record_instruction_only").checked) {
            formData.append("instruction_only", "true");
          }
          if (document.getElementById("record_save_handoff").checked) {
            formData.append("save_handoff", "true");
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
          setCurrentStatus("error");
          renderDebug("recorder error");
        };
        recorder.start();
        recorderState = "recording";
        setCurrentStatus("recording");
        setRecorderButtons();
        setStatus("録音中です。停止後にアップロードして文字起こしします。");
        renderDebug("recording started");
      } catch (error) {
        resetRecorderState();
        setStatus("録音開始に失敗しました: " + error);
        setCurrentStatus("error");
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
      setStatus("録音停止。アップロードの準備中です。");
      setCurrentStatus("stopping");
      renderDebug("stop requested");
    });

    const copyText = async (text, label) => {
      if (!text) {
        showActionFeedback(`${label} はまだありません。`);
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        showActionFeedback(`${label} をコピーしました。`);
      } catch (error) {
        showActionFeedback(`${label} のコピーに失敗しました: ${error}`);
      }
    };

    copyTranscriptButton?.addEventListener("click", async () => {
      await copyText(pageResult.textContent, "文字起こし");
    });

    copyCommandButton?.addEventListener("click", async () => {
      const commandText = pageCommand.textContent.replace(/^指示草案:\\n/, "");
      await copyText(commandText, "指示草案");
    });

    refreshHandoffButton?.addEventListener("click", async () => {
      if (refreshHandoffButton.disabled) {
        showActionFeedback("保存済み handoff がまだありません。");
        return;
      }
      try {
        const response = await fetch("{{ url_for('api_agent_handoff_latest') }}?source=web");
        const payload = await response.json();
        if (!response.ok) {
          showActionFeedback(payload.error || "handoff 保存先を取得できませんでした。");
          return;
        }
        updateOutput({
          message: pageStatus.textContent,
          transcript: payload.transcript || pageResult.textContent,
          command: payload.command || pageCommand.textContent.replace(/^指示草案:\\n/, ""),
          command_path: payload.command_path || "",
          command_text_path: payload.command_text_path || "",
          error: "",
        });
        showActionFeedback("handoff 保存先を更新しました。");
      } catch (error) {
        showActionFeedback("handoff 保存先の確認に失敗しました: " + error);
      }
    });

    setCurrentStatus("idle");
    setRecorderButtons();
    copyTranscriptButton.disabled = !pageResult.textContent;
    copyCommandButton.disabled = !pageCommand.textContent;
    renderDebug("ready");
  </script>
</body>
</html>
"""


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
