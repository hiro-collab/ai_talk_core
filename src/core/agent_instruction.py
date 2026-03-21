"""Helpers for building agent-ready instruction drafts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentInstructionDraft:
    """A minimal instruction draft derived from transcribed speech."""

    transcript: str
    instruction: str


def normalize_instruction_text(text: str) -> str:
    """Normalize transcribed speech into a compact instruction string."""
    return " ".join(text.strip().split())


def build_agent_instruction(transcript: str) -> AgentInstructionDraft | None:
    """Build an agent instruction draft from a transcript."""
    normalized = normalize_instruction_text(transcript)
    if not normalized:
        return None
    return AgentInstructionDraft(
        transcript=normalized,
        instruction=normalized,
    )
