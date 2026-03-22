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

- 効率化の次段としては、自作の `ffprobe + silencedetect` ベース判定を先に `webrtcvad` へ置き換えるのが妥当。CLI / Web UI / API の構成や `capture -> buffer -> transcribe` の境界は維持し、前処理だけ OSS に寄せるのが最小変更で効果が高い。
- Whisper 本体は直ちに置き換えず、必要が出た時点で `faster-whisper` を比較導入する方針がよい。先に VAD を改善し、その後に STT エンジンの速度比較へ進むのが順序として安全。
- Codex 向けの command / draft 生成ロジックは用途固有なので自作維持が妥当。効率化対象は `VAD` と `STT backend` に絞るべき。

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

- `smoke_test.py` の内容自体は妥当で、CLI / Web / API / handoff / runner / finalization の主要経路を一通り押さえている。最近増えた `agent_*` / `codex_*` の互換入口まで確認している点は、移行期の回帰防止として価値がある。
- 一方で、現状は `minimal smoke test` というより `smoke + regression + compatibility` を 1 ファイルへ積み上げた状態で、互換 alias の確認がやや冗長になっている。`command_only` / `instruction_only`, `save_command` / `save_handoff`, `codex_*` / `agent_*` のような対になる経路は parameterize できる余地がある。
- 今すぐ壊れているわけではないが、次の整理対象としては妥当。互換テストの価値は残しつつ、`smoke`, `compat`, `finalization` のように役割を分けるか、少なくとも alias 系をまとめる方向を検討してよい。

- README / Web UI / `src.main` / `SHARE_NOTE.md` の一般説明をさらに `Codex` 固有表現から `instruction draft` / `handoff` / `agent` 側へ寄せた整理は妥当。今回の確認では `uv run python smoke_test.py` が 74 件成功しており、大きな動作問題は見当たらない。
- 特に `src.agent_handoff` / `src.agent_runner` を正面入口として案内し、`src.web.app` の UI も `handoff payload` や `Instruction draft` 表記へ寄せたことで、外向きの語彙はかなり一貫してきた。
- 残るズレは構造側に限られており、保存先パスや互換モジュール名にはまだ `codex` が残る。今の段階では許容範囲だが、名称整理を最後まで進めるなら次は saved bundle / cache path と bridge 層の主名をどうするかを決める段階。

- README / Web UI / `src.main` の外向き文言を `Codex` 固有表現から `instruction draft` / `handoff` / `agent` 側へ寄せた整理は妥当。今回の確認では `uv run python smoke_test.py` が 70 件成功しており、大きな動作問題は見当たらない。
- 特に `src.web.app` の UI 文言と `src.main` の helper 名をそろえたことで、利用者向けには `Codex 専用ツール` より `汎用 handoff front-end` としての見え方が一段整っている。README と SHARE_NOTE もこの方向へ追従している。
- 残る論点は構造そのもので、外向き表現は `agent/handoff` にかなり寄ってきた一方、保存先パスや一部互換モジュールはまだ `codex` 名義が残る。次に名称整理を進めるなら、文言より先に保存 bundle と bridge 層の主名をどうするかを決める段階。

- `src.main` の helper 名を `print_agent_instruction_*` / `save_handoff_if_requested()` に寄せ、README でも `src.agent_handoff` / `src.agent_runner` を正面入口として案内し始めた整理は妥当。今回の確認では `uv run python smoke_test.py` が 70 件成功しており、大きな動作問題は見当たらない。
- `smoke_test.py` には `src.agent_handoff` の prompt / command 読取テストが追加されており、単なる命名変更ではなく新しい正面入口の回帰防止まで押さえられている。`src.web.app` の 404 メッセージも `handoff not found` に寄っており、外向きの語彙は一段そろってきた。
- 構造上の残件は同じで、外側の名称は `agent` に寄ってきた一方、保存・読込の実体やキャッシュパスはまだ `codex` 名義が残る。方向は良いが、次に本当に名称をそろえるなら `bridge` / saved bundle 周りをどこで切るかを決める段階に入っている。

- `src/runners/agent.py` を runner 実体として追加し、`src/agent_runner.py` はそこを参照、`src/runners/codex.py` は互換ラッパーへ下げた整理は妥当。前回の `agent_*` alias 追加から一歩進んで、runner 層では汎用名を主実装にできている。今回の確認では `uv run python smoke_test.py` が 68 件成功しており、大きな動作問題は見当たらない。
- `README.md` と `SHARE_NOTE.md` も `src/runners/agent.py` を主実装として扱う説明へ追従しており、runner 層については `agent` を主名、`codex` を互換名とする方向がかなり明確になった。
- 残る構造上の論点は同じで、runner と instruction は汎用名へ寄り始めた一方、handoff 保存・読込はまだ `src/core/codex_bridge.py` 側に残っている。次に一般化を進めるなら、runner の次は引き続き `handoff` / `bridge` 層が自然。

- `src/agent_handoff.py`, `src/agent_runner.py`, `/api/agent-handoff-latest` を追加して、既存 `codex_*` を壊さずにより汎用的な入口を増やした判断は妥当。段階的整理として安全で、今回の確認では `uv run python smoke_test.py` が 67 件成功しており、大きな動作問題は見当たらない。
- 一方で、一般化はまだ入口名の alias 追加が中心で、内部の共有表現や保存ロジックは引き続き `src/core/codex_bridge.py` に残っている。これは今の段階では実務的だが、`agent_*` 名が正式入口として育つなら、次はいずれ `handoff` / `bridge` 層の命名と責務をそろえる必要がある。
- README の汎用入口説明は追従しており妥当。ただし構造上は `agent_*` と `codex_*` の二重命名がしばらく併存するので、将来どちらを主名にするかは早めに決めた方が記録と利用導線が安定する。

