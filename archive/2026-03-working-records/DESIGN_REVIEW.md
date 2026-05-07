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

## Review 2026-03-22 runtime guidance follow-up

### Findings

1. `suggested_action` の追加は、単なる状態列挙ではなく次の一手が見える点で良い改善です。対象: [`README.md:196`](/home/hiromu/projects/ai_core/README.md#L196)
   - なぜそう感じるか: `runtime_note` だけより、利用者が次に何を見るべきか判断しやすくなります。
   - 改善案: README 側で `問題があるときは runtime_note と suggested_action を確認する` と 1 行で読む順番を示す。

2. runtime status の説明は有益ですが、重要度の順がまだ分かりにくいです。対象: [`README.md:196`](/home/hiromu/projects/ai_core/README.md#L196)
   - なぜそう感じるか: `nvidia_smi_available`, `nvidia_driver_version`, `nvidia_gpu_name`, `runtime_note`, `suggested_action` が同じ重みで並び、最初に何を見るべきかが弱いです。
   - 改善案: まず `transcription_device` と `torch_cuda_available`、次に `runtime_note` と `suggested_action` の順で確認する構成にする。

3. README 全体では、今回の追記も内部理解寄りの積み上げになっていて、利用者向け導線の軽さはまだ弱いです。対象: [`README.md:108`](/home/hiromu/projects/ai_core/README.md#L108) [`README.md:196`](/home/hiromu/projects/ai_core/README.md#L196)
   - なぜそう感じるか: 機能説明は増えている一方、`まず何をすればいいか` の整理はまだ強くありません。
   - 改善案: runtime guidance は `CLI / runtime troubleshooting` の小節へ寄せ、Web UI 利用者向けの導線と分ける。

### UX issues

- `suggested_action` の文言は運用者向けにやや硬いです。対象: [`README.md:196`](/home/hiromu/projects/ai_core/README.md#L196)
  なぜそう感じるか: `uv-managed Torch version` や `pin a driver-compatible build` は慣れていない利用者には重い表現です。
  改善案: README では `まず .venv 内の Torch 構成を確認する` のように一段噛み砕いて説明する。

- 今回の情報は CLI/運用には有益ですが、Web UI 利用者には直接関係しない部分もあります。対象: [`README.md:127`](/home/hiromu/projects/ai_core/README.md#L127) [`README.md:196`](/home/hiromu/projects/ai_core/README.md#L196)
  なぜそう感じるか: Web UI の起動導線と runtime troubleshooting が近いレベルで並んでいます。
  改善案: README を `まず試す`, `Web UI`, `CLI / runtime`, `内部構造` に寄せて分離する。

### Visual issues

- 今回の差分に Web UI の見た目変更はありません。
- そのため、前回レビューした主導線の弱さ、結果エリアの主従不明瞭、`Recorder Debug` の常時露出は継続課題です。対象: [`src/web/app.py:193`](/home/hiromu/projects/ai_core/src/web/app.py#L193)

### Suggested improvements

今すぐやること:

- README の runtime status 説明に、`まず何を見るか` を 1 行追加する。
- `runtime_note` と `suggested_action` の役割の違いを短く書く。
- runtime guidance を Web UI 説明から少し切り離し、CLI/運用向け情報としてまとめる。

後でやること:

- README を `まず試す`, `Web UI`, `CLI / runtime`, `内部構造` の順に再編する。
- 必要なら Web UI 側にも軽い runtime status 導線を用意するが、開発者向け情報を前面に出しすぎない。

### Short summary

今回の変更はデザイン面では README の情報設計改善としてプラスです。特に `suggested_action` の追加は、状態確認を `次の行動` までつなげられる点で良いです。ただし見せ方はまだ内部寄りなので、読む順番と読者別の整理を入れると、使いやすさはさらに上がります。

## Review 2026-03-22 trend-based UI direction

### Findings

1. このプロジェクトは、最近の音声 UI / AI ツールの流れに照らすと、`録音を主導線にする` 方向が最も自然です。
   - なぜそう感じるか: 音声入力は補助機能ではなく主操作として見せる流れが強く、現状 UI でも価値の中心はそこにあります。
   - 改善案: 画面中央の主 CTA を `録音開始` に寄せ、アップロードは補助導線に下げる。

2. 小変更で最も効くのは、入力方法より成果物を主役にする再設計です。
   - なぜそう感じるか: 現状の弱さは、入力の不足より `結果の主従が曖昧` な点にあります。
   - 改善案: `文字起こし結果` を主、`指示草案` を副、保存先や debug を詳細領域に分ける。

3. 機能量を維持しながら見た目を良くするには、`Quick / Advanced` の分離が有効です。
   - なぜそう感じるか: いまは設定・debug・本操作が同じ面にあり、使い手によって必要情報が違いすぎます。
   - 改善案: 通常利用では最小操作だけ見せ、設定や debug は `Advanced` に集約する。

### UX issues

- 現状は `まず何をするか` より `何ができるか` が先に見えます。
  なぜそう感じるか: 録音、アップロード、設定、debug が並列で出ており、主タスクの圧が弱いです。
  改善案: 主タスクを 1 つ決め、その成功フローに沿って UI を組み直す。

- 利用者の層が混ざっています。
  なぜそう感じるか: ふつうに試したい人と、handoff/debug まで使う人が同じ画面密度を見ています。
  改善案: `Quick mode` と `Advanced mode` を分ける。

### Visual issues

- 今の UI は個性はあるが、主役が立っていません。
  なぜそう感じるか: 主ボタン、結果、補助情報のコントラスト差が小さいため、全部が同じ強さに見えます。
  改善案: 主 CTA と結果面だけを一段強くし、他は静かにする。

- 開発中の情報が前に出ていて、完成品の印象を弱めています。
  なぜそう感じるか: debug 情報の露出で、ツールというより内部確認画面に寄ります。
  改善案: debug は通常表示から外す。

### Suggested improvements

今すぐやること:

- 方針として `録音を主導線にする` か `結果を主役にする` かを決める。
- そのうえで、主 CTA を 1 つに絞る。
- 結果エリアを主役化し、保存先や debug を退避する。

後でやること:

- `Quick / Advanced` 構成にする。
- README も同じ思想で `まず試す` と `詳細運用` に分ける。
- 状態遷移に最小限のモーションや視覚変化を入れる。

### Short summary

トレンドと現状の両方を見ると、このプロジェクトの UI 方針は `録音を主導線にする`, `結果を主役にする`, `詳細は隠す` の組み合わせが最も適しています。全部を大きく作り直す必要はなく、まずは主 CTA と結果表示の再設計だけでも、かなり今っぽく締まります。

## Review 2026-03-22 voice integration state visibility

### Findings

1. 将来的に `codex`, `ollama` など複数システムとの音声連携を目指すなら、`いま何をしているか` が一目で分かる GUI は必須に近いです。
   - なぜそう感じるか: 音声 UI は入力中・処理中・外部連携中の区別が見えないと、不安と誤操作が増えます。
   - 改善案: 録音ボタン中心の UI ではなく、状態機械そのものを見せる UI に寄せる。

2. 現状の Web UI は `録音中かどうか` は見えるが、`聞いている / 転写中 / handoff 中 / 外部応答待ち` の区別が弱いです。対象: [`src/web/app.py:254`](/home/hiromu/projects/ai_core/src/web/app.py#L254) [`src/web/app.py:352`](/home/hiromu/projects/ai_core/src/web/app.py#L352)
   - なぜそう感じるか: 音声体験として重要なのは、入力可否より状態の透明性です。
   - 改善案: 少なくとも `待機中`, `聞いている`, `文字起こし中`, `外部へ送信中`, `応答待ち`, `完了`, `エラー` の状態を明示する。

3. 複数バックエンドを扱うなら、`どのシステムに渡しているか` も UI に出すべきです。
   - なぜそう感じるか: `処理中` だけでは、ローカル転写なのか Codex 実行待ちなのか Ollama 応答待ちなのかが分かりません。
   - 改善案: `Sending to Codex`, `Waiting for Ollama` のように対象システム名を含めた状態表示にする。

### UX issues

- 音声 UI は、正しさより先に安心感が必要です。
  なぜそう感じるか: 喋っても拾われているのか、まだ待たされているのかが曖昧だと、ユーザーは話し直しや再操作をしがちです。
  改善案: マイク状態を大きく表示し、入力受付中は波形やパルスなどで `聞いている` 感を出す。

- 外部システム連携では待ち時間の意味づけが必要です。
  なぜそう感じるか: AI 系の待ち時間は数秒でも長く感じやすく、無言の待機は品質を低く見せます。
  改善案: `文字起こし中` と `Codex に送信中` と `応答待ち` を分けて、待ちの意味を明示する。

### Visual issues

- 状態表示はテキストだけでは弱いです。
  なぜそう感じるか: 音声連携は時間変化が本質なので、色・動き・強弱がないと把握しづらいです。
  改善案: 状態ごとに色、ラベル、軽いアニメーションを変える。

- 現状は処理フローが画面上で線になっていません。
  なぜそう感じるか: 結果領域はあるが、`今どの段階か` を示す進行表示がありません。
  改善案: `Listening -> Transcribing -> Drafting -> Sending -> Waiting -> Done` のような横並びまたは縦並びのステップ表示を入れる。

### Suggested improvements

今すぐやること:

- 音声連携 UI の基本状態を定義する。
- 最低限 `待機中`, `聞いている`, `文字起こし中`, `外部送信中`, `応答待ち`, `完了`, `エラー` を GUI に出す方針を決める。
- バックエンド名を状態表示に含める設計にする。

後でやること:

- 波形、パルス、進行ラインなどの軽い視覚表現を足す。
- `Codex`, `Ollama`, その他 backend を切り替えても同じ状態モデルで見せられるようにする。
- 状態機械を UI 設計の中心に置き、機能追加時も同じ表示体系で増やせるようにする。

### Short summary

このプロジェクトが最終的に複数システムとの音声連携を目指すなら、`聞いている / 処理している / 送っている / 待っている` が一目で分かる GUI は必要です。単なる録音 UI では足りず、状態の透明性を前面に出した音声連携 GUI を最初から設計方針に入れるべきです。

## Review 2026-03-22 structure coolness and operating rules check

### Findings

1. 現状の Web UI は「ださくはない」が、まだ `プロトタイプ感` が強く、最近の音声 AI ツールとしては主役の見せ方が弱いです。対象: [`src/web/app.py:193`](/home/hiromu/projects/ai_core/src/web/app.py#L193) [`src/web/app.py:196`](/home/hiromu/projects/ai_core/src/web/app.py#L196) [`src/web/app.py:263`](/home/hiromu/projects/ai_core/src/web/app.py#L263)
   - なぜそう感じるか: 色味と丸みで最低限の雰囲気は出ていますが、ヒーロー領域、主 CTA、成果物の見せ場が弱く、全部が同じ密度で並びます。
   - 改善案: `録音開始` か `文字起こし結果` のどちらかを主役に固定し、その面だけタイポグラフィと余白とコントラストを一段上げる。

2. UI 構成は機能追加に耐える手前までは来ているが、`Quick / Advanced / Debug` の分離がないため、ナウい構成というより開発画面寄りです。対象: [`src/web/app.py:203`](/home/hiromu/projects/ai_core/src/web/app.py#L203) [`src/web/app.py:234`](/home/hiromu/projects/ai_core/src/web/app.py#L234) [`src/web/app.py:256`](/home/hiromu/projects/ai_core/src/web/app.py#L256)
   - なぜそう感じるか: 近年の AI ツールは初回操作を極端に軽くし、詳細設定や内部情報は後段に逃がす構成が主流です。今はその逆で、最初から全部見えています。
   - 改善案: 通常表示は `録音`, `アップロード`, `結果` だけに絞り、モデル選択・handoff 保存・debug は折りたたみの `詳細設定` と `開発者向け` に分離する。

3. README はプロダクト導線より内部構造の説明が先で、見せ方としては玄人向けに寄りすぎています。対象: [`README.md:6`](/home/hiromu/projects/ai_core/README.md#L6) [`README.md:15`](/home/hiromu/projects/ai_core/README.md#L15) [`README.md:108`](/home/hiromu/projects/ai_core/README.md#L108) [`README.md:196`](/home/hiromu/projects/ai_core/README.md#L196)
   - なぜそう感じるか: 使い始めの画としては `Quick start` より `Architecture` が前にあり、体験の入口より実装事情を先に読ませています。
   - 改善案: README 冒頭を `最短で試す`, `Web UI を使う`, `CLI/API を使う`, `内部構造` の順に並べ替える。

4. 運用ルール自体は整理されており、レビュー担当の働き方は明確です。対象: [`REVIEWER_INSTRUCTIONS.md:7`](/home/hiromu/projects/ai_core/REVIEWER_INSTRUCTIONS.md#L7) [`REVIEWER_INSTRUCTIONS.md:35`](/home/hiromu/projects/ai_core/REVIEWER_INSTRUCTIONS.md#L35) [`SHARE_NOTE.md:3`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L3) [`SHARE_NOTE.md:139`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L139)
   - なぜそう感じるか: 記録先の分離、レビュー形式、今回の Turn contract が明示されていて、レビュー結果の置き場と責務がぶれません。
   - 改善案: この運用は維持でよいです。今回のようなデザインレビューでは、`DESIGN_REVIEW.md` のみに所見を寄せ、合意前のアクションを `SHARE_NOTE.md` に書かない運用を徹底する。

### UX issues

- 初回利用者にとって `何が最短成功ルートか` がまだ一目で分かりません。対象: [`src/web/app.py:198`](/home/hiromu/projects/ai_core/src/web/app.py#L198) [`src/web/app.py:228`](/home/hiromu/projects/ai_core/src/web/app.py#L228)
  改善案: どちらか一方に `おすすめ` を付けるか、ヒーローとして先頭に独立表示する。

- `指示草案` と `handoff payload` は power user 向け機能ですが、通常フローと同じ重みで見えています。対象: [`src/web/app.py:213`](/home/hiromu/projects/ai_core/src/web/app.py#L213) [`src/web/app.py:218`](/home/hiromu/projects/ai_core/src/web/app.py#L218) [`src/web/app.py:244`](/home/hiromu/projects/ai_core/src/web/app.py#L244)
  改善案: `詳細設定` に移し、通常利用では説明文だけ見せる。

### Visual issues

- 暖色ベースの方向性は悪くありませんが、現状は少し無難で、`クールさ` より `丁寧な業務ツール` に寄っています。対象: [`src/web/app.py:37`](/home/hiromu/projects/ai_core/src/web/app.py#L37) [`src/web/app.py:74`](/home/hiromu/projects/ai_core/src/web/app.py#L74) [`src/web/app.py:117`](/home/hiromu/projects/ai_core/src/web/app.py#L117)
  改善案: 色数は増やさず、主 CTA と結果面だけに強いコントラストを与えて、その他は静かにする。

- 結果ラベルの英日混在が、洗練より試作感を出しています。対象: [`src/web/app.py:265`](/home/hiromu/projects/ai_core/src/web/app.py#L265) [`src/web/app.py:267`](/home/hiromu/projects/ai_core/src/web/app.py#L267)
  改善案: UI 表示は日本語へ寄せ、英語は API や内部キーに閉じる。

### Suggested improvements

今すぐやること:

- Web UI を `主操作 1 つ + 補助操作 1 つ + 結果表示` の三層に整理する。
- `Recorder Debug` を既定で隠す。
- `instruction_only` と `save_handoff` を折りたたみ詳細へ移す。
- README の先頭を `最短で試す` ベースに並べ替える。

後でやること:

- `Quick / Advanced / Debug` の三段構成にする。
- 状態表示を `待機中 / 録音中 / 文字起こし中 / handoff 保存 / 完了` の流れで見せる。
- 音声ツールらしい軽いモーションや進行表示を足し、静的フォーム感を下げる。

### Short summary

構成は破綻しておらず、最低限の見た目も整っていますが、現時点では `クールなプロダクト` というより `整理された試作 UI` です。最近っぽく締めるなら、主導線を 1 本に絞ること、詳細を隠すこと、結果を主役にすることが効きます。運用ルールは十分整理されているので、レビュー担当は記録先を守って所見を分離する働き方で問題ありません。

## Review 2026-03-22 trend follow-up for stronger product usage

### Findings

1. 最新の音声 AI ツールは `録音開始までの速さ` を最優先にしており、このプロジェクトも主導線をさらに短くしたほうが使われやすくなります。対象: [`src/web/app.py:196`](/home/hiromu/projects/ai_core/src/web/app.py#L196) [`src/web/app.py:228`](/home/hiromu/projects/ai_core/src/web/app.py#L228)
   - なぜそう感じるか: Granola, Limitless 系は設定より前に `すぐ録る` を置いています。今の UI は録音前に設定密度が高く、初速で負けます。
   - 改善案: 初期表示は `録音開始` を主 CTA にし、アップロードは補助導線、設定は折りたたみへ寄せる。

2. 2025-2026 の流れでは、録音後に `再利用する面` があることが重要です。このプロジェクトは handoff / runner 境界を既に持っているので、そこを UI の価値として前面化したほうがよいです。対象: [`src/web/app.py:263`](/home/hiromu/projects/ai_core/src/web/app.py#L263) [`README.md:154`](/home/hiromu/projects/ai_core/README.md#L154) [`README.md:188`](/home/hiromu/projects/ai_core/README.md#L188)
   - なぜそう感じるか: 最近のツールは transcript 単体より `chat`, `follow-up`, `reuse`, `template` に価値を置いています。今の UI は handoff できるのに、その先の使い道が弱く見えます。
   - 改善案: 結果表示の直下に `Copy prompt`, `最新 handoff を開く`, `Codex に渡す`, `Ollama に渡す` のような次アクションを出す。

3. トレンド的には `モード` を前に出す構成が強いです。このプロジェクトでも `Transcript`, `Instruction`, `Handoff` を明示モードにしたほうが意味が伝わります。対象: [`src/web/app.py:213`](/home/hiromu/projects/ai_core/src/web/app.py#L213) [`src/web/app.py:244`](/home/hiromu/projects/ai_core/src/web/app.py#L244)
   - なぜそう感じるか: 現状の `指示草案を優先して返す` は機能の実力に対して見せ方が弱いです。今のままだと checkbox の一機能に見えます。
   - 改善案: `文字起こし`, `指示作成`, `agent handoff` の 3 モード切り替えを主 UI に出し、checkbox ではなく目的選択として見せる。

4. リアルタイム音声体験では状態の透明性が必須です。今後 Realtime 的な体験へ伸ばすなら、いまのうちから状態機械を UI の核にするべきです。対象: [`src/web/app.py:255`](/home/hiromu/projects/ai_core/src/web/app.py#L255) [`src/web/app.py:352`](/home/hiromu/projects/ai_core/src/web/app.py#L352)
   - なぜそう感じるか: 最新の voice agent 設計では、低遅延そのものより `いま何をしているか` の見え方が UX を左右します。
   - 改善案: `待機中`, `録音中`, `アップロード中`, `文字起こし中`, `指示生成中`, `handoff 保存済み`, `外部実行待ち` を順に見せる。

### UX issues

- `録る` の後に何ができるかが弱く、継続利用の絵が見えません。対象: [`src/web/app.py:263`](/home/hiromu/projects/ai_core/src/web/app.py#L263)
  改善案: 単発結果ではなく、直近履歴と再利用アクションを出す。

- power user 向けの強みが UI に昇格していません。対象: [`README.md:162`](/home/hiromu/projects/ai_core/README.md#L162) [`README.md:176`](/home/hiromu/projects/ai_core/README.md#L176) [`README.md:188`](/home/hiromu/projects/ai_core/README.md#L188)
  改善案: handoff / runner 連携は README 内部説明だけでなく、Web UI 上の行動導線として見せる。

### Visual issues

- いまの UI は `transcription form` には見えるが、`voice-to-agent console` には見えません。対象: [`src/web/app.py:198`](/home/hiromu/projects/ai_core/src/web/app.py#L198) [`src/web/app.py:227`](/home/hiromu/projects/ai_core/src/web/app.py#L227)
  改善案: 上部を録音中心のヒーローにし、結果と次アクションを一段強いカードで受ける。

- 最新トレンドに比べると、情報の静止感が強いです。対象: [`src/web/app.py:117`](/home/hiromu/projects/ai_core/src/web/app.py#L117)
  改善案: 状態ラベル、ステップ表示、軽いパルスなどで時間変化を出す。

### Suggested improvements

今すぐやること:

- 主 CTA を `録音開始` に寄せる。
- `Transcript / Instruction / Handoff` のモードを前面に出す。
- 結果の直下に `次にすること` を置く。
- `Recorder Debug` を通常表示から外す。

後でやること:

- 直近履歴を持たせ、再送・再実行できるようにする。
- `Codex`, `Ollama` など送信先ごとの recipe / shortcut を持たせる。
- `voice-to-agent console` として、状態機械中心の UI へ寄せる。

### Short summary

最新トレンドを踏まえると、このプロジェクトは単なる文字起こし UI より `voice capture to agent handoff` に振ったほうが強いです。すでに内部構成はその方向へ向いているので、UI でも `すぐ録る`, `モードを選ぶ`, `次に渡す` を前面に出すと、かなり使いたくなる道具になります。

### Trend references

- Granola overview: https://docs.granola.ai/help-center/getting-started/granola-101
- Limitless quick start: https://help.limitless.ai/en/articles/9096489-quick-start-guide-for-limitless-web-desktop
- OpenAI Realtime voice design: https://platform.openai.com/docs/guides/realtime/voice-design
- OpenAI voice agents guide: https://platform.openai.com/docs/guides/voice-agents
- OpenAI next-generation audio models announcement: https://openai.com/blog/introducing-our-next-generation-audio-models/

## Review 2026-03-22 implementation thread sizing and UI ownership

### Findings

1. このプロジェクトの UI / UX 改善は、今後 `web/ui` と `state/service` と `handoff/driver` を分けて扱わないと崩れやすいです。対象: [`src/web/app.py:30`](/home/hiromu/projects/ai_core/src/web/app.py#L30) [`src/web/app.py:274`](/home/hiromu/projects/ai_core/src/web/app.py#L274)
   - なぜそう感じるか: 現状の Web UI は HTML/CSS, ブラウザ録音 JS, request 制御, 出力整形が 1 ファイルに同居しています。見た目の小変更でも処理状態や API 応答との整合を壊しやすい構造です。
   - 改善案: `web/ui` 担当は画面構成と状態表示だけ、`web/session or service` 担当は状態機械と送受信制御だけ、`handoff/driver` 担当は外部連携だけを持つようにする。

2. デザインレビュー観点でも、Codex 1 スレッドで安全に持てるのは `中規模モジュール 1 個の改修` までです。
   - なぜそう感じるか: UI は見た目だけでなく、文言、状態、非同期処理、結果導線が絡むため、1ターンで複数層をまたぐと局所最適で崩れやすくなります。
   - 改善案: `1スレッド = 1層 + 1目的` を原則にし、UI と core を同時に触る作業は分割する。

3. 今後このリポジトリで `使いたくなる UI` を育てるには、実装の担当分離自体が UX 品質の前提になります。対象: [`SHARE_NOTE.md:124`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L124)
   - なぜそう感じるか: 状態機械中心の UI、Quick / Advanced 分離、voice-to-agent console 化は、見た目だけ直しても成立せず、状態モデルと外部連携の境界が安定している必要があります。
   - 改善案: 少なくとも `core/session`, `drivers/handoff`, `web/ui` の 3 担当に分けて進める。

### UX issues

- UI 改善と構造変更を同じスレッドで同時にやると、レビュー時に `見た目の問題` と `責務分離の問題` が混ざりやすいです。
  改善案: 画面の見直しは `web/ui` スレッド、状態遷移や保存導線は `session/service` スレッドに切る。

- `smoke_test.py` に多系統が集まる構成では、UI 改善の影響範囲が読みにくくなります。
  改善案: UI 主導の変更時は、少なくとも Web UI / API 観点を独立して扱える状態を目指す。

### Visual issues

- 現状の UI が少し `開発画面` に見える理由の一部は、見た目ではなく責務の混在です。
  改善案: UI 層の責務を薄くすると、画面も自然に `操作面` と `詳細面` に分けやすくなる。

### Suggested improvements

今すぐやること:

- 実装担当を `core/session`, `drivers/handoff`, `web/ui` の 3 本に分ける。
- `1スレッド = 1層 + 1目的` を明文化して守る。
- UI と core を同時に触るターンは避ける。

後でやること:

- `cli/runtime` 担当と `tests/docs` 担当も必要に応じて分ける。
- `src/web/app.py` を UI / state / endpoint の境界で分解する。
- `smoke_test.py` の責務集中を緩める。

### Short summary

このプロジェクトでは、担当分離は単なる開発効率の話ではなく、UI 品質を保つための前提です。Codex 1 スレッドで全体を持つのはもう危険寄りなので、今後は `責務境界ごとに別スレッド` を基本運用にしたほうがよいです。

## Review 2026-03-22 operating model change check

### Findings

1. 運用形態の方向自体は正しく、レビュー内容もある程度は実装と記録に読まれています。対象: [`SHARE_NOTE.md:10`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L10) [`SHARE_NOTE.md:109`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L109) [`SHARE_NOTE.md:154`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L154) [`src/web/app.py:261`](/home/hiromu/projects/ai_core/src/web/app.py#L261) [`src/web/app.py:270`](/home/hiromu/projects/ai_core/src/web/app.py#L270)
   - なぜそう感じるか: `reflected in records: yes` が明示され、実際に Web UI では以前のレビュー観点だった状態表示追加と debug 折りたたみが反映されています。
   - 改善案: この `レビュー所見 -> 実装反映 -> SHARE_NOTE で反映確認` の流れは維持でよいです。

2. ただし、並列運用が本当にうまく回っているかはまだ未証明です。対象: [`OPERATIONS_DRAFT.md:18`](/home/hiromu/projects/ai_core/OPERATIONS_DRAFT.md#L18) [`OPERATIONS_DRAFT.md:31`](/home/hiromu/projects/ai_core/OPERATIONS_DRAFT.md#L31) [`SHARE_NOTE.md:17`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L17) [`SHARE_NOTE.md:177`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L177)
   - なぜそう感じるか: 運用草案では `1スレッド = 1層 + 1目的` と worker 分割を定義していますが、今回の実装ターンは Web, driver, core helper, README, test, 運用文書まで横断しており、しかも `worker/drivers-handoff`, `worker/web-ui` は未提出と書かれています。
   - 改善案: いまは `並列運用の思想は入ったが、実際の worker 提出・統合フローはまだ回っていない` と評価するのが正確です。次回は本当に 1 worker 1統合単位で 1 回まわし、その履歴を残すべきです。

3. `web/ui` の責務分離は前進したが、UI 層のサイズはまだ 1 スレッドで扱うには重めです。対象: [`MODULE_REQUIREMENTS.md:83`](/home/hiromu/projects/ai_core/MODULE_REQUIREMENTS.md#L83) [`src/web/app.py:11`](/home/hiromu/projects/ai_core/src/web/app.py#L11) [`src/web/app.py:291`](/home/hiromu/projects/ai_core/src/web/app.py#L291) [`src/web/app.py:522`](/home/hiromu/projects/ai_core/src/web/app.py#L522) [`src/web/app.py:610`](/home/hiromu/projects/ai_core/src/web/app.py#L610) [`src/web/transcription_service.py:83`](/home/hiromu/projects/ai_core/src/web/transcription_service.py#L83)
   - なぜそう感じるか: 転写本体は service に移りましたが、`src/web/app.py` にはまだ HTML/CSS, フロント JS, Flask route, request form 解釈, HTML/JSON レスポンス整形が同居しています。
   - 改善案: 次は `template/assets`, `browser recorder state`, `Flask endpoint glue` の 3 つに分けると、worker 分割の実効性が出ます。

4. テストと文書のハブは依然として大きく、運用草案どおりの ownership がまだ徹底されていません。対象: [`OPERATIONS_DRAFT.md:127`](/home/hiromu/projects/ai_core/OPERATIONS_DRAFT.md#L127) [`OPERATIONS_DRAFT.md:249`](/home/hiromu/projects/ai_core/OPERATIONS_DRAFT.md#L249) [`SHARE_NOTE.md:17`](/home/hiromu/projects/ai_core/SHARE_NOTE.md#L17)
   - なぜそう感じるか: 草案では `README.md` と `smoke_test.py` は docs/tests か統合担当へ寄せる前提ですが、最新ターンではこれらが Web, driver, core 変更と同じ単位で更新されています。
   - 改善案: `README.md` と `smoke_test.py` は本当に別担当へ寄せるか、少なくとも統合時にだけ触るルールにしたほうがよいです。

### UX issues

- 運用面の役割分離は見え始めていますが、利用者向けの体験改善と構造改善がまだ同じターンで混ざりやすいです。
  改善案: `UI見た目`, `状態表示`, `service分離`, `docs/tests` を別ターンに切る。

- `そもそも読んでもらえるか` については、現状は `読まれてはいるが、仕組みで保証されてはいない` 状態です。
  改善案: 統合担当が毎回 `今回どのレビュー所見を反映したか` を 3 行程度で固定フォーマット化するとよいです。

### Visual issues

- Web UI は状態表示や debug 退避で改善しましたが、構造分離が途中なので、まだ `保守 UI と実装面が密結合した画面` に見えます。対象: [`src/web/app.py:261`](/home/hiromu/projects/ai_core/src/web/app.py#L261) [`src/web/app.py:291`](/home/hiromu/projects/ai_core/src/web/app.py#L291)
  改善案: 状態表示はこのまま伸ばしつつ、template と recorder script を切ることで UI の完成度も上げやすくする。

### Suggested improvements

今すぐやること:

- 並列運用の評価は `成功` ではなく `試運転中` と明記する。
- 次の 1 ターンは本当に `1 worker = 1統合単位` で実施する。
- `README.md` と `smoke_test.py` を他責務の実装と同時に触らない。
- `src/web/app.py` の次の分解単位を決める。

後でやること:

- worker 提出から統合までの実績ログを残す。
- `レビュー所見 -> 反映項目` の固定フォーマットを作る。
- `web/ui`, `docs/tests`, `drivers/handoff` の ownership を実運用でも守れるか観察する。

### Short summary

運用変更の考え方は正しく、レビューも実際に一部読まれて反映されています。ただし、現時点では `並列運用がうまくいっている` とまではまだ言えません。いま起きているのは `設計思想の導入` と `部分的な責務分離の成功` で、worker ベースの実運用はこれから本当に試される段階です。

## Review 2026-03-22 maintenance UI and voice-to-agent guidance check

### Findings

1. maintenance UI としては前進していますが、主導線はまだ `録音して agent へ渡す` より `転写フォーム` に見えます。対象: [`src/web/app.py:199`](/home/hiromu/projects/ai_core/src/web/app.py#L199) [`src/web/app.py:203`](/home/hiromu/projects/ai_core/src/web/app.py#L203) [`src/web/app.py:233`](/home/hiromu/projects/ai_core/src/web/app.py#L233) [`src/web/app.py:280`](/home/hiromu/projects/ai_core/src/web/app.py#L280)
   - なぜそう感じるか: README では `voice capture -> transcript -> handoff -> agent backend` を主目的として明示できていますが、Web UI の見え方は依然として `ファイルアップロード / 録音 / 結果表示` の三分割で、handoff や次アクションが主役になっていません。
   - 改善案: 上部を `録音して handoff を作る` ヒーローに寄せ、結果カードの直下に `prompt を使う`, `latest handoff を取る`, `agent に渡す` の次アクションを置く。

2. `Quick / Advanced / Debug` の分離はまだ不十分です。対象: [`src/web/app.py:209`](/home/hiromu/projects/ai_core/src/web/app.py#L209) [`src/web/app.py:216`](/home/hiromu/projects/ai_core/src/web/app.py#L216) [`src/web/app.py:219`](/home/hiromu/projects/ai_core/src/web/app.py#L219) [`src/web/app.py:240`](/home/hiromu/projects/ai_core/src/web/app.py#L240) [`src/web/app.py:250`](/home/hiromu/projects/ai_core/src/web/app.py#L250) [`src/web/app.py:270`](/home/hiromu/projects/ai_core/src/web/app.py#L270)
   - なぜそう感じるか: debug は折りたたまれましたが、通常利用では毎回不要な `model`, `language`, `instruction_only`, `save_handoff` がまだ主操作と同じ面にあります。maintenance UI としては許容範囲でも、素早さはまだ出ません。
   - 改善案: 初期表示は `録音開始` または `音声ファイルを試す` だけを見せ、詳細設定を `Advanced` にまとめる。

3. 状態表示は以前より自然になったが、`voice-to-agent` の流れとしては 1 段足りません。対象: [`src/web/app.py:261`](/home/hiromu/projects/ai_core/src/web/app.py#L261) [`src/web/app.py:383`](/home/hiromu/projects/ai_core/src/web/app.py#L383) [`src/web/app.py:399`](/home/hiromu/projects/ai_core/src/web/app.py#L399)
   - なぜそう感じるか: `待機中 / 録音中 / アップロード中 / 文字起こし中 / 完了 / エラー` は maintenance UI として有効ですが、handoff 保存や agent 連携が見えないため、フローが `transcribe done` で止まって見えます。
   - 改善案: `handoff 保存済み` と `agent 送信待ち` を追加するか、少なくとも完了後に `次は handoff を使う` 導線を明示する。

4. README の入口導線はかなり改善しており、構成意図は以前より伝わります。対象: [`README.md:3`](/home/hiromu/projects/ai_core/README.md#L3) [`README.md:7`](/home/hiromu/projects/ai_core/README.md#L7) [`README.md:14`](/home/hiromu/projects/ai_core/README.md#L14) [`README.md:74`](/home/hiromu/projects/ai_core/README.md#L74)
   - なぜそう感じるか: `What This Is` と `Start Here` が先頭に来たことで、主目的と最短導線はかなり読めるようになりました。
   - 改善案: README の改善方針は維持でよいです。ただし Web UI 節にも `maintenance UI であり、voice-to-agent の確認面である` ことをもう一段はっきり書くとさらに噛み合います。

### UX issues

- `指示草案を優先して返す` は、まだ checkbox の一機能に見えます。対象: [`src/web/app.py:219`](/home/hiromu/projects/ai_core/src/web/app.py#L219) [`src/web/app.py:250`](/home/hiromu/projects/ai_core/src/web/app.py#L250)
  改善案: `Transcript`, `Instruction`, `Handoff` の目的選択として見せる。

- 結果エリアが `読んで終わり` に見えます。対象: [`src/web/app.py:280`](/home/hiromu/projects/ai_core/src/web/app.py#L280) [`src/web/app.py:284`](/home/hiromu/projects/ai_core/src/web/app.py#L284)
  改善案: 保存先表示だけでなく、利用アクションを並べる。

### Visual issues

- 見た目は整っているが、まだ `console` より `管理フォーム` に寄っています。対象: [`src/web/app.py:202`](/home/hiromu/projects/ai_core/src/web/app.py#L202) [`src/web/app.py:280`](/home/hiromu/projects/ai_core/src/web/app.py#L280)
  改善案: 録音導線と結果導線だけを一段強くし、設定面は静かにする。

- 英語ラベルが一部残り、maintenance UI としては少し試作感があります。対象: [`src/web/app.py:282`](/home/hiromu/projects/ai_core/src/web/app.py#L282) [`src/web/app.py:284`](/home/hiromu/projects/ai_core/src/web/app.py#L284)
  改善案: 表示ラベルは日本語へ寄せる。

### Suggested improvements

今すぐやること:

- Web UI の主導線を `録音して handoff を作る` に寄せる。
- `Quick / Advanced / Debug` を明示する。
- 完了後の `次にすること` を結果カードに出す。
- `Instruction draft` / `Saved payload` などの表示ラベルを日本語へ寄せる。

後でやること:

- `Transcript / Instruction / Handoff` のモード UI を用意する。
- `voice-to-agent console` として、handoff 保存から agent 利用までの流れを画面上で完結させる。
- README の Web UI 節を、maintenance UI の役割に合わせて少し補強する。

### Short summary

maintenance UI としての使いやすさは前進しています。特に状態表示と README 入口は良くなっています。ただし、まだ `voice-to-agent console` としては弱く、現状の見え方は `転写フォーム + 状態表示` に留まります。次に効くのは、主導線を handoff 利用まで伸ばすことと、`Quick / Advanced / Debug` をはっきり分けることです。

## Review 2026-03-22 quick advanced debug split check

### Findings

1. `Quick / Advanced / Debug` の分離は今回かなり効いており、maintenance UI としての初速は明確に改善しました。対象: [`src/web/app.py:486`](/home/hiromu/projects/ai_core/src/web/app.py#L486) [`src/web/app.py:517`](/home/hiromu/projects/ai_core/src/web/app.py#L517) [`src/web/app.py:551`](/home/hiromu/projects/ai_core/src/web/app.py#L551) [`src/web/app.py:588`](/home/hiromu/projects/ai_core/src/web/app.py#L588) [`src/web/app.py:621`](/home/hiromu/projects/ai_core/src/web/app.py#L621)
   - なぜそう感じるか: 通常操作では `音声ファイルを選ぶ / 実行する`, `録音開始 / 停止 / 進行を見る` に絞られ、debug は完全に折りたたみへ退避しました。以前より判断コストがかなり下がっています。
   - 改善案: この方向は維持でよいです。次は Quick 内の文言をさらに短くし、1 画面での読み量をもう少し削るとより軽くなります。

2. 初期表示で `録音`, `アップロード`, `結果` が主役になっており、狙いは達成に近いです。対象: [`src/web/app.py:430`](/home/hiromu/projects/ai_core/src/web/app.py#L430) [`src/web/app.py:454`](/home/hiromu/projects/ai_core/src/web/app.py#L454) [`src/web/app.py:631`](/home/hiromu/projects/ai_core/src/web/app.py#L631)
   - なぜそう感じるか: Hero, Maintenance Status, 2 レーン, Result Center の順で流れが整理され、通常利用者がまず見る面は明確になりました。
   - 改善案: さらに寄せるなら、Hero で `録音を試す` を最も強い CTA として出すと、主導線はもっと一本化できます。

3. 開発者向け情報は通常導線をほぼ邪魔しなくなりましたが、上段の `Maintenance Status` は少し運用者向け情報が強すぎます。対象: [`src/web/app.py:454`](/home/hiromu/projects/ai_core/src/web/app.py#L454) [`src/web/app.py:462`](/home/hiromu/projects/ai_core/src/web/app.py#L462)
   - なぜそう感じるか: `現在の入力モード`, `録音ステータス`, `最新の結果`, `次アクション` は有益ですが、通常操作の前に 4 カードが来るため、Quick レーンよりステータス面の圧が少し強いです。
   - 改善案: `Maintenance Status` は 2 カード程度へ圧縮するか、モバイルでは折りたためる形にして、入力レーンをより前面に出す。

4. `voice-to-agent console` としては一歩前進したが、`Result Center` のラベルとアクションはまだ少し試作感があります。対象: [`src/web/app.py:631`](/home/hiromu/projects/ai_core/src/web/app.py#L631) [`src/web/app.py:648`](/home/hiromu/projects/ai_core/src/web/app.py#L648) [`src/web/app.py:709`](/home/hiromu/projects/ai_core/src/web/app.py#L709)
   - なぜそう感じるか: 結果集約と `次アクション` は良い改善ですが、`Result Center`, `Instruction draft`, `Saved payload`, `transcript をコピー` などの英日混在が残っており、操作面としての一貫性がもう少し欲しいです。
   - 改善案: UI ラベルを日本語へ寄せ、`次に使う`, `handoff を確認`, `instruction をコピー` を利用目的ベースの表現にすると完成度が上がります。

### UX issues

- Quick の説明文は丁寧ですが、maintenance UI としてはやや長めです。
  改善案: 1 カード 1 文に近づけ、読まなくても押せる密度にする。

- `最新 handoff を再確認` は行動として良いが、誰向けの何を確認するのかが少し抽象的です。対象: [`src/web/app.py:651`](/home/hiromu/projects/ai_core/src/web/app.py#L651)
  改善案: `最新 handoff を取得` や `保存済み handoff を確認` のように、返る結果を明示する。

### Visual issues

- 全体の密度整理は改善しましたが、Hero と Maintenance Status の情報量はまだやや多いです。対象: [`src/web/app.py:430`](/home/hiromu/projects/ai_core/src/web/app.py#L430) [`src/web/app.py:454`](/home/hiromu/projects/ai_core/src/web/app.py#L454)
  改善案: Hero カード数を 2 に減らすか、Status カードを減らして重心を入力レーンへ寄せる。

- 英日混在は前回と同じく少し残っています。対象: [`src/web/app.py:437`](/home/hiromu/projects/ai_core/src/web/app.py#L437) [`src/web/app.py:457`](/home/hiromu/projects/ai_core/src/web/app.py#L457) [`src/web/app.py:634`](/home/hiromu/projects/ai_core/src/web/app.py#L634)
  改善案: maintenance UI として見せるなら、UI ラベルはどちらかに統一する。

### Suggested improvements

今すぐやること:

- `Maintenance Status` のカード数を少し絞る。
- `Result Center` と結果アクションのラベルを日本語へ寄せる。
- Quick の説明文を一段短くする。

後でやること:

- Hero の主 CTA をさらに強くする。
- `voice-to-agent console` として、handoff 利用までの行動をもっと前面に出す。
- モバイル時の情報順を再調整し、Status より入力レーンを優先表示する。

### Short summary

今回の小変更は有効です。`Quick / Advanced / Debug` 分離は効いており、初期表示で `録音`, `アップロード`, `結果` を主役にする狙いはかなり達成できています。残る課題は、運用ステータス面を少し軽くすることと、`Result Center` 周辺のラベルと次アクションをより完成品らしく揃えることです。
