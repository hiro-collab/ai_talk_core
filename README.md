# ai_core

Whisper を使ってローカル音声ファイルを文字起こしする最小構成です。
現在は `file input -> Whisper -> text` と、固定時間の `mic -> Whisper -> text` を対象にしています。

## Overview

- ローカル音声ファイルを入力し、Whisper で文字起こしします
- 固定時間のマイク録音から文字起こしする最小 CLI も使えます
- `HD Pro Webcam C920` で録音自体は確認済みです
- 常時動作のマイク入力 CLI とノイズ対策は未実装です

## Requirements

- Ubuntu 22.04
- Python 3.11.15
- 仮想環境は `.venv` を使用
- パッケージ管理は `uv` を使用
- `ffmpeg` がシステムに導入済みであること
- GPU は任意です
- 現在の開発環境では CUDA 利用を確認済みです

## Setup

依存同期:

```bash
uv sync
```

## Quick start

サンプル音声を文字起こし:

```bash
uv run python -m src.main data/sample_audio.mp3 --language ja
```

手元で録音した wav を文字起こし:

```bash
uv run python -m src.main data/mic_speech_test_c920_retry.wav --language ja
```

マイクから 5 秒録音して文字起こし:

```bash
uv run python -m src.main --mic --duration 5 --language ja
```

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

マイクデバイス指定:

```bash
uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja
```

サンプル音声:

```bash
uv run python -m src.main data/sample_audio.mp3 --language ja
```

エラー種別:

- `Input error`: ファイルパス、拡張子、モデル名などの入力不備
- `Environment error`: `ffmpeg` / `arecord` 不在、モデルロード失敗、CUDA 実行環境不備
- `Transcription error`: Whisper 実行中の失敗

## Directory structure

```text
ai_core/
├── data/                # 入力音声サンプル
├── models/whisper/      # Whisper モデル保存先
├── src/main.py          # CLI エントリポイント
├── src/io/audio.py      # 音声文字起こし
├── src/io/microphone.py # 固定時間マイク録音
├── MEMORY.md            # 長期前提・設計判断
├── REVIEW.md            # レビュー結果
├── REVIEWER_INSTRUCTIONS.md # レビュアー向け記録ルール
├── SHARE_NOTE.md        # 共有用の現在地メモ
└── LOG.md               # 実行履歴
```

Whisper のモデルは `models/whisper` に保存されます。

## 入出力

- 入力: ローカル音声ファイル、または固定時間のマイク録音
- 対応拡張子: `.mp3`, `.wav`, `.m4a`, `.mp4`, `.mpeg`, `.mpga`, `.webm`
- 出力: 文字起こし結果を標準出力へ表示
- 既定モデル: `small`

## Model storage

- Whisper のモデルは `models/whisper` に保存されます
- モデルファイルは容量が大きいため、VCS 管理対象外にします

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
- 現状はローカル音声ファイルのみ対応しています
- マイク録音は固定時間のみで、常時ストリーミングは未対応です
- 録音音声はそのまま投入しており、VAD や無音トリムは未実装です

## Troubleshooting

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
- `Environment error: failed to load Whisper model ...`
  モデル取得や CUDA 実行環境を確認してください
- GPU が使えない環境では CPU fallback で遅くなる場合があります

## Recording files

- `MEMORY.md`: 長期的に残す前提、設計方針、運用ルール
- `REVIEW.md`: レビュアーの所見、懸念点、改善提案
- `REVIEWER_INSTRUCTIONS.md`: レビュアーへ渡す記録ルール
- `SHARE_NOTE.md`: 現在の状況、次の作業、引き継ぎ事項
- `LOG.md`: 実行コマンド、結果、失敗、確認日時

## 今後の予定

- マイク入力対応
- VAD / 無音トリム
- ノイズ対策
