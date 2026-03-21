"""Compatibility wrapper for the generic agent instruction builder."""

from src.core.agent_instruction import (
    AgentInstructionDraft as CodexInstructionDraft,
    build_agent_instruction as build_codex_instruction,
    normalize_instruction_text,
)

__all__ = [
    "CodexInstructionDraft",
    "build_codex_instruction",
    "normalize_instruction_text",
]
