# Share Note

## Turn contract

- turn mode: `code changes allowed`
- reviewer may update: `REVIEW.md` only
- implementer may update: `code`, `README.md`, `SHARE_NOTE.md`, `LOG.md`
- latest reviewed commit: `ae2c72c Normalize browser audio before transcription`
- latest applied review status:
  - reflected in code: generic default microphone selection
  - reflected in records: yes
  - remaining open items: `final` 条件の高度化, faster-whisper 比較, README 図解

## Changed files in latest implementation turn

- `src/io/audio.py`
- `src/core/pipeline.py`
- `src/main.py`
- `src/core/codex_bridge.py`
- `src/web/app.py`
- `smoke_test.py`
- `README.md`
- `SHARE_NOTE.md`
- `LOG.md`

## Current status

- `uv run python -m src.main data/sample_audio.mp3 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja` で文字起こし成功
- `uv run python -m src.main --mic --duration 5 --language ja` でも文字起こし成功
- `uv run python -m src.main --mic-loop --duration 3 --iterations 1 --language ja` で文字起こし成功
- `uv run python -m src.web.app` でローカル Web UI を起動可能
- `uv run python smoke_test.py` で 21 件の smoke test 成功
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
- 転写結果から `Codex instruction draft` を返す最小ブリッジを追加した
- API に `command_only` オプションを追加し、`command` を主に返せるようにした
- Web UI からも `command_only` を切り替えられるようにした
- Whisper モデルは `models/whisper/small.pt`
- GPU 利用を確認済み (`cuda:0`)
- `HD Pro Webcam C920` で録音確認済み
- README に Architecture 図と Mic-loop Flow 図を追加した
- `src/core/codex_bridge.py` を追加し、Codex 連携用 payload を共通化した
- CLI に `--command-output` を追加し、Codex 連携用 JSON を保存できるようにした
- Web/API からも `save_command` で Codex payload を保存できるようにした
- Codex handoff として JSON に加えて `.txt` prompt も保存できるようにした
- `.txt` 側は bare command ではなく、`Voice transcript` / `Requested task` を含む prompt 形式にした
- 保存済み handoff を取得する `/api/codex-handoff-latest` を追加した
- ローカル CLI から最新 handoff を読む `src.codex_handoff` を追加した
- 最新 handoff を任意コマンドへ流す `src.codex_runner` を追加した

## Next tasks

- `--mic-loop` の出力確定方針を決める
- VAD の導入方針を決める
- `partial` を `final` に切り替える条件を高度化する
- `--mic-loop` は有限ループ最終回に加えて、同一結果の連続でも `final` に寄せるようになった
- `webrtcvad` ベースの speech detection を追加した
- デフォルトマイク選択を C920 固定から、最初の入力デバイス優先へ一般化した
- 無音チャンクは CLI で `[silence N] silence detected` と表示するようになった
- CLI に `--emit-command` を追加した
- CLI に `--command-only` を追加した
- 短すぎる断片は `partial` のままにして、誤認識を `final` に寄せにくくした
- `final` へ寄せるには、同じ結果が複数回連続する必要がある
- `command-only` をそのまま Codex 実行へつなぐ境界整理を続ける
- Web/API 側の `command_path` を使った次段の Codex 実行 bridge を検討する
- Web/API 側の `command_text_path` を使って、そのまま貼り付ける運用も可能にした
- 他プロセスが最新 handoff を取りに来る API 境界を追加した
- Web を経由せずローカル handoff を読む CLI 境界も追加した
- ローカルの Codex 実行プロセスへ handoff を渡す bridge を追加した

## Review-derived actions

- 有限ループ最終回以外の `final` 条件として、同一結果の連続を反映済み
- 短すぎる断片は `final` に寄せにくくする調整を反映済み
- `final` は連続回数ベースで安定化を進めている
- 無音チャンクを Whisper に渡しにくくする軽い VAD 相当を反映済み
- VAD は未着手
- `webrtcvad` ベースの speech detection を反映済み
- 無音チャンク時の表示改善を反映済み
- デフォルトマイク選択の一般化を反映済み
- `/api/transcribe-browser-recording` のサーバーテストは反映済み
- ブラウザ録音の 2 回連続実行は実機確認済み
- ブラウザ録音の精度改善として `webm` の正規化を反映済み
- README への位置づけ反映は対応済み

## Handover notes

- `ffmpeg` が必要
- 入力はローカル音声ファイル前提
- 出力は標準出力のみ
- `MEMORY.md`, `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md` を用途別に使い分ける
