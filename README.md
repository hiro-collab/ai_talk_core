# ai_core

音声で拾った内容を transcript にし、instruction / handoff を生成して外部 agent へつなぐためのローカル基盤です。
Whisper を使った転写は中核の手段であり、主目的は `voice capture -> transcript -> handoff -> agent backend` の流れを育てることです。
現在は `file input`, `mic`, `mic-loop`, `input gate`, `Web UI`, `JSON API`, `agent handoff` を扱えます。

## What This Is

- 主目的: 音声入力を agent 向け handoff に変換すること
- 主導線: `agent_*` CLI / API / handoff
- Web UI: maintenance UI。保守用だが、使いやすく状態が分かることを重視する
- 現在の共通経路: `capture -> buffer -> transcribe`
- 外部入力境界: gesture や network adapter は `input_enabled` に変換してから core へ渡す

## Start Here

GitHub から clone して初回セットアップする:

```bash
git clone https://github.com/hiro-collab/ai_talk_core.git
cd ai_talk_core
sudo apt update
sudo apt install -y ffmpeg alsa-utils
uv sync
uv run python -m src.main data/sample_audio.mp3 --language ja --model small
```

`uv` が未導入の場合は、先に公式手順で `uv` をインストールしてください。Python 依存は `pyproject.toml` と `uv.lock` で管理しているため、通常は `requirements.txt` ではなく `uv sync` を使います。

最短で再実行する:

```bash
uv sync
uv run python -m src.main data/sample_audio.mp3 --language ja
```

初回実行時は Whisper の `small` モデルを `models/whisper/` に自動ダウンロードします。ネットワーク接続が必要です。

Web UI を起動する:

```bash
uv run python -m src.web.app
```

Windows では次の helper を使うと、環境確認後に Web UI を起動してブラウザを開けます:

```powershell
.\start_web.ps1
```

保存済み handoff を agent 向けに読む:

```bash
uv run python -m src.agent_handoff --source web --format prompt
```

保存済み handoff をそのまま外部コマンドへ渡す:

```bash
uv run python -m src.agent_runner --source web --template cat
```

## Current Status

- 今できること: ファイル入力、固定時間マイク入力、簡易マイクループ、Web UI、JSON API、軽量 VAD、軽い無音トリム、instruction draft、handoff 保存
- 入力制御: `input gate` で mic-loop の capture 可否を外部 adapter から制御できる土台を追加済み
- まだできないこと: 真のリアルタイム streaming、本格的な常時待受 UI、`partial/final` の本格運用
- 位置づけ: GUI 主体ではなく、音声入力フロントエンド兼サービス境界を優先
- ブラウザ録音の `webm` はサーバー側で `16kHz mono wav` 相当に正規化してから転写
- Web UI の言語入力欄は既定で `ja`
- `HD Pro Webcam C920` で録音確認済み

## Requirements

- Ubuntu 22.04
- Python 3.11.15
- `uv`
- `ffmpeg`
- `alsa-utils` (`arecord` を使うマイク録音時に必要)
- ネットワーク接続 (初回 Whisper モデル取得時に必要)
- 仮想環境は `uv sync` で作られる `.venv` を使用
- GPU は任意です

## Verified Environment

以下の環境で動作確認しています。PC 固有のホスト名、ユーザー名、ローカル絶対パスは再現に不要なため記載していません。

- OS: Ubuntu 22.04
- Python: 3.11.15
- Package manager: `uv`
- Audio tools: `ffmpeg`, `arecord`
- Whisper model: `small`, `base`
- GPU: NVIDIA CUDA 環境で確認済み
- CPU fallback: 動作しますが、転写は遅くなる場合があります
- Microphone: HD Pro Webcam C920

## Windows Support Plan

Windows ネイティブ実行は一部検証済みです。現時点では Windows 対応を進めている段階で、確実な主対象は引き続き Ubuntu ですが、ファイル入力と Web UI/API 周りは Windows でも開発できます。

