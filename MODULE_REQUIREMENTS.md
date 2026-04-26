# Module Requirements

このファイルは、実装担当とコードレビュー担当が共有する
`モジュールごとの要求仕様` の基準点です。

- レビュー所見そのものは `REVIEW.md` に書く
- UI / UX / 見た目の所見は `DESIGN_REVIEW.md` に書く
- このファイルには、現在の合意済み構成方針と要求仕様だけを書く
- 構成変更や責務変更が入ったら、実装担当が逐次更新する

## System goal

- 本プロジェクトの主目的は、音声入力を受けて transcript を作り、必要に応じて instruction / handoff を生成し、外部 agent backend へつなぐこと
- Web UI は主プロダクトではなく maintenance UI だが、使いやすく状態が分かりやすいことを要求する
- Ubuntu 環境を前提にする

## Layer policy

- `interface` は薄く保つ
- `core` は backend 非依存に保つ
- `driver` は backend 固有処理を閉じ込める
- `io` はホスト依存処理を閉じ込める
- 1 モジュール 1 責務を原則にする
- CLI / Web / API の分岐で core の状態管理ロジックを重複させない

## Module requirements

### `src/io/audio.py`

- Whisper 実行と runtime 検査を担当する
- `ffmpeg`, Torch, Whisper の環境依存を閉じ込める
- transcript 生成を返すが、handoff や driver 知識は持たない
- CLI 文言や Web payload 整形を持たない

### `src/io/microphone.py`

- マイク録音、silence trim、speech detection を担当する
- `arecord`, `ffmpeg`, `webrtcvad` のホスト依存を閉じ込める
- partial/final 判定や handoff 保存の責務は持たない
- 録音結果は `AudioChunk` 相当の core モデルへ渡す

### `src/core/pipeline.py`

- `AudioChunk`, `AudioBuffer`, `TranscriptionResult`, `TranscriptionPipeline` を提供する
- transcript を作る core primitive を担当する
- CLI / Web / driver に依存しない
- session 状態管理は持たない

### `src/core/finalization.py`

- partial から final へ寄せるヒューリスティクスだけを担当する
- repeat count, stable duration, silence, interrupt に関する判定を集約する
- CLI 出力や Web 表示に依存しない

### `src/core/session.py`

- realtime-style な音声セッションの状態管理を担当する
- 少なくとも `buffer`, `repeat_count`, `last_spoken_result`, `finalized_text` を管理する
- chunk 入力を受けて `TranscriptionResult` を返す
- CLI print, Flask request, handoff 保存を直接持たない
- 今後は常時待受に向けた `session/state` の核に育てる

### `src/core/input_gate.py`

- 外部入力で音声 capture を受け付けるかを決める backend 非依存の gate を担当する
- `input_enabled` / `mic_enabled` のような汎用 payload を受ける
- MediaPipe, WebSocket, OBS, Dify など具体 adapter には依存しない
- gesture 固有の判定は統合アプリまたは adapter 側で `input_enabled` に変換してから渡す
- session からは `should_accept_input()` / `set_input_enabled()` 相当で利用できること

### `src/core/agent_instruction.py`

- transcript から instruction draft を作る
- transcript 正規化と instruction 生成の最小責務に限定する
- backend 固有の prompt 組み立てを直接持たない

### `src/core/handoff_bridge.py`

- transcript / instruction を handoff bundle として保存・読込する
- JSON と text prompt の互換境界を維持する
- CLI / Web / driver のどこからでも再利用できるようにする
- backend 実行そのものは担当しない

### `src/web/transcription_service.py`

- Web/API 用の転写 service を担当する
- request 入力を正規化し、転写、handoff 保存、response payload 生成までを行う
- Flask route 定義や HTML rendering は持たない
- Web 専用の整形を閉じ込めるが、UI 表示ロジックは持たない

### `src/web/app.py`

- maintenance UI と JSON API の入口を担当する
- route 定義、HTML template、フロント JS を担当する
- 転写本体処理は service へ委譲する
- 将来的には `待機中`, `聞いている`, `文字起こし中`, `外部送信中`, `応答待ち`, `完了`, `エラー` の状態表示を扱える構成にする
- debug 情報は通常導線から分離する

### `src/runners/agent.py`

- handoff を外部コマンドへ流す runner CLI を担当する
- command 解決と driver request 作成の薄い橋渡しに留める
- backend 状態管理は持たない

### `src/runners/ollama.py`

- Ollama 向けの runner / driver bridge を担当する
- Ollama 固有のコマンド組み立てを閉じ込める
- transcript 生成や handoff 保存は担当しない

### `src/drivers/base.py`

- backend 実行の共通契約を担当する
- 少なくとも `DriverRequest`, `DriverResult`, `dispatch_driver_request()` を提供する
- runner CLI から subprocess 実行の詳細を分離する
- transcript 生成や handoff 読込は担当しない

### `src/main.py`

- CLI entrypoint を担当する
- 引数解釈、入口分岐、出力整形に留める
- mic-loop の状態遷移や転写本体は core/session へ委譲する
- runtime / dependency / doctor 系は段階的に helper へ切り出していく

### `smoke_test.py`

- CLI / Web / API / handoff / runner の回帰確認を担当する
- 互換入口の保護は維持する
- 将来的には責務単位で整理していくが、当面は既存入口の回帰防止を優先する

## Current refactor direction

- 第1段階: `src/core/session.py` を導入し、`src/main.py` の mic-loop 状態管理を移す
- 第2段階: `src/web/transcription_service.py` を導入し、`src/web/app.py` から転写本体処理を移す
- 第3段階: driver contract を整理し、`codex`, `ollama` などを共通境界で扱えるようにする
- 第3段階は最小導入済みで、runner から driver request/result 契約を経由する形になった
- 第4段階: maintenance UI に session 状態表示を導入する
- 第4段階の最初として、Web UI に基本状態表示を追加した
- 外部 gesture 連携の前段として、`src/core/input_gate.py` を導入し、MediaPipe を知らない入力制御境界を追加した

## Near-term product priorities

- 第1優先: `mic-loop` の `final` 条件と VAD / 無音処理を実用寄りにする
- 第2優先: handoff から agent 実行への次段 bridge を整える
- 第3優先: Web UI で `録る -> 結果を見る -> handoff を使う` の主導線を強くする
- 第4優先: backend ごとの status / response 表現をそろえる
- 第5優先: gesture / keyboard / network adapter から `input_enabled` を更新する composition root を追加する
- `codex` 命名整理や `smoke_test.py` 分割は後段の整理対象として扱う

## Review focus

- 各モジュールが要求仕様を超えて責務を抱えすぎていないか
- interface 層が core の状態管理を再実装していないか
- backend 固有処理が core に漏れていないか
- 常時待受へ伸ばす上で `session/state` の置き場所が妥当か
- 互換入口の維持と主導線の整理が両立しているか