- `src/runners/` への整理は妥当で、runner 系を `外部プロセスへ handoff を流す責務` でまとめた単位として分かりやすい。`src/codex_handoff.py`, `src/codex_runner.py`, `src/ollama_runner.py` を互換ラッパーとして残す方針も段階的移行として適切で、既存 CLI 名を壊さずに内部構造だけ整理できている。
- `README.md` の `Repository stance` と `MEMORY.md` の `Stable decisions` は、`ai_core` を現時点では `~/projects` 配下の開発・実験本体として扱い、`~/dev` の共通基盤とは分ける、という整理で一貫している。今の段階で `~/dev` へ寄せない判断は妥当。
- 次に自然なのは runner より `handoff` 層の整理で、共有 handoff が実質的には汎用なのに `src/core/codex_bridge.py` 命名のまま残っている点が次の一般化候補。`ollama_runner` を optional adapter として先に置く判断自体は良いが、Codex/Ollama の両方が共有する中間表現としては名前と責務のずれが少しずつ見え始めている。

- `src/main.py` に `--final-stable-seconds` と `validate_final_stable_seconds()` を追加し、時間ベースの `final` 判定を CLI から調整できるようにした変更は妥当。前回の `chunk_duration` 依存が強すぎる懸念に対して、少なくとも固定閾値のハードコードは解消されている。今回の確認では `uv run python smoke_test.py` が 62 件成功しており、大きな動作問題は見当たらない。
- `README.md` と `smoke_test.py` も今回の引数追加に追従しており、`--final-stable-seconds must be greater than 0` の入力検証や、設定閾値に応じた時間ベース判定の変化まで押さえられている。前回よりコード・文書・テストの同期状態は良い。
- 方針面で残るのは構造上の話で、`final` ヒューリスティクスが `src/main.py` に集まり続けている点は変わらない。repeat 回数、無音、割り込み、経過時間、CLI パラメータが同じモジュールに増えているので、次の整理単位として `pipeline` 側または専用ポリシーモジュールへ寄せる方向は引き続き妥当。

- Medium: `src/main.py` の `has_stable_duration_for_final()` は `stable_seconds = repeat_count * chunk_duration` で判定しているため、`--mic-loop --duration 8` のように長いチャンク長では、中くらい以上の発話が 1 回しか出ていなくても即 `final` になりえます。今回の狙いは `安定時間` の補助判定ですが、現在の実装だと `繰り返し安定` ではなく `単発チャンク長` の影響が強く、従来の repeat ベースより早く確定しすぎる経路が残っています。
- `smoke_test.py` は新しい時間ベース判定をカバーしていますが、`repeat_count == 1` かつ `chunk_duration >= 8` の即時 final 化は未検証です。今回の変更で `uv run python smoke_test.py` は 59 件成功していますが、境界条件の回帰防止としてはこのケースも欲しいです。
- README は `中くらい以上の発話は安定時間が十分長ければ final に寄せる` と追従していますが、方針案としては `final` ヒューリスティクスが増えるほど `src/main.py` から切り離す必要が高まります。repeat 回数・無音・割り込み・経過時間を同じ層で持ち始めているので、次の整理単位はここです。

- `src/codex_runner.py` の `codex-exec` に事前 PATH 検証を追加し、`codex` コマンド不在時は実行前に `Input error` で止めるようにした変更は妥当。実行時の `FileNotFoundError` 任せより利用者に分かりやすく、今回の確認では `uv run python smoke_test.py` が 57 件成功しており、大きな動作問題は見当たらない。
- `README.md` も `codex` コマンドが `PATH` にある前提を追記しており、今回の変更範囲ではコードと説明は整合している。`smoke_test.py` も絶対パス・PATH 不在の失敗系まで追加されていて妥当。
- 方針案としては、今後の構造整理ポイントは `src/main.py` に集まりつつある `mic-loop` の `final` ヒューリスティクスをどこへ逃がすかにある。`required_repeat_count_for_final()` や interrupt/silence finalization が増えてきたため、次の段階では CLI から切り離して `pipeline` 側または専用モジュールへ寄せる前提をレビューに残しておくのがよい。

- `src/main.py` に `maybe_finalize_on_interrupt()` を追加し、`Ctrl+C` 停止時も直前の安定発話を `final` として 1 回だけ flush できるようにした変更は妥当。`mic-loop` の実用上の取りこぼしを減らす最小改善として自然で、今回の確認では `uv run python smoke_test.py` が 52 件成功しており、大きな動作問題は見当たらない。
- その上の未コミット差分として、長い発話は `repeat_count >= 2` で `final` に寄せる `required_repeat_count_for_final()` が入っている。方向性自体は理解できるが、現時点では README と `smoke_test.py` にこの閾値変更の説明・検証が追従していないため、いまのコード状態ではヒューリスティクスだけが先行している。
- 今回の主な残件はここで、`final` 判定閾値を文字列長で変えるなら、その理由と境界条件を README かテストで明示した方がよい。さもないと `mic-loop` の `final` 挙動が初見では追いにくい。

