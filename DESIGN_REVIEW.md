# Design Review

このファイルは、UI / UX / 情報設計 / 見た目に関するレビューの主記録先です。
コードレビューの所見は `REVIEW.md` に書き、ここには混ぜないでください。

## Scope

- 使いやすさ
- 情報の見せ方
- 操作導線
- 視認性
- 最近の流行とのズレ
- 効率の良さ
- 見た目の一貫性
- クールさ / 安っぽさの回避

## Out of Scope

- バグ中心のコードレビュー
- 実装の保守性だけに寄った指摘
- 依存管理や環境構築の問題
- 記録ファイルの更新判断

## Expected Format

1. Findings
2. UX issues
3. Visual issues
4. Suggested improvements
5. Short summary

## Review Rules

- 抽象論で終わらず、必ず具体的な改善案を書く
- 可能なら「今すぐやるべきこと」と「後でやること」を分ける
- 小変更で効く改善を優先する
- `SHARE_NOTE.md` の `Turn contract` を先に確認する
- 今回が `レビューのみ` の場合は、このファイル以外を更新しない

## Current Focus

- `src/web/app.py` のローカル Web UI
- `README.md` の導線と情報設計
- instruction / handoff を扱う UI の分かりやすさ
- 状態表示の自然さ

## Review 2026-03-22

### Findings

