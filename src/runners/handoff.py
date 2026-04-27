"""Shared CLI helpers for reading the latest saved handoff bundle."""

from __future__ import annotations

import argparse
import json

from src.core.handoff_bridge import load_handoff_bundle
from src.io.audio import AudioInputError


def build_parser() -> argparse.ArgumentParser:
    """Build the shared handoff reader CLI parser."""
    parser = argparse.ArgumentParser(
        description="Read the latest saved handoff bundle."
    )
    parser.add_argument(
        "--source",
        default="web",
        help="Handoff source name. Default: web",
    )
    parser.add_argument(
        "--format",
        choices=("prompt", "command", "json-path", "text-path", "json"),
        default="prompt",
        help="Output format. Default: prompt",
    )
    return parser


def render_handoff_output(source: str, output_format: str) -> str:
    """Render one view of the latest handoff bundle."""
    try:
        handoff = load_handoff_bundle(source=source)
    except ValueError as exc:
        raise AudioInputError(str(exc)) from exc
    if handoff is None:
        raise AudioInputError(f"handoff not found for source: {source}")
    if output_format == "prompt":
        return handoff.prompt_text.rstrip("\n")
    if output_format == "command":
        return handoff.command
    if output_format == "json-path":
        return str(handoff.json_path)
    if output_format == "text-path":
        return str(handoff.text_path)
    return json.dumps(
        {
            "transcript": handoff.transcript,
            "command": handoff.command,
            "prompt_text": handoff.prompt_text,
            "command_path": str(handoff.json_path),
            "command_text_path": str(handoff.text_path),
            "source": source,
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> int:
    """Run the shared handoff reader CLI."""
    args = build_parser().parse_args()
    try:
        print(render_handoff_output(args.source, args.format))
    except AudioInputError as exc:
        print(f"Input error: {exc}")
        return 1
    return 0
