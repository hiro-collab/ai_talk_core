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

Status: partially adopted

#### Findings

- Medium: 初見の人にとって README の機能境界がまだ掴みにくい。対象: `README.md:3-13`, `README.md:181-190`。冒頭では `file input`, `mic`, `mic-loop`, 無音トリムまで一気に出てくる一方、制約欄には「現状はローカル音声ファイルのみ対応しています」が残っており、何が実装済みかを誤解しやすい。
- Medium: `README.md:132-135` のエラー種別説明が重複しており、初見ではどちらが正なのか判断しづらい。`Environment error` が 2 行あり、後者だけが無音トリム失敗を含んでいる。
- Medium: `src/main.py:138-139` の入力エラーメッセージが現状と少しずれている。現在は `--mic-loop` もあるが、表示は `audio_file is required unless --mic is used` のままで、CLI の使い方を学ぶ助けになっていない。
- Low-Medium: `--mic-loop --iterations 0` が入力エラーにならず、そのまま終了コード 0 で即終了する。対象: `src/main.py:33`, `src/main.py:115-126`。反復回数を指定できる CLI としては、0 以下は無効値として弾く方が自然。
- Low: `smoke_test.py` は成功系・主要失敗系を押さえているが、`--mic`, `--mic-loop`, `--iterations`, `--no-trim-silence` の検証を含んでいない。README の説明が増えた分、初見ユーザー向けの回帰防止としては追従不足。
- Low: `src/io/microphone.py:42-50` のデフォルトマイク選択は `HD Pro Webcam C920` という機種名文字列に依存しており、この PC では妥当でも汎用実装ではない。README には記載済みだが、PC 固有ロジックとして扱う必要がある。

#### Open questions / assumptions

- `--mic-loop` は擬似リアルタイムの実験用途であり、現時点では partial / final の出し分けや重複抑制は未要件と仮定した
- 固定時間マイク入力と `--mic-loop` はローカル単発 CLI 向けの最小実装であり、録音ファイル履歴や並列実行は現時点で要件外と仮定した
- `HD Pro Webcam C920` 優先は、この PC 専用の暫定仕様として意図的に入れている前提で見た
- README は「知らない人向けの最初の入口」も兼ねる想定で見た

#### Recommended next actions

- 1. README 冒頭に「今できること / まだできないこと」を 2-3 行で明示し、制約欄の古い文言を削除する
- 2. エラー種別説明を 1 セットに整理し、無音トリム失敗は `Environment error` の説明へ統合する
- 3. 引数未指定時のメッセージを `audio_file is required unless --mic or --mic-loop is used` のように現状へ合わせる
- 4. `--iterations` に 1 以上のバリデーションを追加する
- 5. `smoke_test.py` に `--iterations` の失敗系、`--mic-loop` の最小検証、`--no-trim-silence` の引数受理確認を追加する
- 6. リアルタイム化の次段階として、`capture -> buffer -> transcribe` の分離を作る
- 7. ノイズ対策は denoise より先に VAD / 無音トリムから入る

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

- `buffer -> partial/final` のリアルタイム用 API 境界は未実装
- VAD は未実装