- Windows で確認済みの範囲: `uv sync`, ファイル入力の文字起こし, Web UI/API のサーバー側 smoke test, Whisper モデル取得
- Windows のマイク録音は `ffmpeg-dshow` backend を使います。`--mic-backend auto` は Windows では `ffmpeg-dshow`, Linux では `arecord` を選びます
- Windows ネイティブ利用時は `ffmpeg` を別途インストールし、`PATH` に追加してください
- CUDA/GPU 利用は Windows ネイティブと WSL2 で PyTorch の導入条件が変わります
- WSL2 + Ubuntu は、Linux と同じ `arecord` 前提のマイク録音を検証したい場合の有力な選択肢です

Windows ネイティブでの最小確認:

```powershell
uv sync
uv run python -m src.main --doctor
uv run python -m src.main data\sample_audio.mp3 --language ja --model small
uv run python smoke_test.py
```

Windows ネイティブで Web UI を起動:

```powershell
.\start_web.ps1
```

初回だけ `.venv` を作り直したい場合:

```powershell
.\start_web.ps1 -Sync
```

GPU セットアップ後に `-Sync` を使うと、CUDA 版 Torch が CPU 版に戻ることがあります。その場合は `.\setup_gpu_windows.ps1 -Cuda cu128` を再実行してください。

Windows のマイク録音を試す:

```powershell
uv run python -m src.main --mic --duration 5 --language ja --mic-backend auto
```

`default` では `ffmpeg` が最初に報告した DirectShow audio device を使います。明示指定したい場合は、先に device 名を確認してください。

```powershell
ffmpeg -hide_banner -list_devices true -f dshow -i dummy
uv run python -m src.main --mic --duration 5 --language ja --mic-device "Microphone Array (Realtek(R) Audio)"
```

GPU は必須ではありません。CPU 版 Torch でも動作しますが、Whisper は遅くなります。NVIDIA GPU があり、`uv run python -m src.main --doctor` で `nvidia_smi_available: True` かつ `torch_cuda_available: False` の場合は、まずプロジェクトの `.venv` 内だけを調整します。

この環境のように新しめの NVIDIA driver で CPU-only Torch が入っている場合は、次を試します:

```powershell
.\setup_gpu_windows.ps1 -Cuda cu128
```

別の CUDA family を試す場合:

```powershell
.\setup_gpu_windows.ps1 -Cuda cu126
.\setup_gpu_windows.ps1 -Cuda cu118
```

helper は内部で `uv pip install --upgrade torch --index-url https://download.pytorch.org/whl/<cuda-family>` を実行し、最後に `.venv\Scripts\python.exe` で確認します。CUDA 版 Torch を入れた直後に通常の `uv run` を使うと、ロックファイル基準の同期で CPU 版 Torch に戻ることがあります。確認には次のどちらかを使ってください。

```powershell
.\.venv\Scripts\python.exe -m src.main --doctor
uv run --no-sync python -m src.main --doctor
```

最新の対応 CUDA family は PyTorch の公式 selector (`https://pytorch.org/get-started/locally/`) も確認してください。システムの NVIDIA driver を先に変えるより、まず `uv run python -m src.main --doctor` と `uv run python -m src.main --show-torch-pin-plan` で状態を見てください。

## Repository stance

- このリポジトリは現時点では `~/projects/ai_core` に置く前提です
- `~/dev` に移すのは、複数プロジェクトから参照する共通基盤へ育った段階で再検討します
- いまは「AI 基盤そのもの」より「AI 入力と handoff を育てる開発・実験本体」として扱います

## Runtime notes

- GPU 設定後は `torch` の version に `+cu...` が付き、`torch.cuda.is_available() == True` になることを確認します
- GPU 利用は PyTorch の CUDA 対応ビルドと NVIDIA ドライバが正しく揃っていることが前提です
- `pyproject.toml` では Torch の CUDA バリアントを固定していないため、別マシンや通常の `uv sync` 後は CPU 版 Torch が入る可能性があります
- CPU 版 Torch が入った場合でも CLI は動作しますが、Whisper は CPU fallback で遅くなります
- CUDA デバイスが一時的に busy / unavailable の場合も、モデル読み込み時は CPU fallback を試みます

