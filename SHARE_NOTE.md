# Share Note

## Current status

- `uv run python -m src.main data/sample_audio.mp3 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --language ja` でも文字起こし成功
- Whisper モデルは `models/whisper/small.pt`
- GPU 利用を確認済み (`cuda:0`)
- `HD Pro Webcam C920` で録音確認済み

## Next tasks

- README に CUDA / CPU fallback の再現条件を補強する
- 録音処理の専用モジュール境界をもう一段整理する
- VAD / silence trim の最小導入方針を決める
- 成功系と主要失敗系の smoke test を追加する

## Review-derived actions

- 入力検証と `ffmpeg` 確認の前倒しは反映済み
- 不正モデル名の `Input error` 分類は反映済み
- 録音処理の分離は反映済み
- 固定時間マイク録音 CLI は反映済み
- CUDA / CPU fallback の README 追記は未着手
- VAD / silence trim は未着手
- smoke test は未着手

## Handover notes

- `ffmpeg` が必要
- 入力はローカル音声ファイル前提
- 出力は標準出力のみ
- `MEMORY.md`, `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md` を用途別に使い分ける
