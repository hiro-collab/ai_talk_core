# Share Note

## Current status

- `uv run python -m src.main data/sample_audio.mp3 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --language ja` でも文字起こし成功
- `uv run python -m src.main --mic-loop --duration 3 --iterations 1 --language ja` で文字起こし成功
- `uv run python -m src.web.app` でローカル Web UI を起動可能
- `uv run python smoke_test.py` で 9 件の smoke test 成功
- `src/core/pipeline.py` で共通の capture -> buffer -> transcribe 経路を追加
- `AudioBuffer` を追加し、`mic-loop` が最新チャンクをバッファ経由で文字起こしする形になった
- Web UI は fetch ベースで結果領域だけを更新するようになった
- Whisper モデルは `models/whisper/small.pt`
- GPU 利用を確認済み (`cuda:0`)
- `HD Pro Webcam C920` で録音確認済み

## Next tasks

- `--mic-loop` の出力確定方針を決める
- VAD の導入方針を決める
- `buffer -> partial/final` の分離方針を決める

## Review-derived actions

- `buffer -> partial/final` の API 境界は未着手
- VAD は未着手

## Handover notes

- `ffmpeg` が必要
- 入力はローカル音声ファイル前提
- 出力は標準出力のみ
- `MEMORY.md`, `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md` を用途別に使い分ける