## Web UI

ブラウザ GUI を起動:

```bash
uv run python -m src.web.app
```

Windows では:

```powershell
.\start_web.ps1
```

起動後に `http://127.0.0.1:8000` を開きます。

- maintenance UI として、ファイルアップロードとブラウザ録音を扱えます
- `指示草案を優先して返す` で transcript ではなく instruction を主に返せます
- `handoff payload を保存する` で `.cache/codex/web_latest.json` と `.cache/codex/web_latest.txt` に保存します
- 単体起動時は `入力ゲートで録音を制御する` や `handoff を保存する` は手動で有効化します

統合システムやバッチ起動では、Web UI の初期値だけを外から指定できます。
`integration` プリセットは `入力ゲートで録音を制御する`、アップロード/ブラウザ録音の `handoff を保存する` を起動時に有効化します。
モジュール単体の既定値は変えません。

```powershell
.\start_web.ps1 -Preset integration
.\start_web.ps1 -Preset integration -Query "no_persist=1"
```

```bash
AI_TALK_CORE_WEB_PRESET=integration uv run python -m src.web.app
```

外部 adapter / watcher が状態 API や入力ゲート API を直接呼ぶ場合は、起動時に固定 token を渡してください。
未指定の場合はプロセスごとにランダム token が生成され、ブラウザ UI だけが利用します。

```powershell
$env:AI_TALK_CORE_WEB_TOKEN = "local-dev-token"
.\start_web.ps1 -Preset integration
```

```bash
AI_TALK_CORE_WEB_TOKEN=local-dev-token AI_TALK_CORE_WEB_PRESET=integration uv run python -m src.web.app
```

URL で直接指定する場合:

```text
http://127.0.0.1:8000/?profile=integration&no_persist=1
```

補足:

- `profile=integration`: 統合起動向けの初期値を適用
- `save_handoff=1`: アップロード/ブラウザ録音の handoff 保存を同時に有効化
- `input_gate=1` または `gate_auto=1`: ブラウザ録音を入力ゲート制御にする
- `reset_options=1`: ブラウザの保存済み UI 設定を消してから適用
- `no_persist=1`: 今回の起動で UI 設定を localStorage に保存しない
- `profile=dify` は互換 alias です。新しい連携では `integration` を使ってください

## API / CLI Setup

Python 依存を同期:

```bash
uv sync
```

Ubuntu のシステム依存を入れる:

```bash
sudo apt update
sudo apt install -y ffmpeg alsa-utils
```

smoke test 実行:

```bash
uv run python smoke_test.py
```

補足:

- `smoke_test.py` は CLI / Web UI / JSON API のサーバー側動作を確認します
- ブラウザ録音の 2 回連続実行は実ブラウザ依存なので、別途手動確認が必要です

JSON API 例:

```bash
curl -X POST http://127.0.0.1:8000/api/transcribe-upload \
  -F "audio_file=@data/sample_audio.mp3" \
  -F "model=small" \
  -F "language=ja"
```

応答 JSON には `transcript` に加えて `command` が含まれます。

`instruction_only=true` を送ると、`transcript` を空にして `command` を主に返せます。互換のため `command_only=true` も引き続き使えます。

```bash
curl -X POST http://127.0.0.1:8000/api/transcribe-upload \
  -F "audio_file=@data/sample_audio.mp3" \
  -F "model=small" \
  -F "language=ja" \
  -F "instruction_only=true"
```

`save_handoff=true` を送ると、プロジェクト内 `.cache/codex/web_latest.json` と `.cache/codex/web_latest.txt` に handoff を保存し、応答 JSON に `command_path` と `command_text_path` を返します。互換のため `save_command=true` も引き続き使えます。

保存済み handoff を取得:

```bash
curl -H "X-AI-Core-Token: <AI_TALK_CORE_WEB_TOKEN or page data-api-token value>" \
  http://127.0.0.1:8000/api/agent-handoff-latest?source=web
```

