# Repository Guidelines

## Project Structure & Module Organization

This repository is a local Python 3.11 audio-to-agent handoff system. Core source lives in `src/`:

- `src/main.py` provides the CLI for file, microphone, and mic-loop transcription.
- `src/core/` contains pipeline, handoff, session, status, and instruction-building logic.
- `src/io/` handles audio files, microphone capture, ffmpeg checks, and VAD helpers.
- `src/web/` contains the Flask maintenance UI and JSON API.
- `src/runners/` and top-level runner modules bridge saved handoffs to external agents.

Use `data/` for sample inputs such as `data/sample_audio.mp3`. Runtime outputs and transient handoff files are written under `.cache/`; do not treat them as source. Operational notes and design records are kept in root Markdown files such as `README.md`, `MODULE_REQUIREMENTS.md`, and `LOG.md`.

## Build, Test, and Development Commands

- `uv sync` installs the locked Python dependencies into the local `.venv`.
- `uv run python -m src.main data/sample_audio.mp3 --language ja` runs a quick file transcription.
- `uv run python -m src.main --mic --duration 5 --language ja` records a short microphone sample.
- `uv run python -m src.web.app` starts the Flask UI/API at `http://127.0.0.1:8000`.
- `uv run python smoke_test.py` runs the current smoke coverage for CLI, Web UI, and JSON API server behavior.

The project expects `ffmpeg` on the system path. GPU acceleration is optional; Whisper should fall back to CPU when CUDA is unavailable.

## Coding Style & Naming Conventions

Use idiomatic Python with 4-space indentation, type hints where they clarify interfaces, and short module docstrings for entry points. Keep module and function names in `snake_case`; classes use `PascalCase`. Prefer small, explicit helper functions over large procedural blocks. Preserve the existing stdout/stderr split: machine-readable payloads should not be polluted by operational notes.

## Testing Guidelines

There is no separate `tests/` package yet; `smoke_test.py` is the main verification entry point. Run it before changing CLI, web API, handoff, or transcription flow behavior. Add focused tests or smoke assertions near the affected path when introducing new behavior, and keep sample data small enough to remain practical for local runs.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries, for example `Integrate drivers handoff and web UI updates` and `Fix record advanced log path`. Follow that style: describe the user-visible change, not the implementation mechanics. PRs should include the intent, affected CLI/API paths, verification commands run, and any manual audio or browser-recording checks. Include screenshots only for visible Web UI changes.

## Security & Configuration Tips

Do not commit `.cache/`, `.venv/`, generated recordings, local Whisper model files, or machine-specific paths. Treat saved handoff payloads as potentially sensitive because they may contain transcripts or agent instructions.