1. 主導線が弱く、最初の一手が伝わりにくい。対象: Web UI 全体。[`src/web/app.py:193`](/home/hiromu/projects/ai_core/src/web/app.py#L193) [`src/web/app.py:196`](/home/hiromu/projects/ai_core/src/web/app.py#L196)
   - `ファイルアップロード` と `ブラウザ録音` が同格で並び、どちらを主操作にしたいのかが見えません。使い始めの判断コストが高いです。
   - 改善案: 録音を主役にするならヒーロー領域で強く見せ、アップロードは補助カードに下げる。逆ならその反対に寄せる。

2. 結果表示の主従が曖昧で、成果物が強く見えない。対象: 結果エリア。[`src/web/app.py:263`](/home/hiromu/projects/ai_core/src/web/app.py#L263) [`src/web/app.py:271`](/home/hiromu/projects/ai_core/src/web/app.py#L271)
   - `status` `result` `command` `meta` `error` が同じ調子で縦積みされ、何を読めばよいか一瞬で判断しづらいです。
   - 改善案: `transcript` を主、`指示草案` を副、保存先は折りたたみ詳細にする。見出しも日本語に統一する。

3. 開発者向けの情報が常時露出し、プロダクト感を損ねている。対象: Recorder Debug。[`src/web/app.py:256`](/home/hiromu/projects/ai_core/src/web/app.py#L256) [`src/web/app.py:291`](/home/hiromu/projects/ai_core/src/web/app.py#L291)
   - 通常ユーザーに不要な内部状態が前面にあり、安っぽく見えます。最近のツール UI としてはノイズです。
   - 改善案: `details` に退避するか、開発モード時のみ表示する。

4. 設定項目が常時見えていて、反復利用時の速度が出ない。対象: アップロード/録音フォーム。[`src/web/app.py:203`](/home/hiromu/projects/ai_core/src/web/app.py#L203) [`src/web/app.py:241`](/home/hiromu/projects/ai_core/src/web/app.py#L241)
   - `model` `language` `instruction_only` `save_handoff` が毎回見えるため、主操作の密度が下がっています。
   - 改善案: 詳細設定として折りたたみ、既定値は静かな補足テキストで見せる。

5. README が利用者導線より内部構造を優先していて、UI の位置づけが伝わりにくい。対象: README 冒頭から Setup まで。[`README.md:6`](/home/hiromu/projects/ai_core/README.md#L6) [`README.md:15`](/home/hiromu/projects/ai_core/README.md#L15) [`README.md:108`](/home/hiromu/projects/ai_core/README.md#L108)
   - Architecture と handoff の説明が早い段階で前に出ており、初見ユーザーが「まず何を試せばいいか」より先に内部事情を読む構成です。
   - 改善案: README 冒頭は `3つの始め方` を先に置き、Architecture は後段に下げる。

### UX issues

- 録音 UI は状態遷移自体は分かるものの、録音前後の期待値が弱いです。[`src/web/app.py:254`](/home/hiromu/projects/ai_core/src/web/app.py#L254) [`src/web/app.py:447`](/home/hiromu/projects/ai_core/src/web/app.py#L447)
  なぜそう感じるか: `録音中...` や `処理完了` は出る一方で、何秒録ったか、何をしているかの意味が浅いです。
  改善案: `録音中` `アップロード中` `文字起こし中` を分け、アイコンやラベルで状態の意味を明確にする。

- `指示草案を優先して返す` は機能の意味がすぐ伝わりにくいです。[`src/web/app.py:213`](/home/hiromu/projects/ai_core/src/web/app.py#L213) [`src/web/app.py:244`](/home/hiromu/projects/ai_core/src/web/app.py#L244)
  なぜそう感じるか: 通常ユーザーには transcript と command の違いが UI 上だけでは理解しづらいです。
  改善案: `文字起こしではなく、実行指示向けの短い文を優先` のような補足を付ける。

- README は CLI と Web UI の双方を説明しているが、対象読者別の分岐がありません。[`README.md:108`](/home/hiromu/projects/ai_core/README.md#L108) [`README.md:196`](/home/hiromu/projects/ai_core/README.md#L196)
  なぜそう感じるか: 触りたい人は Web UI、組み込みたい人は API/CLI ですが、導線が混ざっています。
  改善案: `まず試す`, `Web UI`, `API/CLI`, `内部構造` の順に章を分ける。

### Visual issues

- 配色は個性がある一方で、強弱がやや均一です。[`src/web/app.py:37`](/home/hiromu/projects/ai_core/src/web/app.py#L37) [`src/web/app.py:74`](/home/hiromu/projects/ai_core/src/web/app.py#L74)
  なぜそう感じるか: 面ごとの差が近く、重要要素が浮きません。
  改善案: 主 CTA と結果面だけコントラストを一段上げ、他は少し静かにする。

- タイポグラフィが無難で、結果の見せ場が弱いです。[`src/web/app.py:60`](/home/hiromu/projects/ai_core/src/web/app.py#L60) [`src/web/app.py:81`](/home/hiromu/projects/ai_core/src/web/app.py#L81)
  なぜそう感じるか: 見出しと結果本文の差が小さく、完成品より管理画面に近い印象です。
  改善案: 転写結果だけ文字サイズと行間を広げ、余白で読みやすさを作る。

- 英日混在のラベルが UI の統一感を落としています。[`src/web/app.py:257`](/home/hiromu/projects/ai_core/src/web/app.py#L257) [`src/web/app.py:265`](/home/hiromu/projects/ai_core/src/web/app.py#L265) [`src/web/app.py:267`](/home/hiromu/projects/ai_core/src/web/app.py#L267)
  なぜそう感じるか: UI 本文は日本語中心なのに、見出しや結果ラベルが英語です。
  改善案: 通常表示は日本語に統一し、技術語は補助的に残す。

### Suggested improvements

今すぐやること:

- 主導線を 1 本決める。`録音を試す` か `ファイルを試す` のどちらかを主 CTA に固定する。
- `Recorder Debug` を既定で隠す。
- 結果エリアを `文字起こし結果` `指示草案` `保存先` に整理し、保存先は折りたたむ。
- `指示草案を優先して返す` に説明文を追加する。
- README 冒頭に `最短で試す手順` を置き、Architecture を後ろへ回す。

後でやること:

- 録音開始から結果表示までの状態遷移を、色・アイコン・アニメーションで明確化する。
- Web UI を `Quick mode` と `Advanced mode` に分け、設定密度を下げる。
- README を読者別に再編し、`使う人向け` と `実装を追う人向け` を分離する。
- UI のトーンをもう少し洗練させる。今の暖色路線を保つなら、カード密度を減らし、主ボタンと結果面だけを強く見せる。

### Short summary

現状の Web UI は機能追加には追随できていますが、画面としては「機能が並んでいる」段階で、主導線と成果物の見せ方が弱いです。最小の改善で効くのは、主 CTA の一本化、結果エリアの再設計、デバッグ情報の退避、詳細設定の折りたたみです。README も同様に、内部構造より先に「最短で何ができるか」を見せた方が、全体の体験はかなり良くなります。
