# Retired Paths

この文書は、通常導線から外した記録と保留した導線の要約です。判断に迷う内容は削除せず、archive 側に本文を残します。

## Archive Location

旧ログ、レビュー記録、作業指示、一時運用案は `archive/2026-03-working-records/` に移しました。これらは履歴確認用であり、要求仕様や接続契約の正本ではありません。

## Moved Records

| File | Kept For | Reason For Retirement |
| --- | --- | --- |
| `LOG.md` | 実行コマンド、結果、作業履歴 | 日時付き作業ログであり、仕様として読むには長すぎる |
| `REVIEW.md` | コードレビュー所見 | レビュー時点の懸念と提案であり、採用済み仕様と混在していた |
| `DESIGN_REVIEW.md` | UI/UX レビュー所見 | デザイン検討ログであり、Web UI 契約ではない |
| `SHARE_NOTE.md` | worker / integrator 間の連絡 | 単体開発時代の作業指示が正本に見えるため |
| `OPERATIONS_DRAFT.md` | 並列 worker / worktree 運用案 | 統合リポジトリ内の単体モジュール文書としては過剰な一時運用ルール |
| `MEMORY.md` | 環境メモ、安定判断、作業ルール | stable decision と一時運用が混ざっていた |
| `REVIEWER_INSTRUCTIONS.md` | レビュー依頼形式 | レビュー記録先の旧運用ルールであり、通常導線には不要 |

## Retired Operational Rules

次のルールは単体開発時代の運用として archive へ下げました。

- `worker/*` worktree を正規の分担単位とする運用。
- main worktree を統合担当専用とする運用。
- `SHARE_NOTE.md` の特定節を作業指示の正本にする運用。
- Worker の返答先を `LOG.md` / `OPERATIONS_DRAFT.md` / `MODULE_REQUIREMENTS.md` に振り分ける運用。
- コードレビューとデザインレビューの記録ファイルを通常導線に並べる運用。

統合リポジトリ側で同様の運用が必要な場合は、リポジトリ全体の運用文書で再定義してください。

## Deferred Product Paths

次の内容は削除せず、要約だけ残します。

- 真の音声 streaming STT: `mic-loop` は固定時間録音の反復であり、streaming STT ではない。
- 本格的な発話区間検出: 軽量 `webrtcvad` は使うが、production-grade VAD pipeline は未担当。
- agent backend 実行基盤: handoff を渡す境界までを担当し、backend lifecycle は統合側または runner target が持つ。
- backend status / response 表現の統一: runner/driver 境界の整理対象だが、要求仕様には昇格していない。
- `codex_*` 命名整理: `agent_*` を主導線にし、`codex_*` は互換入口として残す。
- `smoke_test.py` の責務別分割: 回帰確認は維持するが、分割方針は仕様ではない。

## Archive Use

archive を読むときは、ファイル名や見出しではなく、日付と文脈を確認してください。archive 内の提案、レビュー、作業指示は、そのまま採用済み仕様として扱いません。
