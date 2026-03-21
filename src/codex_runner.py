"""CLI bridge for piping the latest Codex handoff into another command."""

from __future__ import annotations

import argparse
import subprocess

from src.codex_handoff import render_handoff_output
from src.io.audio import AudioInputError


def build_parser() -> argparse.ArgumentParser:
    """Build the Codex runner CLI parser."""
    parser = argparse.ArgumentParser(
        description="Pipe the latest Codex handoff prompt into another command."
    )
    parser.add_argument(
        "--source",
        default="web",
        help="Handoff source name. Default: web",
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
        help="Print the rendered handoff instead of running a command.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to receive the handoff on stdin.",
    )
    return parser


def normalize_command_args(command: list[str]) -> list[str]:
    """Normalize a remainder command after an optional '--' separator."""
    if command and command[0] == "--":
        return command[1:]
    return command


def main() -> int:
    """Run the Codex handoff runner."""
    args = build_parser().parse_args()
    try:
        payload = render_handoff_output(args.source, args.format)
    except AudioInputError as exc:
        print(f"Input error: {exc}")
        return 1

    command = normalize_command_args(args.command)
    if args.print_only or not command:
        print(payload)
        return 0

    completed = subprocess.run(
        command,
        input=payload,
        text=True,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
