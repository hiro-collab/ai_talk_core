# Project Memory

## Environment

- OS: Ubuntu 22.04
- Python: 3.11.15
- Virtual environment: `.venv`
- Package manager: `uv`
- System dependency: `ffmpeg`

## Stable decisions

- Whisper の既定モデルは `small`
- Whisper モデル保存先は `models/whisper`
- サンプル音声は `data/sample_audio.mp3`
- ローカル音声ファイルを CLI から文字起こしする最小構成を優先
- `ai_core` は現時点では `~/projects` 配下の開発・実験本体として扱い、`~/dev` の共通基盤とは分ける

## Design rules

- CLI は薄く保つ
- 入出力と文字起こし処理を分ける
- システム全体を変更しない
- 既存ディレクトリ構造を尊重する
- runner 系の実装は `src/runners/` に寄せ、トップレベル CLI は互換ラッパーとして残す
- `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md`, `MEMORY.md` は用途別に使い分ける
- `DESIGN_REVIEW.md` はデザインレビュー専用の主記録先として使い、コードレビューとは混ぜない
- `SHARE_NOTE.md` の `Turn contract` は最上段で維持し、レビュー運用の基準点とする
- `AGENTS.md` や `/init` 相当の運用ファイルは重複作成しない。既存ファイルの有無を先に確認し、必要時は追加前に提案する

## Codex startup

- Web UI を使う場合: `uv run python -m src.web.app` を起動し、`http://127.0.0.1:8000` を開く
- 保存済み handoff を Codex CLI に渡す場合: `uv run python -m src.agent_runner --source web --template codex-exec`
- `codex-exec` は `codex` コマンドが `PATH` にある前提

## Future direction

- マイク入力対応
- VAD / 無音トリム
- 必要に応じたノイズ対策
