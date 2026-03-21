"""CLI bridge for piping the latest handoff into an Ollama model."""

from __future__ import annotations

import argparse
import subprocess

from src.io.audio import AudioInputError
from src.runners.common import validate_runner_command_available
from src.runners.handoff import render_handoff_output


def build_ollama_command(model: str) -> list[str]:
    """Build the Ollama run command for a model name."""
    normalized_model = model.strip()
    if not normalized_model:
        raise AudioInputError("Ollama model name must not be blank")
    return ["ollama", "run", normalized_model]


def build_parser() -> argparse.ArgumentParser:
    """Build the Ollama runner CLI parser."""
    parser = argparse.ArgumentParser(
        description="Pipe the latest saved handoff prompt into Ollama."
    )
    parser.add_argument("--source", default="web", help="Handoff source name. Default: web")
    parser.add_argument(
        "--model",
        required=True,
        help="Ollama model name, for example llama3 or qwen2.5.",
    )
    parser.add_argument(
        "--format",
        choices=("prompt", "command", "json"),
        default="prompt",
        help="Handoff view to send. Default: prompt",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the rendered handoff instead of running Ollama.",
    )
    return parser


def main() -> int:
    """Run the Ollama handoff bridge."""
    args = build_parser().parse_args()
    try:
        payload = render_handoff_output(args.source, args.format)
        command = build_ollama_command(args.model)
        if args.print_only:
            print(payload)
            return 0
        validate_runner_command_available(command)
    except AudioInputError as exc:
        print(f"Input error: {exc}")
        return 1

    try:
        completed = subprocess.run(
            command,
            input=payload,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        print(f"Input error: runner command not found: {exc.filename}")
        return 1
    return completed.returncode