- `src/codex_runner.py` に `codex-exec` テンプレートを追加し、最新 handoff を `codex exec -C <repo> -` にそのまま流せるようにした変更は妥当。既存の runner 構造を崩さず、Codex 連携の最短導線を 1 つ追加した形になっている。今回の確認では `uv run python smoke_test.py` が 48 件成功しており、大きな動作問題は見当たらない。
- `README.md` の Architecture / Codex Handoff Flow 図は今回の実装に追従しており、以前の `codex_bridge / codex_handoff / codex_runner が図に出ていない` という構成説明のズレは解消された。本文と図の同期状態は前回より明確に良い。
- 小さい残件は、`codex-exec` テンプレートの動作確認が実際の `codex` バイナリ実行ではなくコマンド組み立てテストまでに留まっていること。ローカル環境依存のため妥当ではあるが、実運用前には `codex` コマンドが PATH 上にある前提を README か運用メモで明示してよい。

- `src/main.py` の `mic-loop` に、安定した発話の直後に無音チャンクが来た場合は直前発話を `final` とみなす補助ルールを追加した変更は妥当。`partial/final` を本格実装にする前の最小改善として自然で、今回の確認では `uv run python smoke_test.py` が 43 件成功しており、大きな動作問題は見当たらない。
- `smoke_test.py` には `maybe_finalize_on_silence()` の成功系・非適用系が追加されており、今回のヒューリスティクス追加に対する最低限の回帰防止として十分。README も `同じ結果がある程度安定したあとに無音チャンクが来た場合は、その直前の発話を final として扱う` という説明まで追従している。
- 一方で README の構成図は最新の実装境界まで追いついていない。`Architecture` には `src/core/codex_bridge.py`, `src/codex_handoff.py`, `src/codex_runner.py` が出ておらず、現在の `handoff 保存 -> 読み出し -> 任意コマンドへ受け渡し` の流れは図から読み取りにくい。構成説明としては本文より図の方が stale 気味。

- `src/codex_runner.py` を追加し、最新 handoff を任意コマンドの stdin に流せるようにした変更は妥当。`src.codex_handoff` と保存済み handoff 境界の上に薄い CLI bridge を載せた形で、既存構成を崩していない。今回の確認では `uv run python smoke_test.py` が 41 件成功しており、大きな動作問題は見当たらない。
- `smoke_test.py` には `--print-only`、stdin への受け渡し、`--` 正規化が追加されており、今回の CLI 追加に対する最低限の回帰防止として十分。
- 残件は主に記録同期で、`SHARE_NOTE.md` の smoke test 件数は依然として 21 件のままで、今回の runner CLI 追加と 41 件成功の現在地に追いついていない。

- `src/core/codex_bridge.py` に最新 handoff 読み込みを追加し、`src/web/app.py` から `/api/codex-handoff-latest` で取得できるようにした変更は妥当。保存済みファイルを他プロセスが拾う境界として自然で、今回の確認では `uv run python smoke_test.py` が 38 件成功しており、大きな動作問題は見当たらない。
- `smoke_test.py` には `load_codex_handoff_bundle()` と `/api/codex-handoff-latest` の成功系・404 系が追加されており、今回の API 追加に対する最低限の回帰防止として十分。
- 残件は主に記録同期で、`SHARE_NOTE.md` の smoke test 件数は依然として 21 件のままで、今回の 38 件成功や handoff latest API 追加の現在地に追いついていない。


- Codex handoff の `.txt` 出力を bare command から `Voice transcript` / `Requested task` を含む prompt 形式へ寄せた変更は妥当で、そのまま Codex に渡しやすくなっている。今回の確認では `uv run python smoke_test.py` が 35 件成功しており、大きな動作問題は見当たらない。
- 残件は主に記録同期で、`SHARE_NOTE.md` の smoke test 件数や current status は今回の prompt 形式変更と 35 件成功にまだ追いついていない。


- Web/API の `save_command` を JSON だけでなく `.txt` prompt まで保存する拡張は妥当で、`command_text_path` を返す設計も自然。今回の確認では `uv run python smoke_test.py` が 32 件成功しており、大きな動作問題は見当たらない。
- 残件は主に記録同期で、`SHARE_NOTE.md` の smoke test 件数や current status は今回の `.txt` handoff 保存と 32 件成功にまだ追いついていない。
- `src/web/app.py` の `record_command_only` / `record_save_command` 付近は引き続きインデントがやや崩れており、構文や動作には影響しないが、次の保守性のためには整えてよい。


- Web/API から `save_command` で Codex payload を保存できる追加自体は妥当で、`command_path` を返す設計も自然。今回の確認では `uv run python smoke_test.py` が 30 件成功しており、大きな動作問題は見当たらない。
- 残件は主に記録同期で、`SHARE_NOTE.md` の smoke test 件数や現状説明はまだ今回の `save_command` 追加と 30 件成功に追いついていない。
- `src/web/app.py` の `record_command_only` / `record_save_command` 付近はインデントがやや崩れており、構文や動作には影響しないが、次の保守性のためには整えてよい。


