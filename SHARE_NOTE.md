# Share Note

## Turn contract

- turn mode: `code changes allowed`
- reviewer may update: `REVIEW.md` only
- implementer may update: `code`, `README.md`, `SHARE_NOTE.md`, `LOG.md`
- latest reviewed commit: `8cdbfae Group runner implementations under src/runners`
- latest applied review status:
  - reflected in code: runner CLI, mic-loop finalization on silence, interrupt-time final flush, longer-transcript repeat relaxation, time-based finalization, configurable VAD aggressiveness, Codex exec template with PATH validation, CUDA busy 時の CPU fallback, runner 実装の `src/runners/` 集約開始, `final` ヒューリスティクスの `src/core/finalization.py` 切り出し
  - reflected in records: yes
  - remaining open items: `final` 条件の高度化, VAD の実用化, Codex 実行テンプレート

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
- `uv run python smoke_test.py` で 65 件の smoke test 成功
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
- `src.codex_runner` に組み込みテンプレートを追加し、毎回コマンド列を書かずに試せるようにした
- `src.codex_runner` に `codex exec` へ handoff を流す `codex-exec` テンプレートを追加した
- `codex-exec` は `codex` コマンドの PATH 存在を実行前に検証するようにした
- runner 実装を `src/runners/` へ寄せ始め、トップレベル CLI は互換ラッパーとして残す方針にした
- Whisper モデル読み込み時に CUDA が busy / unavailable の場合、CPU fallback を試すようにした
- `mic-loop` は安定した発話のあとに無音が来た場合、その発話を `final` とみなせるようになった
- `mic-loop` は `Ctrl+C` 停止時も、未確定の最後の発話を `final` として flush できるようになった
- `mic-loop` は十分に長い同一発話であれば、2 回連続でも `final` に寄せるようになった
- `--mic-loop` では `--vad-aggressiveness 0..3` で WebRTC VAD の強さを調整できる
- 中くらい以上の発話は、安定時間が十分長ければ `final` に寄せるようになった
- `--final-stable-seconds` で `final` に寄せる安定時間を調整できる
- `partial/final` のヒューリスティクスは `src/main.py` から `src/core/finalization.py` に切り出した
- README の Architecture 図を handoff / runner まで含む最新構成に更新した

## Next tasks

- `--mic-loop` の出力確定方針を決める
- VAD の実用的な運用方針を決める
- `partial` を `final` に切り替える条件をさらに高度化する
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
- `codex_runner` は template 指定でも handoff を流せるようにした
- `codex_runner` は `codex-exec` テンプレートで Codex CLI にそのまま handoff を流せる
- 無音チャンク直後に直前発話を `final` とみなす補助ルールを追加した
- `Ctrl+C` で止めた時も、最後の安定発話を `final` として 1 回だけ出せるようにした
- 長い発話は 2 回連続、短い発話は 3 回連続を基準に `final` へ寄せる
- VAD のしきい値は CLI から調整できるようにした
- `codex-exec` は PATH に `codex` が無い場合、実行前に入力エラーで止まる
- `final` 判定には repeat 回数に加えて安定時間も使うようにした
- 時間ベースの `final` 条件は CLI からしきい値を調整できる
- `ollama_runner` はシステム未導入前提で、コマンド組み立てと失敗モードまでを先に整える

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
