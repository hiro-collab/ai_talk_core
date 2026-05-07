# Module Responsibilities

`ai-talk-core` の責務境界です。ここにはモジュールごとの担当範囲だけを書き、要求仕様や接続契約は混ぜません。

## 境界原則

- `core` は CLI、Flask、外部 agent backend、ホスト固有コマンドを知らない。
- `io` は Whisper、Torch、ffmpeg、microphone backend などのホスト依存を閉じ込める。
- `web` は HTTP 入出力と Web 専用整形を担当し、転写 primitive を再実装しない。
- `runners` と `drivers` は保存済み handoff を外部コマンドへ渡す境界を担当する。
- top-level `agent_*` / `codex_*` modules は CLI 互換ラッパーとして薄く保つ。

## Core

- `src/core/pipeline.py`: `AudioChunk`, `AudioBuffer`, `TranscriptionResult`, `TranscriptionPipeline` を提供し、transcript 生成の core primitive をまとめる。
- `src/core/session.py`: mic-loop の session 状態、repeat count、finalized text、last spoken result を管理する。
- `src/core/finalization.py`: partial から final へ寄せるヒューリスティクスを担当する。
- `src/core/input_gate.py`: 外部入力が capture を許可するかを backend 非依存で判断する。
- `src/core/agent_instruction.py`: transcript から instruction draft を作る。
- `src/core/handoff_bridge.py`: handoff bundle の JSON/text 保存と読込を担当する。
- `src/core/status_report.py`, `dependency_status.py`, `torch_pin_plan.py`: runtime と dependency の診断情報を作る。

## IO

- `src/io/audio.py`: Whisper 転写、モデルロード、ffmpeg/Torch/Whisper の runtime 検査を担当する。
- `src/io/microphone.py`: マイク録音、silence trim、軽量 speech detection、backend 選択を担当する。

## Web

- `src/web/app.py`: Flask route、local request policy、HTML rendering、static asset 配信、Web server lifecycle を担当する。
- `src/web/transcription_service.py`: Web/API 入力の正規化、転写呼び出し、handoff 保存、response payload 生成を担当する。
- `src/web/static/*`, `src/web/templates/*`: maintenance UI の表示とブラウザ録音操作を担当する。

## Runner / Driver

- `src/runners/agent.py`: 保存済み handoff を外部コマンドへ渡す runner CLI を担当する。
- `src/runners/handoff.py`: 保存済み handoff を CLI で表示する。
- `src/runners/ollama.py`: Ollama 向け command 組み立てを担当する。
- `src/runners/codex.py`: Codex template の互換層を担当する。
- `src/drivers/base.py`: `DriverRequest`, `DriverResult`, `dispatch_driver_request()` の共通契約を担当する。

## Entrypoints

- `src/main.py`: CLI 引数解釈、入口分岐、stdout/stderr 出力整形を担当する。
- `src.agent_handoff`: handoff reader の主導線。
- `src.agent_runner`: runner の主導線。
- `src.codex_handoff`, `src.codex_runner`: 互換入口。
- `src.ollama_runner`: Ollama runner の互換入口。

## Verification

- `smoke_test.py`: CLI / Web / API / handoff / runner の回帰確認を担当する。
- 実ブラウザの MediaRecorder 挙動は smoke test だけでは保証しない。
