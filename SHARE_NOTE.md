# Share Note

## Turn contract

- turn mode: `code changes allowed`
- reviewer may update: `REVIEW.md` only
- implementer may update: `code`, `README.md`, `SHARE_NOTE.md`, `LOG.md`
- latest reviewed commit: `ae2c72c Normalize browser audio before transcription`
- latest applied review status:
  - reflected in code: browser audio normalization before transcription
  - reflected in records: yes
  - remaining open items: `final` 条件の高度化, `VAD`, README 圧縮

## Changed files in latest implementation turn

- `src/io/audio.py`
- `src/web/app.py`
- `README.md`
- `SHARE_NOTE.md`
- `LOG.md`

## Current status

- `uv run python -m src.main data/sample_audio.mp3 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --language ja` でも文字起こし成功
- `uv run python -m src.main --mic-loop --duration 3 --iterations 1 --language ja` で文字起こし成功
- `uv run python -m src.web.app` でローカル Web UI を起動可能
- `uv run python smoke_test.py` で 16 件の smoke test 成功
- `src/core/pipeline.py` で共通の capture -> buffer -> transcribe 経路を追加
- `AudioBuffer` を追加し、`mic-loop` が最新チャンクをバッファ経由で文字起こしする形になった
- `TranscriptionResult` を追加し、`mic-loop` は各チャンクを `partial` として扱う形になった
- Web UI は fetch ベースで結果領域だけを更新するようになった
- ブラウザ録音は `MediaRecorder` と stream を明示的にリセットするようになった
- `/api/transcribe-upload` と `/api/transcribe-browser-recording` の JSON API ルートを追加した
- Web UI / API のアップロード一時ファイルはリクエストごとに固有名を使うようになった
- Web UI の fetch 先は `/api/...` ルートへ統一し、転写本体処理は共通関数へ寄せた
- ブラウザ録音には `Recorder Debug` を追加し、state と blob size を可視化した
- Web UI の言語入力欄は既定で `ja` にした
- ブラウザ録音の `webm` はサーバー側で `16kHz mono wav` 相当に正規化するようになった
- ブラウザ録音はユーザー実機で 2 回連続実行でき、録音状態の復帰と blob 生成は確認済み
- ブラウザ録音の主課題は連続録音の可否より認識精度側になった
- Whisper モデルは `models/whisper/small.pt`
- GPU 利用を確認済み (`cuda:0`)
- `HD Pro Webcam C920` で録音確認済み

## Next tasks

- `--mic-loop` の出力確定方針を決める
- VAD の導入方針を決める
- `partial` を `final` に切り替える条件を高度化する
- `--mic-loop` は有限ループ最終回に加えて、同一結果の連続でも `final` に寄せるようになった
- `--mic-loop` は `ffmpeg` の `silencedetect` でほぼ無音のチャンクを軽くスキップするようになった
- README の `Overview` / `Quick start` の重複を圧縮する

## Review-derived actions

- 有限ループ最終回以外の `final` 条件として、同一結果の連続を反映済み
- 無音チャンクを Whisper に渡しにくくする軽い VAD 相当を反映済み
- VAD は未着手
- `ffprobe` 依存の事前チェックは未着手
- 無音チャンク時の表示改善は未着手
- `/api/transcribe-browser-recording` のサーバーテストは反映済み
- ブラウザ録音の 2 回連続実行は実機確認済み
- ブラウザ録音の精度改善として `webm` の正規化を反映済み
- README への位置づけ反映は対応済み

## Handover notes

- `ffmpeg` が必要
- 入力はローカル音声ファイル前提
- 出力は標準出力のみ
- `MEMORY.md`, `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md` を用途別に使い分ける
