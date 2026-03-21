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

- Medium: `src/io/microphone.py` の無音検出は `ffprobe` を前提にしているが、事前チェックが `ffmpeg` と `arecord` のみで、`ffprobe` 不在時の早期検出がない。`--mic-loop` だけ別マシンで落ちる経路として残っている。
- Low-Medium: `src/main.py` の無音チャンクは空文字の `TranscriptionResult` として表示されるため、`[partial N] ` が「意図した無音スキップ」なのか「認識失敗」なのか区別しづらい。
- Low: `src/io/microphone.py:42-50` のデフォルトマイク選択は `HD Pro Webcam C920` という機種名文字列に依存しており、この PC では妥当でも汎用実装ではない。README には記載済みだが、PC 固有ロジックとして扱う必要がある。

#### Open questions / assumptions

- `--mic-loop` は擬似リアルタイムの実験用途であり、現時点では partial / final の出し分けや重複抑制は未要件と仮定した
- 固定時間マイク入力と `--mic-loop` はローカル単発 CLI 向けの最小実装であり、録音ファイル履歴や並列実行は現時点で要件外と仮定した
- `HD Pro Webcam C920` 優先は、この PC 専用の暫定仕様として意図的に入れている前提で見た
- README は「知らない人向けの最初の入口」も兼ねる想定で見た

#### Recommended next actions

- 1. `ffprobe` 依存の事前チェックを追加し、`--mic-loop` の環境エラーを早期に分かる形へ寄せる
- 2. 無音チャンク時の CLI / Web UI 表示を明確化し、無音スキップと認識失敗を区別できるようにする
- 3. `partial/final` は暫定ヒューリスティクス段階なので、より実用的な確定条件へ進める
- 4. 軽い無音スキップの次段として、本格的な VAD を導入する
- 5. 将来の他システム連携に備え、CLI / Web UI の上に外部連携 API を置けるサービス境界を維持する

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
- `TranscriptionResult` による `partial/final` の暫定結果モデルを追加
- 有限ループ最終回に加え、同一結果の連続時も `final` に寄せる暫定ヒューリスティクスを追加
- `ffprobe` / `ffmpeg silencedetect` を使った軽い無音スキップを `--mic-loop` に追加
- Web UI の転写本体処理を共通化し、fetch 先を `/api/...` に統一
- `/api/transcribe-browser-recording` のサーバーテストを追加
- `Recorder Debug` と `requestData()` 除去を含むブラウザ録音の状態改善を追加
- ブラウザ録音の `webm` を `16kHz mono wav` 相当に正規化してから転写するよう変更
- ブラウザ録音の 2 回連続実行は実機で成功を確認
- README の `Overview` / `Quick start` の重複を圧縮

#### Open

- `partial -> final` は暫定ヒューリスティクス段階で、本格的な確定条件は未完了
- VAD は未実装
- `ffprobe` 依存の事前チェックがない
- 無音チャンク時の CLI / Web UI 表示が分かりにくい

#### Resolved findings

- README 冒頭に「今できること / まだできないこと」を追加し、古い制約文言を整理した
- README のエラー種別説明を 1 セットに整理した
- 引数未指定時の入力エラーメッセージを `--mic-loop` に対応させた
- `--iterations` の 0 以下バリデーションを追加した
- `smoke_test.py` を拡張し、`--iterations` と `--no-trim-silence` の確認を追加した
- `capture -> buffer -> transcribe` の最初の分離として `AudioBuffer` を追加した
- Web UI を `document.write()` ベースの全画面差し替えから、結果領域だけを更新する fetch ベースに改善した
- ブラウザ録音では `MediaRecorder` と stream の明示リセットを追加した
- `TranscriptionResult` を追加し、`mic-loop` が `partial` 扱いの結果モデルを返す形に寄った

#### Future direction note

- 現状の進捗は、`音声を取ってテキスト化する基盤` としては順調。ファイル入力、固定時間マイク入力、擬似リアルタイム、Web UI、共通パイプラインまで揃っている。
- 一方で、`ユーザーが話した内容を Codex などへ渡す` ところまではまだ前段で、会話入力フロントエンドとして完成させるには `VAD`, `partial/final`, 外部連携 API の3点が必要。
- 方針としては、GUI を主役にするより `他システム連携用のサービス` を中心に据え、GUI は保守用の薄い面として扱うのが妥当。

#### Side review

- README は機能一覧としては十分だが、CLI / Web UI / JSON API / pipeline / io 層の関係が文章だけでは追いにくい。初見の人にとっては、長文追加より `Overview` 直後の全体構成図と `mic-loop` の処理フロー図を 1 つずつ入れる方が効果的。

