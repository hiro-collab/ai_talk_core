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
      --bg: #f4efe5;
      --panel: rgba(255, 252, 245, 0.94);
      --panel-strong: #fffaf1;
      --line: #d7c7aa;
      --text: #21170f;
      --muted: #67594d;
      --accent: #9c4f2d;
      --accent-strong: #7d3e21;
      --accent-alt: #1c5660;
      --accent-soft: #f0e5d3;
      --ok-bg: #eff6f1;
      --ok-line: #bcd5c5;
      --result-bg: #fff4df;
      --result-line: #e3c48c;
      --command-bg: #edf0fc;
      --command-line: #b8c4f0;
      --error-bg: #fff0ee;
      --error-line: #e5b1ab;
      --shadow: 0 20px 50px rgba(49, 31, 15, 0.08);
    }
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      font-family: "Noto Sans JP", "Hiragino Sans", sans-serif;
      background:
        linear-gradient(145deg, rgba(255, 245, 225, 0.88), rgba(232, 241, 237, 0.7)),
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.85) 0%, transparent 30%),
        var(--bg);
      color: var(--text);
    }
    main {
      max-width: 1080px;
      margin: 0 auto;
      padding: 36px 20px 72px;
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
    h1 {
      margin: 0;
      font-size: clamp(2rem, 4vw, 3.2rem);
      line-height: 1.04;
    }
    p.lead {
      margin: 0;
      color: var(--muted);
      max-width: 68ch;
      line-height: 1.7;
    }
    .hero-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }
    .hero-card,
    .panel,
    .result-shell {
      background: var(--panel);
      border: 1px solid rgba(215, 199, 170, 0.9);
      border-radius: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }
    .hero-card {
      padding: 16px 18px;
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
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      align-items: start;
    }
    .panel {
      padding: 22px;
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
      font-size: 1.22rem;
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
      background: var(--accent-soft);
      color: var(--accent-strong);
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
    .advanced-card,
    .maintenance-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: var(--panel-strong);
    }
    .quick-card strong,
    .advanced-card strong,
    .maintenance-card strong {
      display: block;
      margin-bottom: 6px;
      font-size: 0.98rem;
    }
    .quick-card p,
    .advanced-card p,
    .maintenance-card p {
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
    label {
      display: block;
      color: var(--muted);
      font-size: 0.92rem;
    }
    input[type="file"],
    input[type="text"],
    select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      background: #fff;
      color: var(--text);
      font: inherit;
    }
    button {
      border: none;
      border-radius: 999px;
      padding: 12px 18px;
      font: inherit;
      cursor: pointer;
      background: var(--accent);
      color: #fff;
      transition: transform 120ms ease, opacity 120ms ease, background 120ms ease;
    }
    button:hover:enabled {
      transform: translateY(-1px);
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.58;
      transform: none;
    }
    button.secondary {
      background: var(--accent-alt);
    }
    button.ghost {
      background: #efe5d6;
      color: var(--text);
    }
    button.inline-action {
      margin: 0;
      padding: 10px 14px;
      font-size: 0.9rem;
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
      margin: 0;
      line-height: 1.55;
    }
    .checkbox {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }
    .checkbox input {
      width: auto;
      margin: 2px 0 0;
      accent-color: var(--accent);
    }
    .status-flow {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }
    .status-step {
      padding: 6px 10px;
      border-radius: 999px;
      background: #efe5d6;
      color: var(--muted);
      font-size: 0.82rem;
    }
    .status-step.active {
      background: var(--accent-alt);
      color: #fff;
    }
    .status-box,
    .result-box,
    .command-box,
    .meta-box,
    .error-box {
      margin-top: 16px;
      padding: 16px;
      border-radius: 18px;
      white-space: pre-wrap;
      line-height: 1.6;
    }
    .status-box[hidden],
    .result-box[hidden],
    .command-box[hidden],
    .meta-box[hidden],
    .error-box[hidden],
    .action-row[hidden] {
      display: none;
    }
    .status-box {
      background: var(--ok-bg);
      border: 1px solid var(--ok-line);
    }
    .result-box {
      background: var(--result-bg);
      border: 1px solid var(--result-line);
    }
    .command-box {
      background: var(--command-bg);
      border: 1px solid var(--command-line);
    }
    .meta-box {
      background: #f7f2e8;
      border: 1px solid #d7ccb8;
      color: var(--muted);
    }
    .error-box {
      background: var(--error-bg);
      border: 1px solid var(--error-line);
      color: #7d2217;
    }
    .maintenance-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .maintenance-copy {
      margin: 0;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.55;
    }
    .maintenance-list {
      display: grid;
      gap: 10px;
      margin-top: 12px;
    }
    .maintenance-item {
      display: grid;
      gap: 4px;
    }
    .maintenance-item span {
      color: var(--muted);
      font-size: 0.82rem;
    }
    .maintenance-value {
      display: block;
      font-size: 1rem;
      color: var(--text);
    }
    .result-shell {
      margin-top: 24px;
      padding: 22px;
    }
    .result-shell-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 14px;
    }
    .result-shell-header h2 {
      margin: 0;
      font-size: 1.2rem;
    }
    .result-shell-header p {
      margin: 6px 0 0;
      color: var(--muted);
      line-height: 1.55;
      font-size: 0.92rem;
    }
    .action-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }
    .action-feedback {
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.88rem;
      min-height: 1.4em;
    }
    details.debug-shell {
      margin-top: 16px;
    }
    details.debug-shell summary {
      cursor: pointer;
      color: var(--muted);
      font-size: 0.9rem;
    }
    .debug {
      margin-top: 12px;
      padding: 14px;
      border-radius: 16px;
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
      line-height: 1.55;
    }
    @media (max-width: 720px) {
      main {
        padding-inline: 14px;
      }
      .panel,
      .result-shell {
        padding: 18px;
      }
      .panel-header,
      .result-shell-header {
        flex-direction: column;
      }
      .mode-switch {
        width: 100%;
      }
      .mode-switch button {
        flex: 1 1 0;
      }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-copy">
        <h1>ai_core maintenance UI</h1>
        <p class="lead">音声を受け取り、文字起こしから handoff 確認までを 1 画面で進めます。通常は `かんたん` から始めます。</p>
      </div>
      <div class="hero-strip">
        <div class="hero-card">
          <p class="eyebrow">主導線</p>
          <strong>録音して handoff を確認</strong>
          <span>入力から結果確認までを最短で進められる構成です。</span>
        </div>
        <div class="hero-card">
          <p class="eyebrow">既定値</p>
          <strong>ja / small で開始</strong>
          <span>詳細設定と録音デバッグは下段にまとめています。</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>操作状況</h2>
          <p>使っている入口と次にすることだけを簡潔に表示します。</p>
        </div>
        <span class="mode-badge">概要</span>
      </div>
      <div class="maintenance-grid">
        <div class="maintenance-card">
          <strong>いまの入口</strong>
          <p class="maintenance-copy">最後に使った操作と録音状態をまとめます。</p>
          <div class="maintenance-list">
            <div class="maintenance-item">
              <span>入力モード</span>
              <strong id="ui-active-lane" class="maintenance-value">未選択</strong>
            </div>
            <div class="maintenance-item">
              <span>録音状態</span>
              <strong id="ui-recorder-state" class="maintenance-value">待機中</strong>
            </div>
          </div>
        </div>
        <div class="maintenance-card">
          <strong>結果と次の操作</strong>
          <p class="maintenance-copy">直近の結果と次に見る場所を示します。</p>
          <div class="maintenance-list">
            <div class="maintenance-item">
              <span>直近の結果</span>
              <strong id="ui-last-outcome" class="maintenance-value">{% if error %}エラー{% elif transcript or command %}結果あり{% elif message %}進行中{% else %}未実行{% endif %}</strong>
            </div>
            <div class="maintenance-item">
              <span>次にすること</span>
              <strong id="ui-next-action" class="maintenance-value">{% if error %}エラー内容を確認{% elif transcript or command %}内容をコピーまたは保存先を確認{% else %}かんたん から開始{% endif %}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>ファイルアップロード</h2>
            <p>通常は かんたん から始め、必要な時だけ 詳細 を開きます。</p>
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
              <strong>1. 音声ファイルを選ぶ</strong>
              <p>通常はここだけで十分です。</p>
              <div class="label-row">
                <label for="audio_file">音声ファイル</label>
                <span class="microcopy">mp3 / wav / m4a / mp4 / webm</span>
              </div>
              <input id="audio_file" name="audio_file" type="file" accept=".mp3,.wav,.m4a,.mp4,.mpeg,.mpga,.webm" required>
            </div>
            <div class="quick-card">
              <strong>2. 実行する</strong>
              <p>結果は下の結果ビューに集約されます。</p>
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
                文字起こし結果より指示草案を優先して確認する
              </label>
              <label class="checkbox" for="upload_save_handoff">
                <input id="upload_save_handoff" name="save_handoff" type="checkbox" value="true">
                handoff 保存先を残して、あとで再利用できるようにする
              </label>
            </div>
          </div>
        </form>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>ブラウザ録音</h2>
            <p>かんたん では録音開始と停止だけを出し、詳細設定は 詳細 に退避しています。</p>
          </div>
          <span class="mode-badge">録音</span>
        </div>
        <div class="mode-switch" role="tablist" aria-label="録音設定モード">
          <button type="button" class="tab-toggle active" data-target="record-quick">かんたん</button>
          <button type="button" class="tab-toggle" data-target="record-advanced">詳細</button>
        </div>

        <div id="record-quick" class="mode-panel quick-stack">
          <div class="quick-card">
            <strong>1. 録音する</strong>
            <p>停止後に自動でアップロードして処理します。</p>
            <div class="row">
              <button id="start-record" class="secondary" type="button">録音開始</button>
              <button id="stop-record" class="ghost" type="button" disabled>録音停止</button>
            </div>
          </div>
          <div class="quick-card">
            <strong>2. 進行を見る</strong>
            <p>録音から完了までの状態を表示します。</p>
            <div class="status-flow" aria-label="録音状態">
              <span id="step-idle" class="status-step active">待機中</span>
              <span id="step-recording" class="status-step">録音中</span>
              <span id="step-uploading" class="status-step">アップロード中</span>
              <span id="step-processing" class="status-step">文字起こし中</span>
              <span id="step-done" class="status-step">完了</span>
              <span id="step-error" class="status-step">エラー</span>
            </div>
            <div id="record-status" class="status-box" hidden></div>
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
              文字起こし結果より指示草案を優先して確認する
            </label>
            <label class="checkbox" for="record_save_handoff">
              <input id="record_save_handoff" type="checkbox" value="true">
              handoff 保存先を残して、あとで呼び出せるようにする
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
      <div class="result-shell-header">
        <div>
          <h2>結果ビュー</h2>
          <p>結果、指示草案、保存先、次の操作をここでまとめて確認できます。</p>
        </div>
        <span class="mode-badge">活用</span>
      </div>
      <div id="page-status" class="status-box" {% if not message %}hidden{% endif %}>{{ message or "" }}</div>
      <div id="page-result" class="result-box" {% if not transcript %}hidden{% endif %}>{{ transcript or "" }}</div>
      <div id="page-command" class="command-box" {% if not command %}hidden{% endif %}>指示草案:
{{ command or "" }}</div>
      <div id="page-meta" class="meta-box" {% if not command_path and not command_text_path %}hidden{% endif %}>{% if command_path %}handoff 保存先:
{{ command_path }}{% endif %}{% if command_text_path %}{% if command_path %}
{% endif %}プロンプト保存先:
{{ command_text_path }}{% endif %}</div>
      <div id="page-error" class="error-box" {% if not error %}hidden{% endif %}>{{ error or "" }}</div>
      <div id="result-actions" class="action-row" {% if not transcript and not command and not command_path and not command_text_path %}hidden{% endif %}>
        <button id="copy-transcript" class="inline-action ghost" type="button">文字起こしをコピー</button>
        <button id="copy-command" class="inline-action ghost" type="button">指示草案をコピー</button>
        <button id="refresh-handoff" class="inline-action secondary" type="button">保存先を確認</button>
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
    const actionFeedback = document.getElementById("action-feedback");
    const activeLane = document.getElementById("ui-active-lane");
    const recorderStateLabel = document.getElementById("ui-recorder-state");
    const lastOutcome = document.getElementById("ui-last-outcome");
    const nextAction = document.getElementById("ui-next-action");
    const copyTranscriptButton = document.getElementById("copy-transcript");
    const copyCommandButton = document.getElementById("copy-command");
    const refreshHandoffButton = document.getElementById("refresh-handoff");
    const statusSteps = {
      idle: document.getElementById("step-idle"),
      recording: document.getElementById("step-recording"),
      uploading: document.getElementById("step-uploading"),
      processing: document.getElementById("step-processing"),
      done: document.getElementById("step-done"),
      error: document.getElementById("step-error"),
    };
    let mediaRecorder = null;
    let activeStream = null;
    let recorderState = "idle";
    let chunks = [];
    let lastBlobSize = 0;

    const showActionFeedback = (text) => {
      actionFeedback.textContent = text;
    };

    const setActiveLane = (text) => {
      activeLane.textContent = text;
    };

    const setRecorderStateLabel = (text) => {
      recorderStateLabel.textContent = text;
    };

    const extractSavedPaths = (text = "") => ({
      command_path: (text.match(/handoff 保存先:\\n([^\\n]+)/) || [null, ""])[1],
      command_text_path: (text.match(/プロンプト保存先:\\n([^\\n]+)/) || [null, ""])[1],
    });

    const syncMaintenanceSummary = ({ message = "", transcript = "", command = "", command_path = "", command_text_path = "", error = "" }) => {
      if (error) {
        lastOutcome.textContent = "エラー";
        nextAction.textContent = "エラー内容を確認";
        return;
      }
      if (transcript || command) {
        lastOutcome.textContent = "結果あり";
        nextAction.textContent = command_path || command_text_path ? "保存先を確認" : "内容を確認して必要ならコピーする";
        return;
      }
      if (message) {
        lastOutcome.textContent = "進行中";
        nextAction.textContent = "処理完了を待つ";
        return;
      }
      lastOutcome.textContent = "未実行";
      nextAction.textContent = "かんたん から開始";
    };

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

    const setActiveStatusStep = (stepName) => {
      Object.values(statusSteps).forEach((element) => element?.classList.remove("active"));
      statusSteps[stepName]?.classList.add("active");
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
      setRecorderStateLabel("待機中");
      setActiveStatusStep("idle");
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
      syncMaintenanceSummary({ message, transcript, command, command_path, command_text_path, error });
    };

    const submitForTranscription = async (url, formData, processingText, laneLabel) => {
      recorderState = "uploading";
      setActiveLane(laneLabel);
      setRecorderStateLabel("アップロード中");
      setActiveStatusStep("uploading");
      setRecorderButtons();
      setStatus(processingText);
      updateOutput({ message: processingText, transcript: "", command: "", command_path: "", command_text_path: "", error: "" });
      showActionFeedback("");
      renderDebug(`upload start -> ${url}`);
      try {
        setRecorderStateLabel("文字起こし中");
        setActiveStatusStep("processing");
        const response = await fetch(url, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "fetch" },
        });
        const payload = await response.json();
        updateOutput(payload);
        if (payload.error) {
          setStatus("処理に失敗しました。");
          setRecorderStateLabel("エラー");
          setActiveStatusStep("error");
        } else {
          setStatus("処理完了");
          setRecorderStateLabel("完了");
          setActiveStatusStep("done");
        }
        renderDebug(`upload done status=${response.status}`);
      } catch (error) {
        const message = "通信に失敗しました: " + error;
        updateOutput({ error: message });
        setStatus(message);
        setRecorderStateLabel("エラー");
        setActiveStatusStep("error");
        renderDebug(`upload failed: ${error}`);
      } finally {
        recorderState = "idle";
        setRecorderButtons();
      }
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

    uploadForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      setActiveLane("ファイルアップロード");
      const formData = new FormData(uploadForm);
      await submitForTranscription(
        "{{ url_for('api_transcribe_upload') }}",
        formData,
        "アップロードした音声を処理中...",
        "ファイルアップロード"
      );
    });

    startButton?.addEventListener("click", async () => {
      if (recorderState !== "idle") {
        renderDebug("start ignored because recorder is not idle");
        return;
      }
      setActiveLane("ブラウザ録音");
      chunks = [];
      lastBlobSize = 0;
      showActionFeedback("");
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
            setRecorderStateLabel("エラー");
            setActiveStatusStep("error");
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
            "録音データをアップロードして処理中...",
            "ブラウザ録音"
          );
        };
        recorder.onerror = () => {
          resetRecorderState();
          setStatus("録音中にエラーが発生しました。");
          setRecorderStateLabel("エラー");
          setActiveStatusStep("error");
          renderDebug("recorder error");
        };
        recorder.start();
        recorderState = "recording";
        setRecorderStateLabel("録音中");
        setActiveStatusStep("recording");
        setRecorderButtons();
        setStatus("録音中です。停止後にアップロードして文字起こしします。");
        renderDebug("recording started");
      } catch (error) {
        resetRecorderState();
        setStatus("録音開始に失敗しました: " + error);
        setRecorderStateLabel("エラー");
        setActiveStatusStep("error");
        renderDebug(`start failed: ${error}`);
      }
    });

    stopButton?.addEventListener("click", () => {
      if (!mediaRecorder || mediaRecorder.state === "inactive" || recorderState !== "recording") {
        renderDebug("stop ignored because recorder is not active");
        return;
      }
      recorderState = "stopping";
      setRecorderStateLabel("停止処理中");
      setRecorderButtons();
      mediaRecorder.stop();
      stopButton.disabled = true;
      setStatus("録音停止。アップロードの準備中です。");
      setActiveStatusStep("uploading");
      renderDebug("stop requested");
    });

    const copyText = async (text, label) => {
      if (!text) {
        showActionFeedback(`${label} はまだありません。`);
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        showActionFeedback(`${label} をクリップボードへコピーしました。`);
      } catch (error) {
        showActionFeedback(`${label} のコピーに失敗しました: ${error}`);
      }
    };

    copyTranscriptButton?.addEventListener("click", async () => {
      await copyText(pageResult.textContent, "文字起こし結果");
    });

    copyCommandButton?.addEventListener("click", async () => {
      const commandText = pageCommand.textContent.replace(/^指示草案:\\n/, "");
      await copyText(commandText, "指示草案");
    });

    refreshHandoffButton?.addEventListener("click", async () => {
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
        showActionFeedback("handoff 保存先の表示を更新しました。");
      } catch (error) {
        showActionFeedback("handoff 保存先の確認に失敗しました: " + error);
      }
    });

    setActiveLane("未選択");
    setRecorderStateLabel("待機中");
    setActiveStatusStep("idle");
    setRecorderButtons();
    const initialSavedPaths = extractSavedPaths(pageMeta.textContent);
    syncMaintenanceSummary({
      message: pageStatus.textContent,
      transcript: pageResult.textContent,
      command: pageCommand.textContent.replace(/^指示草案:\n/, ""),
      command_path: initialSavedPaths.command_path,
      command_text_path: initialSavedPaths.command_text_path,
      error: pageError.textContent,
    });
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