応答には `handoff_id`, `updated_at`, `metadata` も含まれます。
外部 watcher はファイルの存在確認だけでなく、この ID と更新時刻を使って最新 handoff の変化を見られます。

起動状態を確認:

```bash
curl -H "X-AI-Core-Token: <AI_TALK_CORE_WEB_TOKEN or page data-api-token value>" \
  http://127.0.0.1:8000/api/health
curl -H "X-AI-Core-Token: <AI_TALK_CORE_WEB_TOKEN or page data-api-token value>" \
  http://127.0.0.1:8000/api/status
```

`/api/health` と `/api/status` は同じ形で、`server.active_transcriptions`, `server.shutdown_requested`, `stt.ffmpeg_available`, `stt.ffprobe_available`, `input_gate`, `latest_handoff` を返します。

外部 adapter から入力ゲートを更新:

```bash
curl -X POST http://127.0.0.1:8000/api/input-gate \
  -H "X-AI-Core-Token: <AI_TALK_CORE_WEB_TOKEN or page data-api-token value>" \
  -H "Content-Type: application/json" \
  -d '{"input_enabled": true, "reason": "sword_sign", "source": "sword_voice_agent"}'
```

Web UI のブラウザ録音で `入力ゲートで録音を制御する` を有効にすると、
`/api/input-gate` の `input_enabled=true` で録音開始、`false` で録音停止とアップロード処理に進みます。
このモードでは誤操作を避けるため、手動の `録音開始` ボタンは無効になります。

ローカル Web サーバーの停止要求:

```bash
curl -X POST http://127.0.0.1:8000/api/shutdown \
  -H "X-AI-Core-Token: <AI_TALK_CORE_WEB_TOKEN or page data-api-token value>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "batch finished"}'
```

`/api/doctor`, `/api/health`, `/api/status`, `/api/input-gate`, `/api/*-handoff-latest`, `/api/shutdown` はローカル UI の per-process token が必要です。
進行中の転写がある場合は新規転写を受け付けず、処理完了後に停止へ進みます。
すぐ停止したい場合は `{"force": true}` を渡せますが、Whisper/Torch の実行中処理そのものを安全に中断するものではありません。

ローカル CLI から最新 handoff を読む:

```bash
uv run python -m src.agent_handoff --source web --format prompt
```

任意コマンドの stdin に最新 handoff を渡す:

```bash
uv run python -m src.agent_runner --source web -- python -c "import sys; print(sys.stdin.read())"
```

組み込みテンプレートを使う:

```bash
uv run python -m src.agent_runner --source web --template cat
```

Codex CLI にそのまま渡す:

```bash
uv run python -m src.agent_runner --source web --template codex-exec
```

このテンプレートは `codex` コマンドが `PATH` にある前提です。見つからない場合は実行前に入力エラーを返します。

## Quick Start

```bash
uv run python -m src.main data/sample_audio.mp3 --language ja
```

```bash
uv run python -m src.main --mic --duration 5 --language ja
```

```bash
uv run python -m src.main --mic-loop --duration 3 --language ja
```

入力ゲートの状態を確認:

```bash
uv run python -m src.main --show-input-gate --input-gate-format json
```

`Ctrl+C` で停止した場合も、直前の安定した発話は `final` として 1 回だけ flush を試みます。
また、十分に長い同一発話は 2 回連続でも `final` に寄せます。短い断片は引き続き厳しめです。
必要なら `--mic-profile responsive|balanced|strict` で mic-loop の調整プリセットを切り替えられます。
さらに細かく詰めたい場合は `--vad-aggressiveness 0..3` で WebRTC VAD のしきい値を上書きできます。
中くらい以上の発話は安定時間が十分長ければ `final` に寄せます。
この安定時間は `--final-stable-seconds` で上書きできます。
ただし、時間条件だけで単発チャンクを即 `final` にすることは避け、最低限の反復を前提にしています。
これらの `final` ヒューリスティクスは `src/core/finalization.py` に切り出し、CLI 本体から分離しています。
`--mic-loop` の開始時には、実際に使われる profile / VAD / final しきい値を `[mic-tuning] ...` として stderr に表示します。`--instruction-only` や handoff 用の stdout は汚さないようにしています。
`--input-disabled` を付けると mic-loop は capture を開始せず、入力ゲートが開くまで待つ前提の状態になります。現時点の CLI では手動確認用で、実運用では gesture / WebSocket / keyboard などの adapter が `input_enabled` を更新する composition root から使います。