- `src/core/pipeline.py` を介して CLI と Web UI が共通経路へ寄った点は妥当。連携用システムを中心に据える方向として筋が良い。
- `src/web/app.py` のブラウザ録音 UI は、結果領域だけ更新する fetch ベースに変わり、録音中・処理中の状態が見やすくなった。
- README は初見ユーザー向けにかなり改善されており、`今できること / まだできないこと` と `capture -> buffer -> transcribe` の説明は有効。現状理解の補助として十分機能している。
- 全体評価としては、`保守 GUI としては妥当、他システム連携の本命としては次に API 境界が必要` という段階。


### 2026-03-21 (older review snapshot)

Status: adopted with open follow-ups

Note: この時点の Web/API 指摘の多くは、後続実装で解消済み。

#### Findings

- Medium: `src/web/app.py:428-517` で HTML 向け `handle_transcription()` と JSON API 向け `handle_transcription_api()` がほぼ同じ処理を二重実装している。今回の API 追加自体は妥当だが、モデル検証、`ffmpeg` 確認、一時保存、Whisper 実行、例外分類、後始末が重複しており、次の仕様変更で UI と API の挙動がずれやすい。
- Low-Medium: Web UI 側は JSON API ルート追加後も `src/web/app.py:313-316` で HTML ルート `/transcribe-browser-recording` を fetch して `X-Requested-With` 分岐に依存している。`/api/...` を持つ構成に寄せた意図と少しずれており、サービス境界としてはまだ中途半端。
- Low-Medium: `smoke_test.py:112-145` で `/api/transcribe-upload` は追加検証されているが、`/api/transcribe-browser-recording` とユーザー報告の「GUI 上で 2 回連続録音できない」は未カバーのまま。今回の変更でサーバー側 API は強くなった一方、実ブラウザ依存の不安定さは依然としてレビュー上の open item。

#### Open questions / assumptions

- `JSON API ルートを追加しつつ、既存 UI 互換を保つために HTML ルート経由 fetch を残している` という段階的移行を意図している前提で見た
- ブラウザ録音 2 回連続失敗は、サーバー側ではなく `MediaRecorder` / 実ブラウザの状態遷移に残っている可能性が高いと仮定した
- `mic-loop` の有限最終回だけを `final` にする今回の整理は、暫定ルールとしては十分とみなした

#### Recommended next actions

- 1. `src/web/app.py` の転写本体処理を 1 つの共通関数へ寄せ、HTML / JSON はレスポンス整形だけ分ける
- 2. Web UI の fetch 先を `api_...` ルートへそろえるか、逆に header 分岐方式へ一本化するかを決めて境界を明確にする
- 3. `smoke_test.py` に `/api/transcribe-browser-recording` の最小サーバーテストを追加し、実ブラウザ 2 回連続録音は引き続き手動確認項目として残す
- 4. ブラウザ録音の連続実行不具合は、`MediaRecorder` 再生成と `getUserMedia()` 再取得の実ブラウザ確認を続ける


#### Browser recording note

- 実装担当との切り分け議論として、ブラウザ録音 2 回連続失敗の主因候補はサーバー側より `MediaRecorder` と UI 状態遷移にある、という見立ては妥当。
- 優先度が高いのは `requestData() + stop()` の組み合わせ、`ondataavailable` / `onstop` の発火順、`resetRecorderState()` による早すぎる `idle` 復帰、`track.stop()` 後の stream 解放遅延の 4 点。
- 状態機械として `idle -> recording -> stopping -> uploading -> idle` を明示する方針は正しいが、レビュー上の重要点は `idle に戻す責任をどのイベントが持つか` と `resetRecorderState() が cleanup 専用か状態遷移も兼ねるか` を分けて考えること。
- 次の切り分けとしては、`requestData()` を外した比較、`ondataavailable` / `onstop` / `fetch` 完了順のログ、2 回目録音時の blob size、2 回目 `getUserMedia()` が新しい stream を返しているかの確認を優先すべき。


#### README direction / readability note

- 現在の README は、`音声入力フロントエンド兼サービス境界を優先し、GUI は保守用の薄い面` という今後の方針とは大筋で整合している。
- 一方で `README.md` は `Overview`, `Quick start`, `Usage` の間で説明とコマンド例がやや重複しており、初見の人には `何が主軸か` より `できること一覧` が先に強く見えやすい。
- 特に `Overview` は `今できること / まだできないこと` の直後に近い内容の箇条書きが続くため、情報量の割に読み進める負荷が少し高い。
- レビューとしては不整合というより、`方針は合っているが README が少しメモ寄りで冗長` という評価。最小改善なら `Overview` の圧縮、`Quick start` を最短導線へ限定、詳細例は `Usage` に寄せる、の順が効果的。
