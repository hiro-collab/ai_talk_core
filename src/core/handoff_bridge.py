"""Generic handoff helpers for packaging and saving instruction payloads."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.core.llm import build_codex_instruction


@dataclass(frozen=True)
class HandoffPayload:
    """A small reusable payload for downstream agent integration."""

    transcript: str
    command: str


@dataclass(frozen=True)
class HandoffSavedPaths:
    """Saved file paths for one handoff bundle."""

    json_path: Path
    text_path: Path


@dataclass(frozen=True)
class HandoffBundle:
    """Loaded handoff bundle contents."""

    transcript: str
    command: str
    prompt_text: str
    json_path: Path
    text_path: Path


def get_default_handoff_output_path(source: str = "manual") -> Path:
    """Return a project-local default path for saved handoff JSON."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / ".cache" / "codex" / f"{source}_latest.json"


def get_default_handoff_text_path(source: str = "manual") -> Path:
    """Return a project-local default path for saved handoff prompt text."""
    project_root = Path(__file__).resolve().parents[2]
    return project_root / ".cache" / "codex" / f"{source}_latest.txt"


def build_handoff_payload(transcript: str) -> HandoffPayload | None:
    """Build a handoff payload from transcribed text."""
    draft = build_codex_instruction(transcript)
    if draft is None:
        return None
    return HandoffPayload(
        transcript=draft.transcript,
        command=draft.instruction,
    )


def render_handoff_prompt(transcript: str) -> str | None:
    """Render a minimal prompt text that can be handed to an external agent."""
    payload = build_handoff_payload(transcript)
    if payload is None:
        return None
    return (
        "Voice transcript:\n"
        f"{payload.transcript}\n\n"
        "Requested task:\n"
        f"{payload.command}\n"
    )


def save_handoff_payload(transcript: str, output_path: Path) -> Path | None:
    """Save a handoff payload as JSON and return the written path."""
    payload = build_handoff_payload(transcript)
    if payload is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def save_handoff_prompt_text(transcript: str, output_path: Path) -> Path | None:
    """Save a handoff-ready prompt text."""
    prompt_text = render_handoff_prompt(transcript)
    if prompt_text is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prompt_text, encoding="utf-8")
    return output_path


def save_handoff_bundle(
    transcript: str,
    json_path: Path,
    text_path: Path,
) -> HandoffSavedPaths | None:
    """Save both JSON and plain-text handoff files."""
    saved_json_path = save_handoff_payload(transcript, json_path)
    saved_text_path = save_handoff_prompt_text(transcript, text_path)
    if saved_json_path is None or saved_text_path is None:
        return None
    return HandoffSavedPaths(
        json_path=saved_json_path,
        text_path=saved_text_path,
    )


def load_handoff_bundle(source: str = "manual") -> HandoffBundle | None:
    """Load the latest saved handoff bundle for a source."""
    json_path = get_default_handoff_output_path(source=source)
    text_path = get_default_handoff_text_path(source=source)
    if not json_path.exists() or not text_path.exists():
        return None
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    prompt_text = text_path.read_text(encoding="utf-8")
    return HandoffBundle(
        transcript=payload["transcript"],
        command=payload["command"],
        prompt_text=prompt_text,
        json_path=json_path,
        text_path=text_path,
    )