転写結果と指示草案を同時に表示:

```bash
uv run python -m src.main --mic --duration 5 --language ja --emit-instruction
```

指示草案だけ表示:

```bash
uv run python -m src.main --mic --duration 5 --language ja --instruction-only
```

handoff payload を JSON 保存:

```bash
uv run python -m src.main --mic --duration 5 --language ja --handoff-output .cache/codex/latest.json
```

このとき `.txt` 版の prompt も同じ場所に自動生成します。中身は `Voice transcript` と `Requested task` を含む、そのまま外部エージェントへ渡しやすい形式です。

Web UI でも、アップロード欄とブラウザ録音欄の `指示草案を優先して返す` を有効にすると `command_only` と同じ挙動になります。
`handoff payload を保存する` を有効にすると、同じ handoff を `.cache/codex/web_latest.json` と `.cache/codex/web_latest.txt` に保存します。

このマシンでは `--mic-device` を省略した場合、`arecord -l` で見つかった最初の入力デバイスを優先します。

## Usage

基本実行:

```bash
uv run python -m src.main /path/to/audio.wav
```

言語指定:

```bash
uv run python -m src.main /path/to/audio.wav --language ja
```

モデル変更:

```bash
uv run python -m src.main /path/to/audio.wav --model base
```

マイク録音:

```bash
uv run python -m src.main --mic --duration 5 --language ja
```

マイクループ:

```bash
uv run python -m src.main --mic-loop --duration 3 --language ja
```

入力ゲートを閉じた状態で mic-loop を開始:

```bash
uv run python -m src.main --mic-loop --input-disabled --input-gate-reason sword_sign
```

VAD の強さを変える:

```bash
uv run python -m src.main --mic-loop --duration 3 --language ja --vad-aggressiveness 3
```

mic-loop の調整プリセットを切り替える:

```bash
uv run python -m src.main --mic-loop --duration 3 --language ja --mic-profile strict
```

一覧だけ確認する:

```bash
uv run python -m src.main --list-mic-profiles
```

JSON で取り出す:

```bash
uv run python -m src.main --list-mic-profiles --mic-tuning-format json
```

現在の profile と override から解決される tuning 値だけ確認する:

```bash
uv run python -m src.main --show-mic-tuning --mic-profile responsive --vad-aggressiveness 3 --final-stable-seconds 9
```

JSON で取り出す:

```bash
uv run python -m src.main --show-mic-tuning --mic-profile balanced --mic-tuning-format json
```

Whisper / Torch / ffmpeg の runtime 状態を確認する:

```bash
uv run python -m src.main --show-runtime-status
```

JSON で取り出す:

```bash
uv run python -m src.main --show-runtime-status --runtime-status-format json
```

この出力には `nvidia_smi_available`, `nvidia_driver_version`, `nvidia_gpu_name`, `transcription_device`, `runtime_note`, `suggested_action` も含まれ、driver 側と Torch 側の食い違い、および GPU が使えないときの CPU fallback を読み取りやすくします。`nvidia-smi` は見えるのに `torch_cuda_available` が `False` の場合は、`runtime_note` に Torch/driver CUDA mismatch の疑い、`suggested_action` に project-local な次の一手を出します。

依存の解決状態を確認する:

```bash
uv run python -m src.main --show-dependency-status
```

JSON で取り出す:

```bash
uv run python -m src.main --show-dependency-status --dependency-status-format json
```

