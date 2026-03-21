"""Helpers for packaging and saving Codex-ready instruction payloads."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.core.llm import build_codex_instruction


@dataclass(frozen=True)
class CodexPayload:
    """A small reusable payload for downstream Codex integration."""

    transcript: str
    command: str


@dataclass(frozen=True)
class CodexSavedPaths:
    """Saved file paths for a Codex handoff bundle."""

    json_path: Path
    text_path: Path


def get_default_codex_output_path(source: str = "manual") -> Path:
    """Return a project-local default path for saved Codex payloads."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / ".cache" / "codex" / f"{source}_latest.json"


def get_default_codex_text_path(source: str = "manual") -> Path:
    """Return a project-local default path for saved Codex instruction text."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / ".cache" / "codex" / f"{source}_latest.txt"


def build_codex_payload(transcript: str) -> CodexPayload | None:
    """Build a Codex payload from transcribed text."""
    draft = build_codex_instruction(transcript)
    if draft is None:
        return None
    return CodexPayload(
        transcript=draft.transcript,
        command=draft.instruction,
    )


def render_codex_prompt(transcript: str) -> str | None:
    """Render a minimal prompt text that can be handed to Codex."""
    payload = build_codex_payload(transcript)
    if payload is None:
        return None
    return (
        "Voice transcript:\n"
        f"{payload.transcript}\n\n"
        "Requested task:\n"
        f"{payload.command}\n"
    )


def save_codex_payload(transcript: str, output_path: Path) -> Path | None:
    """Save a Codex payload as JSON and return the written path."""
    payload = build_codex_payload(transcript)
    if payload is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def save_codex_instruction_text(transcript: str, output_path: Path) -> Path | None:
    """Save a Codex-ready prompt text."""
    prompt_text = render_codex_prompt(transcript)
    if prompt_text is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt_text, encoding="utf-8")
    return output_path


def save_codex_handoff_bundle(
    transcript: str,
    json_path: Path,
    text_path: Path,
) -> CodexSavedPaths | None:
    """Save both JSON and plain-text Codex handoff files."""
    saved_json_path = save_codex_payload(transcript, json_path)
    saved_text_path = save_codex_instruction_text(transcript, text_path)
    if saved_json_path is None or saved_text_path is None:
        return None
    return CodexSavedPaths(
        json_path=saved_json_path,
        text_path=saved_text_path,
    )
