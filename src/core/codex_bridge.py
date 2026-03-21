"""Compatibility wrapper around the generic handoff bridge."""

from src.core.handoff_bridge import (
    HandoffBundle as CodexHandoff,
    HandoffPayload as CodexPayload,
    HandoffSavedPaths as CodexSavedPaths,
    build_handoff_payload as build_codex_payload,
    get_default_handoff_output_path as get_default_codex_output_path,
    get_default_handoff_text_path as get_default_codex_text_path,
    load_handoff_bundle as load_codex_handoff_bundle,
    render_handoff_prompt as render_codex_prompt,
    save_handoff_bundle as save_codex_handoff_bundle,
    save_handoff_payload as save_codex_payload,
    save_handoff_prompt_text as save_codex_instruction_text,
)

__all__ = [
    "CodexHandoff",
    "CodexPayload",
    "CodexSavedPaths",
    "build_codex_payload",
    "get_default_codex_output_path",
    "get_default_codex_text_path",
    "load_codex_handoff_bundle",
    "render_codex_prompt",
    "save_codex_handoff_bundle",
    "save_codex_instruction_text",
    "save_codex_payload",
]
