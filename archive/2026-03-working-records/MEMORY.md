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
- Worker は `worker/*` worktree で差分作成と局所確認までを担当し、main で直接コミットしない
- 統合担当だけが main worktree で採用判断、必要時の再構成、最終テスト、統合コミット、採用済み記録の反映を行う
- main と worker で同じ責務ファイルを同時に dirty にしない。main 側に未コミット差分がある場合は、統合作業か一時退避かを先に決めてから Worker を進める
- 統合担当の最新指示は `SHARE_NOTE.md` の `## Integrator messages` を正本にする
- Worker の事実ベースの返答は `LOG.md` に担当名 prefix 付きで書き、提案や境界相談は `OPERATIONS_DRAFT.md` または `MODULE_REQUIREMENTS.md` に書く
- `SHARE_NOTE.md` の `## Integrator messages` は最新有効分を正本とし、古い指示を積み上げすぎない
- 統合担当経由の連絡は、境界越え、契約変更、main 影響ありの案件を優先し、軽微な担当内判断まで集約しすぎない

## Codex startup

- Web UI を使う場合: `uv run python -m src.web.app` を起動し、`http://127.0.0.1:8000` を開く
- 保存済み handoff を Codex CLI に渡す場合: `uv run python -m src.agent_runner --source web --template codex-exec`
- `codex-exec` は `codex` コマンドが `PATH` にある前提

## Future direction

- マイク入力対応
- VAD / 無音トリム
- 必要に応じたノイズ対策
