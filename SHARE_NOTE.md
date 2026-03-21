# Share Note

## Current status

- `uv run python -m src.main data/sample_audio.mp3 --language ja` で文字起こし成功
- Whisper モデルは `models/whisper/small.pt`
- GPU 利用を確認済み (`cuda:0`)
- `HD Pro Webcam C920` で録音確認済み

## Next tasks

- レビュー後の合意待ち

## Handover notes

- `ffmpeg` が必要
- 入力はローカル音声ファイル前提
- 出力は標準出力のみ
- `MEMORY.md`, `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md` を用途別に使い分ける
