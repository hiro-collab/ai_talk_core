# Operations Draft

このファイルは、今後の並列実装と運用整理のための
`方針案` をまとめるドラフトです。

- 確定ルールではありません
- 安定した運用ルールになったものだけ `MEMORY.md` へ移します
- 実装担当、レビュー担当、統合担当が同じ前提を見るための草案です

## Purpose

- Codex 1 スレッドに責務を集めすぎない
- 複数担当で並列に進めても、境界が崩れないようにする
- `git worktree` を使った並列作業の置き場と確認手順を整理する

## Thread sizing draft

- 基本単位は `1スレッド = 1層 + 1目的`
- 1 スレッドで安全に扱いやすい目安:
  - 変更ファイル `3-6 個程度`
  - 外部境界 `2つまで`
  - テスト観点 `1-2 系統まで`
- 分割を検討すべき条件:
  - 変更が `7 ファイル` を超える
  - `2 層以上` をまたぐ
  - `UI と core` を同時に触る
  - `構造変更` と `機能追加` が同時に入る
  - `互換 alias` と `新設計` を同時に整理する
  - テスト更新が複数層に広がる

## Worker split draft

- `Worker_core_session`
  - 対象: `src/core/session.py`, `src/core/pipeline.py`, `src/core/finalization.py`, `src/main.py` の mic-loop 周辺
- `Worker_drivers_handoff`
  - 対象: `src/drivers/*`, `src/runners/*`, `src/core/handoff_bridge.py`, `src/core/agent_instruction.py`
- `Worker_web_ui`
  - 対象: `src/web/app.py`, `src/web/transcription_service.py`
- 必要時のみ追加:
  - `Worker_cli_runtime`
  - `Worker_docs_tests`

## Git worktree draft

- 上位ディレクトリを散らかさないため、worktree はリポジトリ配下に閉じる
- 候補パス:
  - `/home/hiromu/projects/ai_core/.worktrees/`
- 例:
  - `.worktrees/core-session`
  - `.worktrees/drivers-handoff`
  - `.worktrees/web-ui`
  - `.worktrees/cli-runtime`
  - `.worktrees/docs-tests`

### Naming draft

- branch 名:
  - `worker/core-session`
  - `worker/drivers-handoff`
  - `worker/web-ui`
- worktree 名は branch 末尾と揃える

### First setup draft

- 最初の試行では 2 Worker から始める
- 候補:
  - `worker/web-ui`
  - `worker/drivers-handoff`
- main worktree は `/home/hiromu/projects/ai_core` のまま使う

### Example commands draft

`.worktrees` ディレクトリを作る:

```bash
mkdir -p /home/hiromu/projects/ai_core/.worktrees
```

`Worker_web_ui` を作る:

```bash
git worktree add /home/hiromu/projects/ai_core/.worktrees/web-ui -b worker/web-ui
```

`Worker_drivers_handoff` を作る:

```bash
git worktree add /home/hiromu/projects/ai_core/.worktrees/drivers-handoff -b worker/drivers-handoff
```

確認:

```bash
git worktree list
```

### Working locations draft

- main / integrator:
  - `/home/hiromu/projects/ai_core`
- `Worker_web_ui`:
  - `/home/hiromu/projects/ai_core/.worktrees/web-ui`
- `Worker_drivers_handoff`:
  - `/home/hiromu/projects/ai_core/.worktrees/drivers-handoff`

### Removal draft

- 未統合で不要になった Worker は、その worktree だけ削除する

```bash
git worktree remove /home/hiromu/projects/ai_core/.worktrees/web-ui
git branch -D worker/web-ui
```

- 統合済みで不要になった Worker も同様に後片付けする
- branch を消す前に、統合済みか未統合かを確認する

## Ownership draft

- メイン worktree:
  - 統合担当だけが使う
  - レビュー確認、最終テスト、統合コミット、整合調整を担当する
- 各 worker worktree:
  - 自分の責務だけ編集する
  - 共通ファイルを複数 Worker で同時に触らない

### Shared file caution

- `README.md` と `smoke_test.py` は原則 `Worker_docs_tests` か統合担当に寄せる
- `src/main.py` は `Worker_core_session` か `Worker_cli_runtime` のどちらか一方だけ
- `src/web/app.py` は `Worker_web_ui` を主担当にする

## Role split draft

このドラフトでは、少なくとも次の 4 者を分けて扱う。

- 実装 Worker
- 統合担当
- コードレビュアー
- デザインレビュアー

### Implementation Worker draft

- 役割:
  - 担当責務のコード変更を行う
  - 局所確認を行う
- 原則:
  - `1 Worker = 1責務 = 1統合単位`
  - 他 Worker の担当ファイルを同時に触らない

### Integrator draft

- 役割:
  - main worktree を保持する
  - Worker の差分を 1 本ずつ統合する
  - 全体 smoke test を行う
  - rollback 判断を行う
- 原則:
  - main で直接大きな実装をしない
  - 複数 Worker をまとめて統合しない

