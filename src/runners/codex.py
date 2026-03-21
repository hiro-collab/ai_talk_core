"""CLI bridge for piping the latest handoff prompt into Codex or another command."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from src.io.audio import AudioInputError
from src.runners.common import normalize_command_args, validate_runner_command_available
from src.runners.handoff import render_handoff_output


STATIC_TEMPLATES: dict[str, list[str]] = {
    "cat": ["cat"],
    "python-stdin": ["python", "-c", "import sys; print(sys.stdin.read())"],
}


def build_template_command(template: str, workdir: Path) -> list[str]:
    """Build one of the supported runner template commands."""
    if template in STATIC_TEMPLATES:
        return STATIC_TEMPLATES[template]
    if template == "codex-exec":
        return ["codex", "exec", "-C", str(workdir), "-"]
    raise AudioInputError(f"unknown runner template: {template}")


def build_parser() -> argparse.ArgumentParser:
    """Build the Codex runner CLI parser."""
    parser = argparse.ArgumentParser(
        description="Pipe the latest handoff prompt into another command."
    )
    parser.add_argument("--source", default="web", help="Handoff source name. Default: web")
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
        "--template",
        choices=("cat", "python-stdin", "codex-exec"),
        default=None,
        help="Use a built-in command template instead of a manual command.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to receive the handoff on stdin.",
    )
    return parser


def resolve_runner_command(template: str | None, command: list[str], workdir: Path) -> list[str]:
    """Resolve the effective command from a template or explicit args."""
    manual_command = normalize_command_args(command)
    if template is not None:
        return build_template_command(template, workdir)
    return manual_command


def main() -> int:
    """Run the Codex handoff runner."""
    args = build_parser().parse_args()
    try:
        payload = render_handoff_output(args.source, args.format)
        command = resolve_runner_command(args.template, args.command, Path.cwd())
        validate_runner_command_available(command)
    except AudioInputError as exc:
        print(f"Input error: {exc}")
        return 1

    if args.print_only or not command:
        print(payload)
        return 0

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
