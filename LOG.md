# Work Log

## 2026-03-21

- `~/ダウンロード/20260120161306_21ba1fcc9c7e0a5b.mp3` を `data/sample_audio.mp3` へ移動
- Whisper `small` モデルを `models/whisper/small.pt` に配置
- `uv run python -m src.main --help` を実行
- `uv run python -m src.main data/sample_audio.mp3 --language ja` を実行
- 文字起こし成功を確認
- GPU 利用先が `cuda:0` であることを確認
- `arecord -D plughw:2,0 -f S16_LE -c 1 -r 16000 -d 3 data/mic_test_c920.wav` を実行
- `HD Pro Webcam C920` で 3 秒の録音成功を確認
- `ffprobe` で `data/mic_test_c920.wav` が 16kHz / mono / 3.0 秒であることを確認
- `arecord -D plughw:2,0 -f S16_LE -c 1 -r 16000 -d 5 data/mic_speech_test_c920.wav` を実行
- `uv run python -m src.main data/mic_speech_test_c920.wav --language ja` を実行
- C920 からの録音を Whisper で文字起こしできることを確認
- 認識結果は崩れがあり、マイク位置や入力条件の調整余地があることを確認
- `tree -L 3 /home/hiromu` を実行し、ホーム配下の構成を確認
- `rg --files` を実行し、`~/projects/ai_core` のファイル一覧を確認
- `sed -n '1,220p' README.md` を実行し、README の内容を確認
- `sed -n '1,220p' pyproject.toml` を実行し、依存定義を確認
- `sed -n '1,220p' src/main.py` を実行し、CLI 実装を確認
- `sed -n '1,260p' src/io/audio.py` を実行し、音声処理実装を確認
- `uv run python -c "import whisper, torch; ..."` を実行し、`whisper 20250625`, `torch 2.10.0+cu128`, `cuda_available=True` を確認
- `uv run python -m src.main data/sample_audio.mp3 --language ja` を実行し、文字起こし成功を再確認
- `ls -lh models/whisper data/sample_audio.mp3` を実行し、`small.pt` が 462M、`data/sample_audio.mp3` が 126K であることを確認
- `uv run python -c "from src.io.audio import load_transcription_model; ..."` を実行し、ロードした Whisper モデルの `device` が `cuda:0` であることを確認
- `uv run python -m src.main no_such_file.wav` を実行し、`Input error: audio file not found: /home/hiromu/projects/ai_core/no_such_file.wav` を確認
- `uv run python -m src.main data/sample_audio.mp3 --model notamodel` を実行し、`Environment error: failed to load Whisper model 'notamodel': Model notamodel not found ...` を確認
- `src/main.py` で入力検証と `ffmpeg` 確認をモデルロード前に移動
- `src/io/audio.py` で `validate_model_name()` を追加
- `uv run python -m src.main data/sample_audio.mp3 --model notamodel` を再実行し、`Input error: invalid Whisper model name: notamodel` を確認
- `src/io/microphone.py` を追加し、固定時間マイク録音を実装
- `uv run python -m src.main --mic data/sample_audio.mp3` を実行し、`Input error: audio_file cannot be used together with --mic` を確認
- `uv run python -m src.main --mic --duration 5 --mic-device plughw:2,0 --language ja` を実行し、固定時間マイク録音から文字起こしまで成功することを確認
- `src/io/microphone.py` で `arecord -l` から `HD Pro Webcam C920` を優先するデフォルトデバイス選択を追加
- `uv run python -m src.main --mic --duration 5 --language ja` を実行し、`--mic-device` 省略時でも文字起こし成功を確認
- `sed -n '1,240p' REVIEWER_INSTRUCTIONS.md` を実行し、レビュー記録ルールを確認
- `sed -n '1,240p' REVIEW.md`, `SHARE_NOTE.md`, `LOG.md`, `MEMORY.md` を実行し、既存記録内容を確認