この出力では、`pyproject.toml` に `torch` が直接書かれているか、現在の `torch` が `openai-whisper` 経由の transitive dependency かを確認できます。

runtime と dependency をまとめて確認する:

```bash
uv run python -m src.main --doctor
```

JSON で取り出す:

```bash
uv run python -m src.main --doctor --doctor-format json
```

project-local な Torch pin 方針を確認する:

```bash
uv run python -m src.main --show-torch-pin-plan
```

JSON で取り出す:

```bash
uv run python -m src.main --show-torch-pin-plan --torch-pin-plan-format json
```

`torch.cuda.is_available() == False` かつ `nvidia-smi` が見えている場合は、まず system driver を触る前に `.venv` 内の Torch pin 方針を確認してください。
また、現在の Torch に `+cu128` のような build suffix が付いている場合は、単なる version pin ではなく build/source の選択まで必要になることがあります。
plan 出力には `pyproject_dependency_entry` と `uv_add_command` も含まれるので、次に `pyproject.toml` へ何を足すかの叩き台として使えます。

`final` に寄せる安定時間を変える:

```bash
uv run python -m src.main --mic-loop --duration 3 --language ja --final-stable-seconds 6
```

2 回だけループして確認:

```bash
uv run python -m src.main --mic-loop --duration 3 --iterations 2 --language ja
```

マイクデバイス指定:

```bash
uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja
```

無音トリムを無効化:

```bash
uv run python -m src.main --mic --duration 5 --no-trim-silence --language ja
```

サンプル音声:

```bash
uv run python -m src.main data/sample_audio.mp3 --language ja
```

手元で録音した wav を文字起こし:

```bash
uv run python -m src.main data/mic_speech_test_c920_retry.wav --language ja
```

## Directory structure

```text
ai_core/
├── data/                # 入力音声サンプル
├── models/whisper/      # Whisper モデル保存先
├── src/core/pipeline.py # capture -> buffer -> transcribe の共通経路
├── src/main.py          # CLI エントリポイント
├── src/io/audio.py      # 音声文字起こし
├── src/io/microphone.py # 固定時間マイク録音
├── src/web/app.py       # ローカル Web UI
├── MEMORY.md            # 長期前提・設計判断
├── REVIEW.md            # レビュー結果
├── REVIEWER_INSTRUCTIONS.md # レビュアー向け記録ルール
├── SHARE_NOTE.md        # 共有用の現在地メモ
└── LOG.md               # 実行履歴
```

Whisper のモデルは `models/whisper` に保存されます。

## 入出力

- 入力: ローカル音声ファイル、固定時間のマイク録音、または簡易マイクループ
- 対応拡張子: `.mp3`, `.wav`, `.m4a`, `.mp4`, `.mpeg`, `.mpga`, `.webm`
- 出力: 文字起こし結果を標準出力へ表示
- `--emit-command` / `--emit-instruction` 使用時は指示草案も標準出力へ表示
- `--command-only` / `--instruction-only` 使用時は転写本文を省いて指示草案だけを表示
- `--command-output` / `--handoff-output` 使用時は `{"transcript": "...", "command": "..."}` の JSON を保存
- 既定モデル: `small`

## Model storage

- Whisper のモデルは `models/whisper` に保存されます
- モデルファイルは容量が大きいため、VCS 管理対象外にします
- プロジェクトごとにモデルを持つ方針なので、複数プロジェクトで Whisper を使うと保存容量は重複します
- 既定モデルは `small` です。初回転写時に自動取得されます
- 事前に取得する場合は次を実行します:

```bash
uv run python -c "import whisper; whisper.load_model('small', download_root='models/whisper')"
```

別モデルを使う場合は `--model base` などを指定します。指定したモデルも初回利用時に同じ場所へ取得されます。

## サンプル結果

入力:
- `data/sample_audio.mp3`

出力例:

```text
こんにちは、温度区さんです。 より自然で、より人間らしい声になりました。
```

マイク録音テストでは文字起こしパイプライン自体は成功していますが、結果の安定化には前処理が必要です。