- `src/io/microphone.py` のデフォルトマイク選択を `HD Pro Webcam C920` 固定から `arecord -l` で見つかった最初の入力デバイス優先へ一般化した変更は妥当。PC 固有ロジックを外す最小改善として自然で、前回までのレビュー観点にも合う。
- ただし記録側は少し追随不足があり、`SHARE_NOTE.md` では `Changed files in latest implementation turn` が今回の変更内容と一致していない。また `VAD は未着手` と `webrtcvad ベースの speech detection を反映済み` が同居しており、表現がややねじれている。
- 今回の残件はコード上の重大な問題ではなく、複数マイク環境で `arecord -l` の列挙順に依存することと、記録同期の明確化に寄っている。


- `webrtcvad -> partial/final 改善 -> faster-whisper 比較` の順序は、現状コードベースに対して合理的。今の主課題は STT backend の絶対速度より、無音や雑なチャンクを減らして入力品質を上げることなので、先に VAD を改善する方が精度と体感速度の両方に効く。
- `command / draft` 生成ロジックは用途固有なので自作維持で問題ない。効率化対象を `VAD` と `STT backend` に限定する切り分けは妥当。
- 逆に `faster-whisper` を先行導入すると、速度差・精度差・VAD不足が同時に変わって原因切り分けが難しくなるため、現段階では優先度を下げる判断が正しい。
- 運用面では、次のレビュー依頼前に `REVIEW.md` を棚卸しして stale な open item を整理する、という実装担当の判断も妥当。

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

## Review 2026-03-22 mic tuning stdout note

### Findings

- Medium: `--mic-loop` 開始時の `[mic-tuning] ...` 表示は有用ですが、`--command-only` でも stdout に必ず出るため、後段が標準出力をそのまま instruction として読む運用ではノイズになります。対象: [src/main.py](/home/hiromu/projects/ai_core/src/main.py)
- Low: `--list-mic-profiles` と `[mic-tuning] ...` の追加自体は妥当です。profile ごとの VAD / final しきい値が見えるので、調整結果を把握しやすくなっています。対象: [src/main.py](/home/hiromu/projects/ai_core/src/main.py), [README.md](/home/hiromu/projects/ai_core/README.md)
- Low: ここ最近レビューに手間がかかって見える主因は、コードが全面的に崩れているからではなく、`smoke_test.py` が互換性確認まで含む 81 テスト規模へ増え、`README.md` / `SHARE_NOTE.md` / `LOG.md` / `REVIEW.md` も同時に追う運用になっているためです。実装自体はまだ層で追えますが、`src/main.py` に mic-loop の表示・調整・最終化の責務が集まり気味です。

### Verification

- `uv run python smoke_test.py` を実行し、81 tests OK を確認

## Environment note

- GPU が見えていない主因は `CUDA_VISIBLE_DEVICES` ではなく、PyTorch の CUDA ビルドと NVIDIA driver の不整合の可能性が高い。確認結果では `torch.__version__ == 2.10.0+cu128`, `torch.version.cuda == 12.8` に対し、`nvidia-smi` は Driver `535.288.01` / CUDA `12.2` だった。
- この状態では `torch.cuda.is_available()` が `False` になり、Whisper は CPU fallback する。少なくともこのプロジェクト用途では、`cu128` の新しさより `GPU が安定して使える組み合わせへ合わせること` の方が性能影響が大きい。
- 実務上の優先順位は `driver を上げる` か `Torch を driver に合う CUDA build へ下げる` のどちらかで、まずは後者の方が小さい変更で収まりやすい。

## Review 2026-03-22 runtime status follow-up

### Findings

- Low: `--show-runtime-status` と `get_runtime_status()` の追加は妥当です。`transcription_device` と `runtime_note` が入り、GPU 不可時の CPU fallback を CLI から読み取りやすくなっています。対象: [src/io/audio.py](/home/hiromu/projects/ai_core/src/io/audio.py), [src/main.py](/home/hiromu/projects/ai_core/src/main.py)
- Low: 前回の懸念だった `[mic-tuning] ...` による stdout 汚染は改善されています。`[mic-tuning] ...` と `Stopped microphone loop.` を stderr に逃がしたことで、`--instruction-only` や handoff 用の stdout を壊しにくくなりました。対象: [src/main.py](/home/hiromu/projects/ai_core/src/main.py)
- Low: 記録側では [SHARE_NOTE.md](/home/hiromu/projects/ai_core/SHARE_NOTE.md) の `latest reviewed commit` がまだ `fd7e728` のままで、実装の現在地より古いです。今回の runtime status 追加自体は反映されていますが、この欄だけは stale です。

### Verification

- `uv run python smoke_test.py` を実行し、91 tests OK を確認

## Review 2026-03-22 memory startup note

### Findings

- Low: 今回の差分にはコード本体の変更がありません。確認できたのは [MEMORY.md](/home/hiromu/projects/ai_core/MEMORY.md) の `Codex startup` 追記と、未追跡の [AGENTS.md](/home/hiromu/projects/ai_core/AGENTS.md) だけでした。そのため、コードレビューとしての新しいバグ・設計所見はありません。
- Low: `Codex startup` の内容は運用メモとしては有用ですが、短期的な起動手順まで [MEMORY.md](/home/hiromu/projects/ai_core/MEMORY.md) に入れると、長期ルールと日次運用の境界が少し曖昧になります。恒常的な repository guidance は [AGENTS.md](/home/hiromu/projects/ai_core/AGENTS.md) 側、長期前提は [MEMORY.md](/home/hiromu/projects/ai_core/MEMORY.md) 側、と分けたままの方が整理しやすいです。

