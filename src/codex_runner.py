"""CLI bridge for piping the latest Codex handoff into another command."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from src.codex_handoff import render_handoff_output
from src.io.audio import AudioInputError


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


def normalize_command_args(command: list[str]) -> list[str]:
    """Normalize a remainder command after an optional '--' separator."""
    if command and command[0] == "--":
        return command[1:]
    return command


def resolve_runner_command(template: str | None, command: list[str], workdir: Path) -> list[str]:
    """Resolve the effective command from a template or explicit args."""
    manual_command = normalize_command_args(command)
    if template is not None:
        return build_template_command(template, workdir)
    return manual_command


def validate_runner_command_available(command: list[str]) -> None:
    """Validate that the target command is available before execution."""
    if not command:
        return
    executable = command[0]
    if "/" in executable:
        if not Path(executable).exists():
            raise AudioInputError(f"runner command not found: {executable}")
        return
    if shutil.which(executable) is None:
        raise AudioInputError(f"runner command not found in PATH: {executable}")


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


if __name__ == "__main__":
    raise SystemExit(main())
