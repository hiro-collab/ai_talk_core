# Share Note

## Turn contract

- turn mode: `code changes allowed`
- reviewer may update: `REVIEW.md` only
- design reviewer may update: `DESIGN_REVIEW.md` only
- implementer may update: `code`, `README.md`, `SHARE_NOTE.md`, `LOG.md`
- latest reviewed commit: `293de29 Add explicit Torch pin guidance details`
- latest applied review status:
  - reflected in code: runner CLI, mic-loop finalization on silence, interrupt-time final flush, longer-transcript repeat relaxation, time-based finalization, configurable VAD aggressiveness, Codex exec template with PATH validation, CUDA busy 時の CPU fallback, runner 実装の `src/runners/` 集約開始, `final` ヒューリスティクスの `src/core/finalization.py` 切り出し, `agent_*` handoff / runner 互換入口の追加, `src/core/handoff_bridge.py` で汎用 handoff 境界の導入開始, `src/core/agent_instruction.py` で指示草案生成の実体化, `src/runners/agent.py` で runner 実体の汎用化
  - reflected in records: yes
  - remaining open items: `final` 条件の高度化, VAD の実用化, 実行テンプレートの整理

## Integrator messages

- Worker は統合担当の最新メッセージをこの節で読む
- この節は一時運用面として扱い、採用済み事実の棚とは分けて最新有効分だけを残す
- Worker の事実ベースの応答先は `LOG.md`
- Worker の提案、懸念、境界相談は `OPERATIONS_DRAFT.md` または `MODULE_REQUIREMENTS.md`
- Worker は未合意の提案や途中経過を `SHARE_NOTE.md` に直接書かない

### Message to `worker/web-ui`

- 直近の返答、確認結果、連絡ルール理解の報告は受領済み
- `worker/web-ui` の `src/web/app.py` は main working tree へほぼ反映済み
- main 側は追加で、`prompt-only` 表示契約の維持と、保存済み handoff が無い時の 404 抑止を持っている
- 現在の未統合差分は `LOG.md` と `OPERATIONS_DRAFT.md` の worker 側記録が中心である
- API / handoff 契約は引き続き変更しない
- 優先テーマは `録音を主導線にする`, `結果を主役にする`, `handoff を次アクションとして見せる`
- 局所確認結果は `LOG.md` に `worker/web-ui:` で始めて追記する
- 統合相談が必要な場合だけ `OPERATIONS_DRAFT.md` に `worker/web-ui:` で始めて追記する

### Message to `worker/drivers-handoff`

- 担当範囲は `src/drivers/*`, `src/runners/*` と handoff 周辺の最小範囲に留める
- `main` で直接コミットしない
- 提出単位は code 差分を優先し、記録更新は原則分離する
- 返答受領済み。提出済み code commits は main working tree へ統合済み
- 現在の worker 側の未コミット差分は `LOG.md` のみ
- 次段の優先候補は handoff から agent 実行への bridge と backend status 表現の整理
- 進捗や確認結果は `LOG.md` に `worker/drivers-handoff:` で始めて追記する
- 契約変更や統合相談は `MODULE_REQUIREMENTS.md` または `OPERATIONS_DRAFT.md` に `worker/drivers-handoff:` で始めて追記する

## Implementer messages

### Message to implementer

- 方針連絡は確認済み
- Worker 向けの現在有効な作業指示の正本は、引き続き `## Integrator messages` に固定する
- `## Implementer messages` は統合担当との共有メモとして扱い、Worker への実作業指示の正本にはしない
- Worker への具体指示、提出単位の固定、採否判断は統合担当が中継する
- `SHARE_NOTE.md` は最新有効分だけを維持し、詳細履歴は `LOG.md` / `REVIEW.md` へ寄せる方針で進める

### Message to integrator

- 今回の目的は、現行の分担運用を崩さずに UI 調整と記録整理を安全に進めること
- `main` での直接コミット禁止を維持し、境界越え、契約変更、main 影響ありの案件を優先して中継する
- `SHARE_NOTE.md` は最新有効な指示と統合済み事実だけを残し、詳細履歴は `LOG.md` / `REVIEW.md` 参照へ寄せる
- `worker/web-ui` の返答、109 tests / OK、連絡ルール理解の確認は受領済みとして扱う
- コードレビュー担当からの最新所見は受領済みとして扱い、`worker/drivers-handoff` の次の返答待ちを継続する
- 前回確認以降の追加返答はないため、現行連絡を維持する
- 優先機能は `mic-loop final`, `VAD 実運用`, `handoff -> agent bridge`, `backend status 表現`, `結果再利用導線` の順で扱う

### Message to `worker/web-ui`

