# ai_core

Whisper を使ってローカル音声ファイルを文字起こしする最小構成です。
現在は `file input -> Whisper -> text`、固定時間の `mic -> Whisper -> text`、および簡易ループの `mic-loop -> Whisper -> text` を対象にしています。内部の共通経路は `capture -> buffer -> transcribe` へ寄せ始めています。

## Overview

- 今できること: ファイル入力、固定時間マイク入力、簡易マイクループ、Web UI、JSON API、軽い無音トリム、Codex 指示草案出力
- まだできないこと: 真のリアルタイム streaming、`partial/final` の本格運用、VAD
- 位置づけ: GUI 主体ではなく、音声入力フロントエンド兼サービス境界を優先
- ブラウザ録音の `webm` はサーバー側で `16kHz mono wav` 相当に正規化してから転写
- Web UI の言語入力欄は既定で `ja`
- `HD Pro Webcam C920` で録音確認済み

## Requirements

- Ubuntu 22.04
- Python 3.11.15
- 仮想環境は `.venv` を使用
- パッケージ管理は `uv` を使用
- `ffmpeg` がシステムに導入済みであること
- `ffprobe` がシステムに導入済みであること
- GPU は任意です
- 現在の開発環境では CUDA 利用を確認済みです

## Runtime notes

- 現在の確認環境では `torch 2.10.0+cu128`, `torch.cuda.is_available() == True` でした
- GPU 利用は PyTorch の CUDA 対応ビルドと NVIDIA ドライバが正しく揃っていることが前提です
- `pyproject.toml` では Torch の CUDA バリアントを固定していないため、別マシンでは CPU 版 Torch が入る可能性があります
- CPU 版 Torch が入った場合でも CLI は動作しますが、Whisper は CPU fallback で遅くなります

## Setup

依存同期:

```bash
uv sync
```

smoke test 実行:

```bash
uv run python smoke_test.py
```

補足:

- `smoke_test.py` は CLI / Web UI / JSON API のサーバー側動作を確認します
- ブラウザ録音の 2 回連続実行は実ブラウザ依存なので、別途手動確認が必要です

Web UI 起動:

```bash
uv run python -m src.web.app
```

JSON API 例:

```bash
curl -X POST http://127.0.0.1:8000/api/transcribe-upload \
  -F "audio_file=@data/sample_audio.mp3" \
  -F "model=small" \
  -F "language=ja"
```

応答 JSON には `transcript` に加えて `command` が含まれます。

## Quick start

```bash
uv run python -m src.main data/sample_audio.mp3 --language ja
```

```bash
uv run python -m src.main --mic --duration 5 --language ja
```

```bash
uv run python -m src.main --mic-loop --duration 3 --language ja
```

転写結果と Codex 用の指示草案を同時に表示:

```bash
uv run python -m src.main --mic --duration 5 --language ja --emit-command
```

ブラウザ GUI を起動:

```bash
uv run python -m src.web.app
```

起動後に `http://127.0.0.1:8000` を開きます。

このマシンでは `--mic-device` を省略した場合、`HD Pro Webcam C920` が見つかれば自動的に優先されます。

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
- `--emit-command` 使用時は Codex 用の指示草案も標準出力へ表示
- 既定モデル: `small`

## Model storage

- Whisper のモデルは `models/whisper` に保存されます
- モデルファイルは容量が大きいため、VCS 管理対象外にします
- プロジェクトごとにモデルを持つ方針なので、複数プロジェクトで Whisper を使うと保存容量は重複します

## サンプル結果

入力:
- `data/sample_audio.mp3`

出力例:

```text
こんにちは、温度区さんです。 より自然で、より人間らしい声になりました。
```

マイク録音テストでは文字起こしパイプライン自体は成功していますが、結果の安定化には前処理が必要です。

## Notes / limitations

- 初回実行時は Whisper モデルをダウンロードします
- GPU が使える環境では CUDA を利用します
- GPU が使えない場合は CPU 実行になります
- `ffmpeg` が無い環境では文字起こしに失敗します
- マイク入力は固定時間録音の反復であり、真のストリーミング処理ではありません
- 録音音声は `ffmpeg` の `silenceremove` で軽く前後トリムできます
- `--mic-loop` では `ffmpeg` の `silencedetect` でほぼ無音のチャンクを軽くスキップします
- 無音チャンクは CLI では `[silence N] silence detected` と表示します
- `AudioBuffer` は入っていますが、`buffer -> partial/final` の扱いはまだ未実装です
- `--mic-loop` では通常チャンクを `partial` として表示し、有限ループの最後または同一結果の連続時に `final` へ寄せます
- 発話区間検出としての VAD は未実装です
- ブラウザ録音の連続実行は smoke test では拾えないため、実ブラウザでの確認が必要です

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
- `Environment error: ffprobe is not installed or not found in PATH`
  `ffprobe` が利用可能か確認してください
- `Environment error: arecord is not installed or not found in PATH`
  `arecord` が利用可能か確認してください
- `Environment error: failed to list microphone devices: ...`
  `arecord -l` が成功するか確認してください
- `Environment error: microphone recording failed: ...`
  デバイス名やマイク接続状態を確認してください
- `Environment error: silence trimming failed: ...`
  `ffmpeg` が利用可能か、入力 wav が壊れていないか確認してください
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
