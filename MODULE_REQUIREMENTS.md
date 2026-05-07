# Module Requirements

この文書は `ai-talk-core` の要求仕様だけを置く正本です。責務境界は `docs/module-responsibilities.md`、接続契約は `docs/integration-contract.md`、廃止/保留導線は `docs/retired-paths.md` に分けます。

## 目的

`ai-talk-core` は、ローカル音声入力を transcript に変換し、必要に応じて instruction / handoff を生成して外部 agent backend へ渡せる状態にする。

## 必須要件

- ローカル音声ファイルを Whisper で転写できること。
- 固定時間マイク録音と mic-loop を CLI から実行できること。
- Web UI / JSON API からファイルアップロードとブラウザ録音を扱えること。
- transcript から instruction draft を生成できること。
- handoff を JSON と text prompt の両方で保存し、CLI と API から読めること。
- 外部 adapter から `input_enabled` を更新できる input gate を持つこと。
- CLI / Web / API が core の状態管理ロジックを重複実装しないこと。
- Whisper, Torch, ffmpeg, microphone backend などのホスト依存処理を `src/io/` 側へ閉じ込めること。
- Web UI は maintenance UI として扱い、公開サーバー前提の認証・権限管理を持ち込まないこと。

## 非目標

- 公開 Web サービス化。
- gesture / keyboard / network adapter の具体実装。
- agent backend そのものの実行基盤。
- 真の音声 streaming STT。
- 長期履歴ストアや会話メモリ。

## 環境要件

- Python 3.11 以上。
- Python 依存は `uv sync` で同期する。
- `ffmpeg` が `PATH` から使えること。
- Ubuntu のマイク録音では `arecord` が使えること。
- GPU は任意。CUDA が使えない場合は CPU fallback を許容する。

## 互換要件

- agent 側の主導線は `src.agent_handoff` と `src.agent_runner`。
- `src.codex_handoff`, `src.codex_runner`, `/api/codex-handoff-latest` は互換入口として残す。
- API や payload に残る `command` / `command_only` / `save_command` は、`instruction` / `handoff` 系の主導線へ寄せつつ互換として受け付ける。

## 確認要件

- CLI / Web API / handoff / runner の変更後は `uv run python smoke_test.py` を実行する。
- Web UI 表示やブラウザ録音導線を変えた場合は、実ブラウザで録音を複数回実行して確認する。
