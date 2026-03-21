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

Status: partially adopted

#### Findings

- High: 無効な入力でも先に Whisper モデルをロードしており、入力エラー時にもモデル準備コストを払う実装になっている。対象: `src/main.py:41-43`, `src/io/audio.py:65-68`
- Medium: `--model notamodel` のような不正モデル名が `Input error` ではなく `Environment error` に分類される。対象: `src/io/audio.py:53-62`
- Medium: GPU 利用は現在の PC では成立しているが、その再現条件が依存定義に固定されていない。対象: `pyproject.toml:5-6`, `README.md:14-20`, `README.md:96-99`
- Low-Medium: `models/whisper` をプロジェクト直下に持つ方針は最小構成としては妥当だが、モデル増加時にコードと大容量資産が同居する運用になる。対象: `src/io/audio.py:27-32`, `README.md:78-81`
- Low: 自動確認がなく、CLI の成功系と主要失敗系が手動確認に依存している。対象: `README.md`, `src/main.py`, `src/io/audio.py`
- Low: ホーム全体の整理は概ね方針どおりだが、`~/shared`, `~/dev/zadar_ws`, `~/projects/screenworld` などに大容量バイナリや成果物があり、今後はバックアップと容量管理の切り分けが課題になる。対象: `tree -L 3 /home/hiromu` の確認結果

#### Open questions / assumptions

- 単一ユーザー・単一マシン向けのローカル CLI を前提とし、配布パッケージ化はまだ不要と仮定した
- マイク入力はまず録音ファイル経由のバッチ文字起こしで十分で、リアルタイム処理は未要求と仮定した
- ノイズ対策は一般的な室内雑音を対象とし、遠距離収音や会議室アレイまでは未対象と仮定した
- `models/whisper` をプロジェクト単位で閉じたい意図があると仮定した

#### Recommended next actions

- 1. `src/main.py` で入力パス検証と `ffmpeg` 確認をモデルロード前に移し、失敗時の無駄なモデル準備を止める
- 2. `src/io/audio.py` の例外分類を見直し、不正モデル名を入力エラーとして返す
- 3. `README.md` に CUDA 対応 Torch の再現方法、CPU fallback 条件、モデル保存方針の注意点を追記する
- 4. マイク入力追加前に、録音処理を `src/io/audio.py` から分離できる境界を決める
- 5. ノイズ対策は最初から重い denoise を入れず、`mono / 16kHz / silence trim` または VAD から始める
- 6. サンプル音声の成功系と主要失敗系の smoke test を追加する

#### Adopted

- `src/main.py` で入力ファイル検証、モデル名検証、`ffmpeg` 確認をモデルロード前に実施
- `src/io/audio.py` で不正モデル名を `Input error` に分類するよう修正
- `src/io/microphone.py` を追加し、録音処理を音声文字起こし処理から分離
- `--mic --duration` による固定時間マイク録音 CLI を追加
- `HD Pro Webcam C920` を優先するデフォルトマイク選択を追加
- README の前提条件、制約、エラー種別は整理済み

#### Open

- CUDA 対応 Torch の再現方法は README に未記載
- CPU fallback 条件の詳細は README に未記載
- モデル保存方針の注意点は追加の余地あり
- VAD / silence trim は未実装
- smoke test は未追加
