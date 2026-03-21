# Review Notes

## Purpose

- レビュアーの所見を集約する
- Findings, open questions, 改善提案を残す
- 実装担当との合意前の観点も保持する

## Writing rules

- Findings を重大度順に書く
- 可能なら対象ファイルや箇所を明記する
- 実行事実は `LOG.md` に重複転記しない
- 長期前提として確定した内容だけ `MEMORY.md` へ反映する
- 合意済みの次アクションだけ `SHARE_NOTE.md` へ反映する

## Review entries

### 2026-03-21

Status: adopted with open follow-ups

#### Findings

- Low: `src/io/microphone.py:42-50` のデフォルトマイク選択は `HD Pro Webcam C920` という機種名文字列に依存しており、この PC では妥当でも汎用実装ではない。README には記載済みだが、PC 固有ロジックとして扱う必要がある。

#### Open questions / assumptions

- `--mic-loop` は擬似リアルタイムの実験用途であり、現時点では partial / final の出し分けや重複抑制は未要件と仮定した
- 固定時間マイク入力と `--mic-loop` はローカル単発 CLI 向けの最小実装であり、録音ファイル履歴や並列実行は現時点で要件外と仮定した
- `HD Pro Webcam C920` 優先は、この PC 専用の暫定仕様として意図的に入れている前提で見た
- README は「知らない人向けの最初の入口」も兼ねる想定で見た

#### Recommended next actions

- 1. リアルタイム化の次段階として、`buffer -> partial/final` の API 境界を作る
- 2. ノイズ対策は denoise より先に VAD から入る

#### Realtime direction

- Step 1: 固定秒数録音を 0.5-1 秒程度の短いチャンク取得へ置き換える
- Step 2: 録音、バッファ管理、Whisper 呼び出しを分離する
- Step 3: partial result と final result を分ける
- Step 4: VAD を追加して無音区間の推論を減らす
- Step 5: 必要になった時点で軽い前処理を追加し、それでも不足するなら denoise を検討する

#### Adopted

- `src/main.py` で入力ファイル検証、モデル名検証、`ffmpeg` 確認をモデルロード前に実施
- `src/io/audio.py` で不正モデル名を `Input error` に分類するよう修正
- `src/io/microphone.py` を追加し、録音処理を音声文字起こし処理から分離
- `src/core/pipeline.py` を追加し、CLI と Web UI で共通の capture -> transcribe 経路を共有
- `src/core/pipeline.py` に `AudioBuffer` を追加し、`mic-loop` を `capture -> buffer -> transcribe` に寄せた
- `--mic --duration` による固定時間マイク録音 CLI を追加
- `--mic-loop` と `--iterations` による擬似リアルタイムの反復 CLI を追加
- `--no-trim-silence` による軽い無音トリムの ON/OFF 切替を追加
- `HD Pro Webcam C920` を優先するデフォルトマイク選択を追加
- README に CUDA / CPU fallback の runtime note を追加
- README にモデル保存方針の注意点を追加
- README 冒頭に「今できること / まだできないこと」を追加
- README のエラー種別説明を 1 セットに整理
- 引数未指定時のメッセージを `--mic-loop` に対応させた
- `--iterations` の 0 以下バリデーションを追加
- `smoke_test.py` を拡張し、`--iterations` と `--no-trim-silence` の確認を追加
- `ffmpeg` の `silenceremove` を使った軽い無音トリムを追加

#### Open

- `partial -> final` の確定条件は未実装
- VAD は未実装

#### Resolved findings

- README 冒頭に「今できること / まだできないこと」を追加し、古い制約文言を整理した
- README のエラー種別説明を 1 セットに整理した
- 引数未指定時の入力エラーメッセージを `--mic-loop` に対応させた
- `--iterations` の 0 以下バリデーションを追加した
- `smoke_test.py` を拡張し、`--iterations` と `--no-trim-silence` の確認を追加した
- `capture -> buffer -> transcribe` の最初の分離として `AudioBuffer` を追加した
- Web UI を `document.write()` ベースの全画面差し替えから、結果領域だけを更新する fetch ベースに改善した
- `TranscriptionResult` を追加し、`mic-loop` が `partial` 扱いの結果モデルを返す形に寄った

#### Side review

- `src/core/pipeline.py` を介して CLI と Web UI が共通経路へ寄った点は妥当。連携用システムを中心に据える方向として筋が良い。
- `src/web/app.py` のブラウザ録音 UI は、結果領域だけ更新する fetch ベースに変わり、録音中・処理中の状態が見やすくなった。
- README は初見ユーザー向けにかなり改善されており、`今できること / まだできないこと` と `capture -> buffer -> transcribe` の説明は有効。現状理解の補助として十分機能している。
- 全体評価としては、`保守 GUI としては妥当、他システム連携の本命としては次に API 境界が必要` という段階。