### Verification

- `git diff` 上、コード差分はなく、今回の変更対象は `MEMORY.md` と未追跡の `AGENTS.md` のみであることを確認

## Review 2026-03-22 doctor command follow-up

### Findings

- Low: `--doctor` の追加は妥当です。runtime と dependency の状態を 1 回で見られるので、今回の Torch/CUDA 不整合のような切り分けには有効です。対象: [src/main.py](/home/hiromu/projects/ai_core/src/main.py)
- Low: 実装自体に大きな問題は見当たりませんが、記録同期は少し遅れています。[SHARE_NOTE.md](/home/hiromu/projects/ai_core/SHARE_NOTE.md) の current status はまだ `90 件` の smoke test 成功のままで、今回確認した `97 tests OK` に追いついていません。[LOG.md](/home/hiromu/projects/ai_core/LOG.md) も同様です。
- Low: [MEMORY.md](/home/hiromu/projects/ai_core/MEMORY.md) の `Codex startup` と未追跡の [AGENTS.md](/home/hiromu/projects/ai_core/AGENTS.md) が併存しており、運用メモの置き場が少し重なっています。コードの不具合ではありませんが、役割分担としては整理余地があります。

### Verification

- `uv run python smoke_test.py` を実行し、97 tests OK を確認


## Review 2026-03-22 README and structure review

### Findings

