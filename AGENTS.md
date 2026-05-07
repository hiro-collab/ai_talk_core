# Repository Guide

This repository contains the `ai-talk-core` module: a local Python audio-to-agent handoff boundary.

## Structure

- `src/main.py`: CLI for file transcription, microphone capture, mic-loop, diagnostics, and handoff output.
- `src/core/`: backend-neutral pipeline, session, finalization, input gate, handoff, status, and instruction logic.
- `src/io/`: host-dependent audio, microphone, ffmpeg, Torch, Whisper, and VAD helpers.
- `src/web/`: Flask maintenance UI, JSON API, static assets, and Web transcription service.
- `src/runners/`: handoff-to-command runner implementations.
- `data/`: small sample inputs.
- `docs/`: module responsibility, integration contract, and retired-path summaries.

Runtime output belongs under `.cache/`, `.venv/`, or `models/`; do not treat those paths as source.

## Commands

```bash
uv sync
uv run python -m src.main --doctor
uv run python -m src.main data/sample_audio.mp3 --language ja
uv run python -m src.web.app
uv run python smoke_test.py
```

Windows helper:

```powershell
.\start_web.ps1
```

The project expects `ffmpeg` on `PATH`. Ubuntu microphone capture also needs `arecord` from `alsa-utils`. GPU acceleration is optional; Whisper may fall back to CPU.

## Style

Use idiomatic Python with 4-space indentation and type hints where they clarify boundaries. Keep CLI and Flask route code thin; put reusable behavior in `src/core/`, `src/io/`, `src/web/transcription_service.py`, or `src/runners/` as appropriate.

Preserve stdout/stderr separation. Machine-readable output, handoff payloads, and JSON responses must not be mixed with diagnostic prose.

## Verification

Run `uv run python smoke_test.py` before changing CLI, Web API, handoff, runner, or transcription flow behavior. Add focused assertions near the affected path when broadening behavior.

Manual browser-recording checks are still useful for UI changes because repeated MediaRecorder runs depend on real browser behavior.

## Documentation

Keep README short. Requirements, responsibility boundaries, connection contracts, and retired paths are separated:

- `MODULE_REQUIREMENTS.md`
- `docs/module-responsibilities.md`
- `docs/integration-contract.md`
- `docs/retired-paths.md`

Files under `archive/` are historical records. Do not cite them as active instructions unless a human explicitly asks for archaeology.
