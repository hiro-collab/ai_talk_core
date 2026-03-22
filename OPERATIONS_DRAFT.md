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

## Escalation draft

- 全担当が意見を上に通せるようにする
- ただし、`提案中`, `採用済み`, `実施済み` を同じ場所へ混ぜない

### Proposal status draft

- `提案中`
  - `REVIEW.md`
  - `DESIGN_REVIEW.md`
  - `MODULE_REQUIREMENTS.md`
  - `OPERATIONS_DRAFT.md`
- `採用済み`
  - `SHARE_NOTE.md`
- `実施済み`
  - `LOG.md`

### Proposal routing draft

- 実装 Worker:
  - モジュール境界や担当範囲の提案は `MODULE_REQUIREMENTS.md` または `OPERATIONS_DRAFT.md` に上げる
  - 実行した事実は `LOG.md` に残す
- 統合担当:
  - 各担当から上がった提案を拾い、採用したものだけ `SHARE_NOTE.md` に反映する
  - 統合と確認の事実は `LOG.md` に残す
- コードレビュアー:
  - 所見と懸念は `REVIEW.md` に書く
- デザインレビュアー:
  - 所見と懸念は `DESIGN_REVIEW.md` に書く

### Share note rule draft

- `SHARE_NOTE.md` は採用済みの現在地だけを書く
- レビュアーや Worker は、未合意の提案を直接 `SHARE_NOTE.md` に書かない
- 統合担当または実装責任者が、採用した内容だけを `SHARE_NOTE.md` に昇格させる

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

## Communication draft

- 基本の連絡経路は `統合担当経由` にする
- Worker 同士が直接仕様調整を始めない
- 境界を越える判断は、統合担当が中継して決める

### Direction flow draft

- 統合担当 -> Worker:
  - 作業指示
  - 担当範囲
  - 触ってよいファイル
  - 確認方法
- Worker -> 統合担当:
  - 実装結果
  - 未解決事項
  - 他担当へ影響する懸念
- 統合担当 -> レビュアー:
  - 見てほしい差分
  - 観点
  - 前提条件
- レビュアー -> 統合担当:
  - `REVIEW.md` または `DESIGN_REVIEW.md` に記録した所見
- 統合担当 -> `SHARE_NOTE.md` / `LOG.md`:
  - 採用結果
  - 実行事実

### Worker report template draft

Worker は統合担当へ、少なくとも次を短く返す。

```text
変更:
- ...

変更ファイル:
- ...

確認:
- ...

未解決:
- ...

他担当への影響:
- なし / あり: ...
```

### Integrator message template draft

統合担当が各担当へ最初に渡す指示は、少なくとも次を含める。

```text
役割:
- ...

今回の目的:
- ...

触ってよいファイル:
- ...

触らないファイル:
- ...

確認:
- ...

返答形式:
- 変更 / 変更ファイル / 確認 / 未解決 / 他担当への影響
```

## Worker-led execution draft

- Worker は `相談してから着手` より `担当範囲で実装まで進めてから報告` を基本にする
- 進みを速くするため、Worker の現場判断を許容する
- ただし、`main に入れるかどうか` の判断は統合担当が持つ
- 実装担当は、中長期の設計方針と標準パターンを握る

### Worker-led principles draft

- Worker は自分の担当境界内なら、提案だけで止まらず実装まで進めてよい
- Worker は小さい統合単位を意識し、区切りごとに報告する
- Worker は迷った場合、`A案で進めたが B案もある` という形で報告してよい
- Worker は他担当領域へ広げない
- Worker は `README.md` と `smoke_test.py` の大整理を勝手に始めない
- Worker は `SHARE_NOTE.md` を確定事項として更新しない

### Integrator gate draft

- 統合担当は Worker の成果を受けて、`採用 / 保留 / 差し戻し` を決める
- 統合担当は main に入れる順番と単位を決める
- 統合担当は `1 本ずつ統合 -> 全体確認 -> 次へ` を守る
- main に直接入る前に止めるのが統合担当の役割であり、Worker を細かく止めすぎない

### Integrator autonomy draft

- 統合担当は、毎回実装担当へ確認を取りに行かず、まず自分で一次判断する
- 実装担当への確認は、境界越え、複数層同時変更、main test failure のような例外時に絞る
- Worker は `相談待ち` ではなく `実装まで進めてから提出` を前提に扱う
- 統合担当は `main に入れるかどうか` の関門としてふるまう

### Integrator decision rules draft

- 採用寄りに判断してよい条件:
  - `1 Worker = 1責務 = 1統合単位` を守れている
  - 担当境界内で閉じている
  - 局所確認が通っている
- 保留寄りに判断すべき条件:
  - 変更が `7 ファイル` を超える
  - `2 層以上` をまたぐ
  - `UI と core` を同時に大きく触る
  - `README.md` と `smoke_test.py` の大整理を同時に含む
  - review で medium 以上の懸念が出ている