- [`src/web/app.py`](/home/hiromu/projects/ai_core/src/web/app.py) の UI 表示整理を `web/ui` 層の中で閉じて進める
- 主導線、status 面、結果ラベル、次アクションの見せ方は調整してよい
- API / handoff 契約は変更しない
- 直近の Hero 圧縮、status 圧縮、結果ビュー文言整理は妥当
- 次も小さい提出単位で進め、`情報設計の再配置` と `結果アクション追加` を同時に広げすぎない
- 優先テーマは `録音を主導線にする`, `結果を主役にする`, `handoff を次アクションとして見せる`
- 現時点では追加の差し戻しはなく、引き続き同方針で進めてよい
- 進捗と確認結果は `LOG.md` に `worker/web-ui:` で記録し、統合相談が必要な場合だけ `OPERATIONS_DRAFT.md` に上げる

### Message to `worker/drivers-handoff`

- `src/drivers/*`, `src/runners/*`, handoff 周辺の最小範囲で責務を保ったまま進める
- 提出単位は code 差分を優先し、CLI / Web / docs まで同時に広げない
- 直近の返答はまだ未確認のため、まず差分の有無、再開する範囲、局所確認計画を `LOG.md` に短く返す
- 追加返答があるまでは、新規作業を広げず現行方針を維持する
- 優先テーマは `handoff を agent 実行へ渡す次段 bridge` と `backend ごとの status / response 表現` の整理
- 進捗は `LOG.md`、契約変更や境界相談は `MODULE_REQUIREMENTS.md` または `OPERATIONS_DRAFT.md` に記録する

### Message to code reviewer

- 最新の所見受領を確認した。現時点の懸念は `SHARE_NOTE.md` と運用記録の責務分離にあるものとして扱う
- 次回も `core/session`, `drivers/handoff`, `web/ui` の境界と、記録側の責務混在リスクを優先して見てほしい
- 技術面では `mic-loop final` 条件、VAD 実運用、handoff / bridge 命名整理を重点観点とする
- 今回は追加依頼なしとし、次回 review 時も所見は `REVIEW.md` にのみ記録する

### Message to design reviewer

- 本日は休み
- デザインレビュー依頼は次回に回す

## Changed files in latest implementation turn

- `src/web/app.py`
- `src/drivers/base.py`
- `src/runners/agent.py`
- `src/runners/common.py`
- `src/runners/ollama.py`
- `smoke_test.py`
- `MODULE_REQUIREMENTS.md`
- `OPERATIONS_DRAFT.md`
- `SHARE_NOTE.md`
- `LOG.md`

## Current status

- main の現在地は `agent handoff` 主導線と `worker/*` 運用ルールの両立を前提にする
- `main` の未コミット差分は記録ファイルと `smoke_test.py` に限られ、`src/web/app.py` の未コミット差分はない
- `worker/web-ui` の UI 改善は main working tree にほぼ統合済みで、main 側は `prompt-only` 表示契約と 404 抑止を追加保持している
- `worker/drivers-handoff` の driver response 正規化、runner 共通 helper、公開 export、関連 smoke test は main working tree に統合済み
- handoff / runner / driver / session / web service の分離は main に反映済み
- Web UI の Quick / Advanced / Debug 分離と maintenance status は main に反映済み
- 詳細な実装履歴と確認ログは `LOG.md` を正本とする

## Next tasks

- `--mic-loop` の `final` 条件をさらに詰める
- VAD の実用運用と無音処理の方針を固める
- handoff から agent 実行への次段 bridge を整理する
- backend ごとの response / status 表現の統一を検討する

## Feature priority

### 今すぐ必要

- `mic-loop` の `final` 条件を実用寄りにする
- VAD と無音処理の運用を固める
- `録る -> 結果を見る -> handoff を使う` の主導線を完成させる

### 近いうちに必要

- handoff から agent 実行への次段 bridge を整える
- backend ごとの status / response 表現をそろえる
- 結果の再利用導線を整える

### 後でよい

- handoff / bridge / cache path に残る `codex` 命名の整理
- `smoke_test.py` の責務別整理
- 履歴や session 保存の拡張

## Collaboration request

- リポジトリ分割は保留し、同一リポジトリ内で `core/session`, `drivers/handoff`, `web/ui` の境界を維持する
- レビュー所見は `REVIEW.md` / `DESIGN_REVIEW.md` に残し、合意済み事項だけを `SHARE_NOTE.md` に昇格する
- 事実ベースの進捗は `LOG.md`、境界相談は `OPERATIONS_DRAFT.md` または `MODULE_REQUIREMENTS.md` に残す

## Review-derived actions

- 無音表示改善、`webrtcvad` ベース検出、browser recording 連続実行確認は反映済み
- session / handoff / runner / driver / web service の切り出しは反映済み
- なお `final` 条件の高度化と VAD 実運用は open のまま

## Handover notes

- `ffmpeg` が必要
- `MEMORY.md`, `REVIEW.md`, `SHARE_NOTE.md`, `LOG.md` を用途別に使い分ける
- デザインレビューは `DESIGN_REVIEW.md` を主記録先にし、コードレビューとは混ぜない
- 詳細な統合履歴、採用判断、個別確認は `LOG.md` を参照する
