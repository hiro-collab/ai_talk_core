"""Shared helpers for external runner CLIs."""

from __future__ import annotations

import sys

from src.drivers.base import DriverResult, validate_runner_command_available


def normalize_command_args(command: list[str]) -> list[str]:
    """Normalize a remainder command after an optional '--' separator."""
    if command and command[0] == "--":
        return command[1:]
    return command


def emit_driver_result(result: DriverResult) -> int:
    """Print normalized backend output and return the process exit code."""
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode
