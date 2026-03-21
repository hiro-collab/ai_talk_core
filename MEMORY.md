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

## Design rules

- CLI は薄く保つ
- 入出力と文字起こし処理を分ける
- システム全体を変更しない
- 既存ディレクトリ構造を尊重する
- `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md`, `MEMORY.md` は用途別に使い分ける
- `SHARE_NOTE.md` の `Turn contract` は最上段で維持し、レビュー運用の基準点とする

## Future direction

- マイク入力対応
- VAD / 無音トリム
- 必要に応じたノイズ対策