- 実装担当へ上げるべき条件:
  - Worker の変更が担当境界を越えている
  - `2 Worker` を同時に統合しないと成立しない
  - `src/main.py`, `src/web/app.py`, `smoke_test.py`, `README.md` を同時に大きく触る必要がある
  - main で `uv run python smoke_test.py` が落ちる

### Integrator priorities draft

1. main を壊さない
2. 担当境界を守る
3. `1 本ずつ統合` を守る
4. 採用済みと draft を混ぜない
5. 実装担当への確認は例外時だけに絞る

### Review reflection draft

- 統合担当は、各統合のたびに `どのレビュー所見を反映したか` を短く残す
- 目的は、レビューが読まれたかを見えるようにすること
- 長文でなく、差分単位で `反映したこと / 入れなかったこと` を書く

#### LOG format draft

`LOG.md` には、各統合ごとに次の固定フォーマットを追記する。

```text
- review reflection:
  - code: ...
  - design: ...
  - not adopted: ...
```

例:

```text
- review reflection:
  - code: `Worker_drivers_handoff` は `src/drivers/base.py` と runner 追従だけに留め、CLI / Web / docs へ広げなかった
  - design: `Worker_web_ui` で `Quick / Advanced / Debug` 分離を維持し、結果周辺の文言整理を進めた
  - not adopted: `README.md` と `smoke_test.py` の整理は今回の統合には含めなかった
```

#### SHARE_NOTE format draft

- 採用済みだけを共有する必要がある場合は、`SHARE_NOTE.md` に短く残す

```text
- Latest integration reflection:
  - code review: ...
  - design review: ...
```

### Implementation lead draft

- 実装担当は各 Worker の逐次判断を細かく止めない
- 実装担当は、統合後に標準パターンと設計方針へ寄せる
- 実装担当は、境界の逸脱と中長期の複雑化だけを強く監視する

### Fast reporting draft

- Worker の報告は短く固定する
- 統合担当は最初から全文を読まず、次だけで一次判断する
  - `変更`
  - `変更ファイル`
  - `確認`
  - `未解決`
  - `他担当への影響`

### Allowed worker updates draft

- Worker が更新してよいもの:
  - 自分の担当コード
  - 必要最小限の `MODULE_REQUIREMENTS.md`
  - 必要最小限の `OPERATIONS_DRAFT.md`
  - 実行事実としての `LOG.md`
- Worker が更新してはいけないもの:
  - 採用済み事項としての `SHARE_NOTE.md`
  - 他担当の主記録ファイル
  - main 統合判断を前提にした説明

### Message opening draft

- 連絡文の冒頭で、`誰から誰へ` と `今回の目的` を明示する
- 例:
  - `実装担当より統合担当への連絡です。`
  - `実装担当より実装 Worker への連絡です。`
  - `実装担当よりコードレビュー担当への連絡です。`
  - `実装担当よりデザインレビュー担当への連絡です。`
  - `統合担当より Worker_web_ui への連絡です。`
  - `統合担当より Worker_drivers_handoff への連絡です。`

### Role-specific opening draft

実装担当から統合担当への連絡例:

```text
実装担当より統合担当への連絡です。
今回の目的は、各担当の提案と差分を安全に集約し、main を常に動く状態に保つことです。
```

実装担当から実装 Worker への連絡例:

```text
実装担当より実装 Worker への連絡です。
今回の目的は、担当範囲を小さく保ち、責務を越えずに実装を進めることです。
```

実装担当からコードレビュー担当への連絡例:

```text
実装担当よりコードレビュー担当への連絡です。
今回の目的は、実装の正しさに加えて、責務境界と分担運用の安全性を確認してもらうことです。
```

実装担当からデザインレビュー担当への連絡例:

```text
実装担当よりデザインレビュー担当への連絡です。
今回の目的は、maintenance UI としての使いやすさと、voice-to-agent 導線の見せ方を確認してもらうことです。
```

統合担当から Worker への連絡例:

```text
統合担当より Worker_web_ui への連絡です。
今回の目的は、Web UI の見せ方と操作導線だけを改善することです。
```

```text
統合担当より Worker_drivers_handoff への連絡です。
今回の目的は、driver 契約と handoff / runner 境界だけを改善することです。
```

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

## Review request draft

- レビュー依頼時は、対象の特定だけを最小限で明示する
- 目的は、レビュアーが `main しか見えない` 状態を避けること
- 毎回長文にせず、次の 5 項目だけでよい

```text
対象 branch: ...
base commit: ...
review target: ...
状態: main 統合前 / main 統合後
見てほしい観点: ...
```

例:

```text
対象 branch: worker/web-ui
base commit: a010cd8
review target: ea6f037
状態: main 統合後
見てほしい観点: web/ui の責務逸脱がないか
```