## Notes / limitations

- 初回実行時は Whisper モデルを `models/whisper/` にダウンロードします
- GPU が使える環境では CUDA を利用します
- GPU が使えない場合は CPU 実行になり、転写は遅くなる場合があります
- `ffmpeg` が無い環境では文字起こしに失敗します
- マイク録音には `arecord` が必要です。Ubuntu では `alsa-utils` に含まれます
- マイク入力は固定時間録音の反復であり、真のストリーミング処理ではありません
- 録音音声は `ffmpeg` の `silenceremove` で軽く前後トリムできます
- `--mic-loop` では `webrtcvad` でほぼ無音のチャンクを軽くスキップします
- 無音チャンクは CLI では `[silence N] silence detected` と表示します
- `AudioBuffer` は入っていますが、`buffer -> partial/final` の扱いはまだ未実装です
- `--mic-loop` では通常チャンクを `partial` として表示し、有限ループの最後または同一結果の連続時に `final` へ寄せます
- 短すぎる断片は `partial` のままにして、誤認識を `final` に寄せにくくしています
- 同じ結果がある程度安定したあとに無音チャンクが来た場合は、その直前の発話を `final` として扱います
- `final` へ寄せるには、同じ結果が複数回連続する必要があります
- 発話区間検出としての VAD は未実装です
- ブラウザ録音の連続実行は smoke test では拾えないため、実ブラウザでの確認が必要です

ここでいう VAD 未実装は「本格的な発話区間検出パイプラインが未実装」という意味です。軽量な `webrtcvad` ベースの speech detection は `mic-loop` ですでに使っています。

## Compatibility notes

主導線は `agent_*` ですが、互換のため `codex_*` 入口も残しています。

- handoff reader の主導線: `src.agent_handoff`
- runner の主導線: `src.agent_runner`
- 互換入口: `src.codex_handoff`, `src.codex_runner`, `/api/codex-handoff-latest`

既存の `src/core/codex_bridge.py`, `src/core/llm.py`, `src/runners/codex.py` も互換のため残していますが、新しい構成では `src/core/handoff_bridge.py`, `src/core/agent_instruction.py`, `src/runners/agent.py` を参照します。

## Architecture

```mermaid
flowchart LR
    CLI["CLI\nsrc/main.py"]
    WEB["Web UI / JSON API\nsrc/web/app.py"]
    WEBSERVICE["Web transcription service\nsrc/web/transcription_service.py"]
    SESSION["Session\nsrc/core/session.py"]
    PIPE["Pipeline\nsrc/core/pipeline.py"]
    MIC["Microphone I/O\nsrc/io/microphone.py"]
    AUDIO["Audio I/O\nsrc/io/audio.py"]
    DRAFT["Command Draft\nsrc/core/agent_instruction.py"]
    BRIDGE["Handoff Bridge\nsrc/core/handoff_bridge.py"]
    HANDOFF["Handoff Reader\nsrc.agent_handoff / src.codex_handoff"]
    RUNNER["Runner\nsrc.agent_runner / src.codex_runner.py"]
    RUNNER_IMPL["Runner impls\nsrc/runners/*"]
    WHISPER["Whisper"]

    CLI --> SESSION
    CLI --> PIPE
    CLI --> MIC
    WEB --> WEBSERVICE
    WEBSERVICE --> PIPE
    SESSION --> PIPE
    PIPE --> AUDIO
    PIPE --> WHISPER
    CLI --> DRAFT
    WEBSERVICE --> DRAFT
    DRAFT --> BRIDGE
    CLI --> BRIDGE
    WEBSERVICE --> BRIDGE
    BRIDGE --> HANDOFF
    HANDOFF --> RUNNER
    RUNNER --> RUNNER_IMPL
```

### Mic-loop Flow

