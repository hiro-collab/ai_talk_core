# Retired Paths

通常導線から外した記録と保留導線の索引です。本文は `archive/` 側に残しますが、通常の実装判断では archive まで読まなくても大丈夫です。必要な場合は履歴確認として参照します。

## Archive Policy

- archive は履歴確認用です。
- 要求仕様、責務境界、接続契約は active docs 側に短く書きます。
- archive の内容を採用する場合は、必要な事実だけを短く抽出し、`MODULE_REQUIREMENTS.md`、`docs/module-responsibilities.md`、または `docs/integration-contract.md` へ書き直します。
- 変更履歴、検証ログ、作業メモは仕様文書へ戻しません。

## Record Index

| Path | Status |
| --- | --- |
| `archive/2026-03-working-records/LOG.md` | 作業ログ。履歴確認用。 |
| `archive/2026-03-working-records/REVIEW.md` | コードレビュー記録。採用済み仕様とは分ける。 |
| `archive/2026-03-working-records/DESIGN_REVIEW.md` | UI/UX レビュー記録。Web UI 契約とは分ける。 |
| `archive/2026-03-working-records/SHARE_NOTE.md` | 旧連絡メモ。通常の作業入口とは分ける。 |
| `archive/2026-03-working-records/OPERATIONS_DRAFT.md` | 旧 worker / worktree 運用案。統合側で必要なら再定義する。 |
| `archive/2026-03-working-records/MEMORY.md` | 旧環境メモ。要求仕様とは分ける。 |
| `archive/2026-03-working-records/REVIEWER_INSTRUCTIONS.md` | 旧レビュー依頼形式。通常導線では使わない。 |

## Deferred Index

| Topic | Status |
| --- | --- |
| 真の音声 streaming STT | `mic-loop` は固定時間録音の反復として扱う。 |
| 本格的な発話区間検出 | 軽量 `webrtcvad` の範囲に留める。 |
| agent backend 実行基盤 | handoff を渡す境界までを担当する。 |
| backend status / response 表現の統一 | 要求仕様には昇格していない。 |
| `codex_*` 命名整理 | `agent_*` が主導線、`codex_*` は互換入口。 |
| `smoke_test.py` 分割 | 回帰確認は維持し、分割方針は仕様にしない。 |