- Medium: プロジェクトの主目的が「Whisper による最小文字起こし」ではなく「音声で拾った指示を agent に handoff すること」であるのに、[README.md](/home/hiromu/projects/ai_core/README.md) の冒頭と構成はまだ転写ツール中心に見える。特に [README.md](/home/hiromu/projects/ai_core/README.md#L3) の導入、[README.md](/home/hiromu/projects/ai_core/README.md#L8) の Overview、[README.md](/home/hiromu/projects/ai_core/README.md#L168) の互換説明が同じ重さで並んでおり、初見では「何のためのプロジェクトか」が掴みにくい。
- Medium: `agent_*` へ寄せる方針に対して、互換用の `codex_*` 導線が README とテストで前に出すぎている。実装上の互換ラッパーは小さいが、[src/agent_runner.py](/home/hiromu/projects/ai_core/src/agent_runner.py)、[src/codex_runner.py](/home/hiromu/projects/ai_core/src/codex_runner.py)、[src/agent_handoff.py](/home/hiromu/projects/ai_core/src/agent_handoff.py)、[src/codex_handoff.py](/home/hiromu/projects/ai_core/src/codex_handoff.py) の二系統が README と `smoke_test.py` 上でも並列に見え、読者に不要な選択肢を増やしている。
- Medium: [src/main.py](/home/hiromu/projects/ai_core/src/main.py) は CLI 本体に加えて、mic-loop 調整、handoff 保存、runtime/dependency doctor まで抱えており責務が重い。特に [src/main.py](/home/hiromu/projects/ai_core/src/main.py#L339) 以降の parser と [src/main.py](/home/hiromu/projects/ai_core/src/main.py#L492) 以降の分岐は、通常利用の入口としても保守観点でも読み負荷が高い。
- Medium: [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py) は将来もメンテナンス用ツールとして残す前提に対し、UI テンプレート、フロント JS、リクエスト処理、転写サービス呼び出しが 1 ファイルに集中している。特に [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py#L582) の `process_transcription_request()` は flag 解釈、一時ファイル処理、正規化、転写、handoff 保存、レスポンス整形まで一括で、保守用 UI として長く持つには見通しが悪い。
- Low-Medium: [smoke_test.py](/home/hiromu/projects/ai_core/smoke_test.py) は CLI / Web / API / handoff / runner / finalization を 1 ファイルに集約しており、カバレッジ自体は広いが、読みやすさと変更追跡性は落ちている。特に [smoke_test.py](/home/hiromu/projects/ai_core/smoke_test.py#L71) の互換 alias 群を含め、「何を守るテストか」の輪郭が掴みにくい。
- Low: README の説明には現状との差が残っている。[README.md](/home/hiromu/projects/ai_core/README.md#L9) では `VAD` を「まだできないこと」に入れている一方、[README.md](/home/hiromu/projects/ai_core/README.md#L52) では `webrtcvad speech detection` を mic-loop flow に含めており、実装にも VAD 関連の入口がある。[src/main.py](/home/hiromu/projects/ai_core/src/main.py#L33) これは「本格 VAD は未完成」なのか「軽量 VAD は導入済み」なのかを README 上で書き分けた方がよい。
- Low: 細部の可読性では、[src/main.py](/home/hiromu/projects/ai_core/src/main.py#L49) の `format_transcription_result()` が `object` を受けて `getattr` ベースになっている点や、[src/io/audio.py](/home/hiromu/projects/ai_core/src/io/audio.py#L113) 付近の空行の乱れなど、小さいが積み重なる読みにくさがある。大きな不具合ではないが、整理局面では拾いたい。

### Open questions / assumptions

- 今回のレビューは、主目的を「音声指示を agent に handoff すること」、主導線を `agent_*`、Web UI を将来も残すメンテナンス用ツール、という前提でまとめた。
- `codex_*` は当面の互換入口として維持しつつも、今後の説明・命名・主導線は `agent_*` に寄せていく想定で見た。
- 案内資料の「読みやすさ」は UI デザインではなく、README、CLI help、モジュール責務、テストの見通しを主対象として扱った。

### Recommended next actions

- 1. [README.md](/home/hiromu/projects/ai_core/README.md) の冒頭を `agent handoff` 主体に書き換え、`transcribe` は手段、`Web UI` は保守用導線と分かる順序へ再構成する。
- 2. README と CLI 例は `agent_*` を主導線に固定し、`codex_*` は互換セクションへ退避する。
- 3. [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py) から転写処理本体を service 関数へ切り出し、テンプレートとリクエスト処理の責務を分ける。
- 4. [src/main.py](/home/hiromu/projects/ai_core/src/main.py) の doctor/runtime/dependency 系と mic-loop 系の責務を段階的に分離する。
- 5. [smoke_test.py](/home/hiromu/projects/ai_core/smoke_test.py) を少なくとも `CLI / Web / Handoff` の論理単位に整理し、レビュー時に意図を追いやすくする。

### README restructuring note

- README の再構成自体は、コードや互換導線との整合を見ながら進める必要があるため、実装担当が [README.md](/home/hiromu/projects/ai_core/README.md) を編集するのが妥当。
- レビュー観点としては、再構成の軸を `Whisper の最小文字起こし` ではなく `音声で拾った指示を agent に handoff するローカルツール` へ明示的に寄せるべき。
- 章立ては `まず試す` -> `Web UI` -> `API / CLI` -> `Agent handoff` -> `Compatibility notes` -> `Architecture` の順がよい。これは [DESIGN_REVIEW.md](/home/hiromu/projects/ai_core/DESIGN_REVIEW.md#L67) の `3つの始め方` および [DESIGN_REVIEW.md](/home/hiromu/projects/ai_core/DESIGN_REVIEW.md#L81) の `読者別に分ける` 提案とも整合する。
- 実装担当が整理する際は、[SHARE_NOTE.md](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L124) にある再編方針、すなわち `transcription core`, `session/state`, `driver`, `maintenance UI` の境界を README の説明順にも反映させるのが望ましい。
- `agent_*` を主導線、`codex_*` を互換導線として明確に分け、初見ユーザーに不要な選択肢を最初から見せすぎない構成にした方がよい。

### Codex thread sizing note

- 今後のレビューでは、実装の正しさだけでなく `1つの Codex スレッドで安全に把握できる変更単位か` も確認対象に含めるべき。
- 現時点の目安として、1 スレッドで安全に扱いやすい単位は `1層 + 1目的`、変更ファイル `3-6 個程度`、外部境界 `2つまで`、テスト観点 `1-2 系統まで` と考えるのが妥当。
- 逆に [src/main.py](/home/hiromu/projects/ai_core/src/main.py), [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py), [smoke_test.py](/home/hiromu/projects/ai_core/smoke_test.py) のように、複数責務を集約した箇所は、単一スレッド実装で局所最適の修正が入りやすく、整合崩れのリスクが高い。
- 分割判断の危険信号としては、`変更が 7 ファイルを超える`, `2 層以上をまたぐ`, `UI と core を同時に触る`, `構造変更と機能追加を同時に行う`, `互換 alias と新設計を同時に整理する`, `テスト更新が広範囲に及ぶ` を目安にするとよい。
- このプロジェクトでは、少なくとも `core/session`, `drivers/handoff`, `web/ui` の 3 担当に分ける前提で設計とレビューを進めた方が安全であり、必要に応じて `cli/runtime`, `tests/docs` まで分離できる構造を意識するのが望ましい。

### Module contract note

- 今後の分担実装とレビュー精度を上げるため、各モジュールの `要求仕様 / 契約` を実装担当が 1 か所に明文化した方がよい。
- 現状はコードと README と運用メモに意図が分散しており、レビュー担当が `このモジュールが何を保証し、どこまで責任を持つか` を毎回コードから逆算している。
- 少なくとも `transcription core`, `session/state`, `handoff`, `drivers`, `Web UI / CLI / API`, `tests/docs` の単位で、`purpose`, `inputs`, `outputs`, `invariants`, `non-goals`, `owner boundary` を整理しておくと、責務逸脱や境界崩れをレビューで検出しやすくなる。
- 特に [src/main.py](/home/hiromu/projects/ai_core/src/main.py), [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py), [src/core/handoff_bridge.py](/home/hiromu/projects/ai_core/src/core/handoff_bridge.py), [src/runners/agent.py](/home/hiromu/projects/ai_core/src/runners/agent.py) は入口と境界が混ざりやすいため、先に契約を書いてから整理した方が安全。
- 記録場所は分散させず、実装担当が参照・更新しやすい 1 ファイルに集約するのが望ましい。レビュー観点としては、`モジュール契約が存在すること` 自体を、今後の再編の前提条件に近い扱いで見てよい。

### Review ownership split proposal

- コードレビュー担当も、実装担当の分割方針に合わせて役割を分ける案を採ってよい。
- 基本案としては、`core/session`, `drivers/handoff`, `web/ui` の 3 系統でレビュー責務を分けるのが妥当。
- 必要に応じて `cli/runtime`, `tests/docs` を追加し、入口の薄さ、運用診断、README や契約文書との整合、回帰防止観点を別に見られるようにするとよい。
- 常時すべてを分離するより、`主担当レビュー 1 本 + 必要時だけサブレビュー追加` の運用の方が軽く、現実的。
- サブレビューを追加すべき条件は、`2 層以上をまたぐ変更`, `7 ファイル超の変更`, `UI と core の同時変更`, `構造変更と機能追加の同時進行`, `互換 alias 整理を含む変更`, `テスト更新が複数層に及ぶ変更` を目安にするとよい。
- この分割案を採る場合、各レビュー担当も `モジュール契約` を前提に見られるようにし、`実装の正しさ` だけでなく `責務逸脱`, `境界のにじみ`, `将来の分担実装を壊さないか` を明示的に確認するのが望ましい。

### Operations change note

- 今回の運用変更の方向性自体は妥当であり、複雑化したコードとレビューを `1 スレッド / 1 担当` に集約しない方針は、このリポジトリの現状に合っている。
- ただし、運用ルールを `REVIEW.md` に追記するだけでは、履歴の厚さに埋もれて実装担当に読み飛ばされる可能性がある。
- 実装担当に実際に読まれ、運用として機能させるには、`判断に使う短い形` で残すことが重要であり、長文の所感より `何が変わったか`, `いつ分割するか`, `誰が何を見るか` が一目で分かる書き方の方がよい。
- レビュー記録としては `REVIEW.md` に残す価値があるが、実効化には実装担当が後で [SHARE_NOTE.md](/home/hiromu/projects/ai_core/SHARE_NOTE.md) などの基準点へ `合意済み運用変更` として昇格させる必要がある。
- したがって、レビュー側の役割は `提案をレビューに残すこと`、実装担当側の役割は `採用した運用だけを共有基準へ反映すること` と切り分けるのがよい。

## Review 2026-03-22 operations sync review

### Findings

- Low-Medium: 分担運用そのものは前進しているが、コードレビュー記録が最新実装に追いついていない。現行コードには [src/core/session.py](/home/hiromu/projects/ai_core/src/core/session.py#L35), [src/web/transcription_service.py](/home/hiromu/projects/ai_core/src/web/transcription_service.py#L83), [src/drivers/base.py](/home/hiromu/projects/ai_core/src/drivers/base.py#L29), [src/core/status_report.py](/home/hiromu/projects/ai_core/src/core/status_report.py#L1) が入り、README も `agent handoff` 主体に再構成されているが、[REVIEW.md](/home/hiromu/projects/ai_core/REVIEW.md) の最新レビュー群はまだ `src/main.py` / `src/web/app.py` の責務集中や旧 README 構成を前提にした所見が中心で、`108 tests OK` を含む今回の分割結果を評価しきれていない。運用としては `分担実装` は動いているが、`分担レビュー` はまだ同期不足。
- Low-Medium: [SHARE_NOTE.md](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L17) 以降は current status, next tasks, collaboration request, handover notes が 1 ファイルに厚く積み上がっており、最新の統合済み事実と draft/補足が混ざりやすい。特に [SHARE_NOTE.md](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L177) の worker 未提出メモのような統合担当向け注記まで同居していて、`いま main に何が入っているか` を一読で判断しづらい。
- Low: [OPERATIONS_DRAFT.md](/home/hiromu/projects/ai_core/OPERATIONS_DRAFT.md#L16) と [MODULE_REQUIREMENTS.md](/home/hiromu/projects/ai_core/MODULE_REQUIREMENTS.md#L17) は有効に機能しており、少なくとも `1スレッド = 1層 + 1目的`、`interface は薄く保つ`、`CLI / Web / API で core 状態管理を重複させない` という方針は、[src/main.py](/home/hiromu/projects/ai_core/src/main.py#L110), [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py#L390), [src/runners/agent.py](/home/hiromu/projects/ai_core/src/runners/agent.py#L63) の実装にも反映され始めている。少なくとも今回確認した範囲では、分担の方向性は正しい。
- Low: 残る主なリスクは、コード分割より `smoke_test.py` と運用記録の集中である。[MODULE_REQUIREMENTS.md](/home/hiromu/projects/ai_core/MODULE_REQUIREMENTS.md#L117) でも当面は回帰防止優先としているため妥当ではあるが、レビュー/統合コストの中心は引き続きここに残る。

### Open questions / assumptions

- 今回は `main` 上の現行コードと記録ファイルを見て、分担運用が機能しているかを確認した。
- `SHARE_NOTE.md` の `108 件` と handover note の統合担当確認は、main 上での統合確認結果として扱った。
- 各 worker の個別差分までは追っていないため、評価対象は `最終統合後の main に見えている状態` とした。

### Recommended next actions

- 1. [REVIEW.md](/home/hiromu/projects/ai_core/REVIEW.md) に、今回の `session/service/driver` 分割を前提にした新しいレビュー節を作り、古い前提の所見と区別できるようにする。
- 2. [SHARE_NOTE.md](/home/hiromu/projects/ai_core/SHARE_NOTE.md) は `現在の統合済み事実` と `worker / integrator 向け補足` を分け、main の状態を一読で把握できるようにする。
- 3. `分担実装は成功`, `分担レビューは同期不足`, `次の集中箇所は smoke_test.py と記録整理` という現状認識を共有基準へ短く反映する。

## Review 2026-03-22 worker scope pre-review

### Findings

- Low: `Worker_web_ui` の `Quick / Advanced / Debug` 分離は、`web/ui` 層の情報設計と表示密度の整理に留まる限り、`1層 + 1目的` に収まっている。対象は [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py) と必要なら関連する最小の Web テストまでに留めるべきで、`transcription_service`, `handoff`, `driver` 側の契約変更まで広げないのが安全。
- Low-Medium: `Quick / Advanced / Debug` 分離は、もし `どの情報を返すか`, `どの payload を作るか`, `どの保存処理を走らせるか` まで触り始めると `web/ui` から `service` や `handoff` へにじむ。UI モードは表示上の整理として扱い、意味論を変える変更は別ターンに切るべき。
- Low: `Worker_drivers_handoff` の `DriverResult` 最小拡張は、backend 実行契約の明確化に留まる限り、`drivers/handoff` 層の単一目的として妥当。[src/drivers/base.py](/home/hiromu/projects/ai_core/src/drivers/base.py) と [src/runners/agent.py](/home/hiromu/projects/ai_core/src/runners/agent.py), [src/runners/ollama.py](/home/hiromu/projects/ai_core/src/runners/ollama.py) 程度で閉じるなら安全。
- Low-Medium: `DriverResult` 拡張が危険になるのは、結果モデルの追加項目に合わせて `core` の handoff 形式、CLI 表示、Web UI 状態表示、README を同時に変え始めた場合。`driver contract の最小拡張` と `外向きの利用体験変更` は分けた方が将来の分担実装を壊しにくい。
- Low: 事前評価としては、今回の 2 件はどちらも `1層 + 1目的` に収められる。前提条件は、`Worker_web_ui` は UI 表示整理だけ、`Worker_drivers_handoff` は request/result 契約の最小変更だけに留め、`README.md` や `smoke_test.py` の広域整理を同時に抱え込まないこと。

### Open questions / assumptions

- `Quick / Advanced / Debug` は UI モード分離であり、API payload や handoff 契約の意味は変えない前提で見た。
- `DriverResult` 最小拡張は、backend dispatch の結果表現を少し整える変更であり、core の transcript/handoff モデルまでは触らない前提で見た。

### Recommended next actions

- 1. `Worker_web_ui` は `src/web/app.py` と Web UI 近傍テストだけで閉じるようにし、service 層の仕様変更は別ターンに分ける。
- 2. `Worker_drivers_handoff` は `src/drivers/base.py` と runner 呼び出し側の最小追従だけに留め、CLI / Web / docs の広域更新を同時に行わない。
- 3. どちらも `README.md` と `smoke_test.py` の大きな整理を抱え込むなら、`docs/tests` を別担当に切る方が安全。

## Review 2026-03-22 worker integration visibility review

### Findings

- Medium: `worker/web-ui` と `worker/drivers-handoff` の各 branch 自体はまだ基準点 `a010cd8` に止まっており、`git log --all` 上で進んでいるのは main の統合コミット `ea6f037` と `4f6b560` だけだった。したがって、今回レビューできたのは `各 Worker の生差分` ではなく `統合後の main に入った結果` だけであり、Worker 自走型運用としては可視性が弱い。早期検知レビューを安定させるには、review 依頼時に `対象 branch / commit / base` のいずれかを固定すべき。
- Low-Medium: `Worker_web_ui` の統合結果 [src/web/app.py](/home/hiromu/projects/ai_core/src/web/app.py) は `Quick / Advanced / Debug` 分離に加えて、maintenance status, Result Center, copy action, latest handoff refresh action まで同時に入っており、`web/ui` 層の中では閉じているが、`1層 + 1目的` としてはやや広がり気味。大きく壊れてはいないが、次回以降は `モード分離` と `結果アクション追加` を別ターンに分けた方が統合事故を減らせる。
- Low-Medium: `Worker_drivers_handoff` の統合結果では、[src/drivers/base.py](/home/hiromu/projects/ai_core/src/drivers/base.py) に `validate_driver_command_available()` を追加しつつ、[src/runners/common.py](/home/hiromu/projects/ai_core/src/runners/common.py) 側にも `validate_runner_command_available()` が残っている。現時点では互換 alias として動くが、command availability の責務が driver 層と runner 層に二重化しており、将来ここがずれると境界崩れの温床になる。
- Low: `DriverResult` への `command_name`, `succeeded`, `has_output` 追加自体は小さく、[src/drivers/base.py](/home/hiromu/projects/ai_core/src/drivers/base.py), [src/runners/agent.py](/home/hiromu/projects/ai_core/src/runners/agent.py), [src/runners/ollama.py](/home/hiromu/projects/ai_core/src/runners/ollama.py) で閉じており妥当。ただし現時点では caller 側で十分に活用されておらず、ここから CLI 表示や Web UI 状態表示まで同時に広げると `drivers/handoff` を超えてにじみやすい。

### Open questions / assumptions

- 今回の評価対象は worker branch の未統合差分ではなく、main に入った統合コミット `ea6f037` と `4f6b560` とした。
- `Worker_web_ui` と `Worker_drivers_handoff` の局所確認内容までは見えていないため、評価は統合後コードからの逆算を含む。

### Recommended next actions

- 1. Worker 単位レビューを依頼する際は、`対象 branch`, `対象 commit`, `base commit` のどれを見るかを明示する。
- 2. `Worker_web_ui` は次回以降、`情報設計の再配置` と `結果アクション追加` を別ターンに分ける。
- 3. `Worker_drivers_handoff` は command validation の正本を driver 側か runner 側のどちらかに寄せ、二重化を早めに解消する。