```mermaid
flowchart LR
    GATE["input gate"]
    CAPTURE["capture chunk"]
    SKIP["skip capture"]
    VAD["webrtcvad speech detection"]
    SESSION["session state"]
    TRANSCRIBE["Whisper transcribe"]
    RESULT["partial / final heuristic"]
    COMMAND["instruction draft"]

    GATE -->|enabled| CAPTURE
    GATE -->|disabled| SKIP
    CAPTURE --> VAD
    VAD -->|speech| SESSION
    VAD -->|silence| SESSION
    SESSION --> TRANSCRIBE
    SESSION --> RESULT
    TRANSCRIBE --> RESULT
    RESULT --> COMMAND
```

### Agent Handoff Flow

```mermaid
flowchart LR
    TRANSCRIBE["transcription result"]
    DRAFT["command draft"]
    SAVE["handoff save\njson + txt"]
    API["/api/agent-handoff-latest\n/api/codex-handoff-latest"]
    CLI["src.agent_handoff\nsrc.codex_handoff"]
    RUNNER["src.agent_runner / src.codex_runner"]
    TARGET["target command / agent-side process"]

    TRANSCRIBE --> DRAFT
    DRAFT --> SAVE
    SAVE --> API
    SAVE --> CLI
    CLI --> RUNNER
    RUNNER --> TARGET
```

## Manual checks

- Web UI でブラウザ録音を 2 回連続で実行する
- 1 回目の録音後に `録音開始` が再び押せることを確認する
- 2 回目の録音後も結果更新とエラー表示が正常に動くことを確認する
- `Recorder Debug` に `state`, `chunks`, `lastBlobSize` が妥当な値で出ることを確認する

## Troubleshooting

エラー種別:

- `Input error`: ファイルパス、拡張子、モデル名、CLI 引数の入力不備
- `Environment error`: `ffmpeg` / `arecord` 不在、モデルロード失敗、無音トリム失敗、CUDA 実行環境不備
- `Transcription error`: Whisper 実行中の失敗

- `Input error: audio file not found`
  指定したファイルパスを確認してください
- `Input error: unsupported audio file extension`
  対応拡張子のファイルを使用してください
- `Input error: invalid Whisper model name`
  `small`, `base` など有効なモデル名を指定してください
- `Environment error: ffmpeg is not installed or not found in PATH`
  `ffmpeg` が利用可能か確認してください
- `Environment error: arecord is not installed or not found in PATH`
  `arecord` が利用可能か確認してください
- `Environment error: failed to list microphone devices: ...`
  `arecord -l` が成功するか確認してください
- `Environment error: microphone recording failed: ...`
  デバイス名やマイク接続状態を確認してください
- `Environment error: microphone recording timed out`
  `ffmpeg-dshow` / `arecord` が戻らない状態です。マイクデバイス名、OS の録音権限、別アプリによる占有を確認してください
- `Environment error: silence trimming failed: ...`
  `ffmpeg` が利用可能か、入力 wav が壊れていないか確認してください
- Web UI 終了時に固まる場合
  `X-AI-Core-Token` 付きで `/api/status` の `server.active_transcriptions` を確認してください。Whisper 実行中は停止要求が完了まで待つことがあります。今回の Web UI は新規転写を止め、録音/トリム系 subprocess にはタイムアウトを設定しています。
- `Environment error: failed to load Whisper model ...`
  モデル取得や CUDA 実行環境を確認してください
- `Ctrl+C`
  `--mic-loop` の停止に使用します
- GPU が使えない環境では CPU fallback で遅くなる場合があります
- `uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.version.cuda)"`
  で現在の Torch / CUDA 状態を確認できます

## Recording files

- `MEMORY.md`: 長期的に残す前提、設計方針、運用ルール
- `REVIEW.md`: レビュアーの所見、懸念点、改善提案
- `REVIEWER_INSTRUCTIONS.md`: レビュアーへ渡す記録ルール
- `SHARE_NOTE.md`: 現在の状況、次の作業、引き継ぎ事項
- `LOG.md`: 実行コマンド、結果、失敗、確認日時

## 今後の予定

- 出力確定方針の整理
- VAD
- ノイズ対策
- 真のリアルタイム処理
