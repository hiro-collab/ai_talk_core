# Share Note

## Current status

- `uv run python -m src.main data/sample_audio.mp3 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --language ja` でも文字起こし成功
- `uv run python -m src.main --mic-loop --duration 3 --iterations 1 --language ja` で文字起こし成功
- `uv run python -m src.web.app` でローカル Web UI を起動可能
- `uv run python smoke_test.py` で 8 件の smoke test 成功
- `src/core/pipeline.py` で共通の capture -> buffer -> transcribe 経路を追加
- `AudioBuffer` を追加し、`mic-loop` が最新チャンクをバッファ経由で文字起こしする形になった
- Whisper モデルは `models/whisper/small.pt`
- GPU 利用を確認済み (`cuda:0`)
- `HD Pro Webcam C920` で録音確認済み

## Next tasks

- `--mic-loop` の出力確定方針を決める
- VAD の導入方針を決める
- `buffer -> partial/final` の分離方針を決める

## Review-derived actions

- 入力検証と `ffmpeg` 確認の前倒しは反映済み
- 不正モデル名の `Input error` 分類は反映済み
- 録音処理の分離は反映済み
- 固定時間マイク録音 CLI は反映済み
- `--mic-loop` による擬似リアルタイム処理は反映済み
- ローカル Web UI は反映済み
- 共通の `capture -> buffer -> transcribe` 経路は反映済み
- CUDA / CPU fallback の README 追記は反映済み
- `silenceremove` による軽い無音トリムは反映済み
- VAD は未着手
- smoke test は反映済み

## Handover notes

- `ffmpeg` が必要
- 入力はローカル音声ファイル前提
- 出力は標準出力のみ
- `MEMORY.md`, `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md` を用途別に使い分ける