### Code reviewer draft

- 役割:
  - 実装の正しさだけでなく、責務逸脱と境界崩れを確認する
  - 所見は `REVIEW.md` に書く
- 見る観点:
  - `core/session`
  - `drivers/handoff`
  - `cli/runtime`
  - `tests/docs`
- 補足:
  - 基本は `担当観点` で分け、必ずしも専用 worktree は持たない

### Design reviewer draft

- 役割:
  - maintenance UI の使いやすさ、状態表示、情報設計、見た目を確認する
  - 所見は `DESIGN_REVIEW.md` に書く
- 見る観点:
  - `web/ui`
  - README の導線
  - voice-to-agent console としての見せ方
- 補足:
  - こちらも基本は `担当観点` で分ける

## Reviewer handling draft

- レビュアーは Worker と別系統で扱う
- 最初の試行では、レビュアー専用 worktree は必須ではない
- まずは差分と main 上の確認結果を見てレビューする軽い運用でよい
- 必要になった時だけ、レビュアー専用 worktree を追加する

### Mapping draft

- `Worker_core_session`
  - 主レビュー観点: `core/session`
- `Worker_drivers_handoff`
  - 主レビュー観点: `drivers/handoff`
- `Worker_web_ui`
  - 主レビュー観点: `web/ui`
- 必要時のみ追加:
  - `cli/runtime`
  - `tests/docs`

## Integration draft

- 並列作業を始める場合でも、`main` は統合専用として扱う
- Worker は `main` に直接コミットしない
- `1 Worker = 1責務 = 1統合単位` を原則にする
- 統合は `1 Worker ずつ` 行う
- 複数 Worker をまとめて一気に main へ入れない

### Integration flow draft

1. `main` を現在の安定基準点にする
2. Worker ごとに専用 branch / worktree を切る
3. Worker 側で局所確認を行う
4. main worktree へ 1 Worker 分だけ取り込む
5. main worktree で `uv run python smoke_test.py`
6. 問題がなければ次の Worker を統合する
7. 問題があれば、その Worker の統合だけ戻す

## Rollback draft

- ロールバック単位は `ファイル` ではなく `Worker の統合コミット` として扱う
- 破損時は `reset --hard` ではなく `git revert` を優先する
- `main` 上では履歴を壊す操作を避ける
- どの Worker が何を入れたか分かる短い統合コミットを作る

### Safe rollback draft

- 失敗時の基本:
  - どの Worker 統合で壊れたかを特定する
  - main worktree でその統合コミットだけ `git revert` する
- まだ main に統合していない Worker の変更は、対応する worktree を破棄すればよい
- 慣れるまでは、統合ごとに確認を挟み、複数 Worker をまとめて戻す状況を作らない

### Checkpoint draft

- 慣れるまでは統合前後に lightweight tag を置く案も有効
- 例:
  - `checkpoint/pre-worker-web-ui`
  - `checkpoint/post-worker-web-ui`
- これは rollback 手段そのものではなく、`どの時点が安定だったか` を見失わないための目印として使う

## Trial plan draft

- 最初の試行では Worker を 2 本までに絞る
- 候補:
  - `Worker_web_ui`
  - `Worker_drivers_handoff`
- `src/main.py`, `README.md`, `smoke_test.py` のようなハブファイルを複数 Worker で同時に触らない
- 最初の試行では、統合のたびに `git diff --stat` と `uv run python smoke_test.py` を必ず確認する

## Verification draft

- Worker は局所確認だけ行う
- 全体 smoke test は統合担当が main worktree で行う
- 手動確認も原則として統合担当が行う

### Local verification examples

- `Worker_core_session`
  - `uv run python -m py_compile src/core/session.py src/core/pipeline.py src/core/finalization.py src/main.py`
  - mic-loop 周辺の確認
- `Worker_drivers_handoff`
  - `uv run python -m py_compile src/drivers/base.py src/runners/agent.py src/runners/ollama.py`
  - handoff / runner 周辺の確認
- `Worker_web_ui`
  - `uv run python -m py_compile src/web/app.py src/web/transcription_service.py`
  - Web/API 周辺の確認

### Integration verification

- main worktree で `uv run python smoke_test.py`
- 必要な手動確認:
  - Web UI の録音
  - handoff 保存
  - runner 実行
- 直近の実機確認では、以下を main worktree で確認済み:
  - `/api/transcribe-upload`
  - `save_handoff=true`
  - `src.agent_handoff --source web --format prompt`
  - `src.agent_runner --source web --template cat`
  - Web UI のファイルアップロード
  - ブラウザ録音 1 回
  - Web UI の状態表示
  - debug 折りたたみ

## Record handling draft

- 実行事実は `LOG.md`
- 合意済みの現在地は `SHARE_NOTE.md`
- 長期ルールになったものだけ `MEMORY.md`
- モジュール境界は `MODULE_REQUIREMENTS.md`
- このファイルは、その手前の運用ドラフト置き場として使う
