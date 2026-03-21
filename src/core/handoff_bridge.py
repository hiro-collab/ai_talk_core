"""Generic handoff helpers layered on top of the current bundle format."""

from src.core.codex_bridge import (
    CodexHandoff as HandoffBundle,
    CodexPayload as HandoffPayload,
    CodexSavedPaths as HandoffSavedPaths,
    build_codex_payload as build_handoff_payload,
    get_default_codex_output_path as get_default_handoff_output_path,
    get_default_codex_text_path as get_default_handoff_text_path,
    load_codex_handoff_bundle as load_handoff_bundle,
    render_codex_prompt as render_handoff_prompt,
    save_codex_handoff_bundle as save_handoff_bundle,
    save_codex_instruction_text as save_handoff_prompt_text,
    save_codex_payload as save_handoff_payload,
)

__all__ = [
    "HandoffBundle",
    "HandoffPayload",
    "HandoffSavedPaths",
    "build_handoff_payload",
    "get_default_handoff_output_path",
    "get_default_handoff_text_path",
    "load_handoff_bundle",
    "render_handoff_prompt",
    "save_handoff_bundle",
    "save_handoff_payload",
    "save_handoff_prompt_text",
]
