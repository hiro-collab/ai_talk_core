"""Shared helpers for external runner CLIs."""

from __future__ import annotations

import sys
import shutil
from pathlib import Path

from src.drivers.base import DriverResult
from src.io.audio import AudioInputError


def normalize_command_args(command: list[str]) -> list[str]:
    """Normalize a remainder command after an optional '--' separator."""
    if command and command[0] == "--":
        return command[1:]
    return command


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


def emit_driver_result(result: DriverResult) -> int:
    """Print normalized backend output and return the process exit code."""
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode
