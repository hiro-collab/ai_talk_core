"""Shared helpers for external runner CLIs."""

from __future__ import annotations

import sys

from src.drivers import (
    DriverRequest,
    DriverResult,
    dispatch_driver_request,
    validate_driver_command_available,
)


def normalize_command_args(command: list[str]) -> list[str]:
    """Normalize a remainder command after an optional '--' separator."""
    if command and command[0] == "--":
        return command[1:]
    return command


def validate_runner_command_available(command: list[str]) -> None:
    """Validate that the target command is available before execution."""
    validate_driver_command_available(command)


def execute_runner_command(backend_name: str, command: list[str], payload: str) -> DriverResult:
    """Build and dispatch one normalized backend request for runner CLIs."""
    return dispatch_driver_request(
        DriverRequest(
            backend_name=backend_name,
            command=command,
            payload=payload,
        )
    )


def emit_driver_result(result: DriverResult) -> int:
    """Print normalized backend output and return the process exit code."""
    response = result.response
    if not response.has_output:
        return response.returncode
    if response.stream == "stdout":
        print(response.text, end="")
        if response.stderr_text:
            print(response.stderr_text, end="", file=sys.stderr)
        return response.returncode
    if response.stream == "stderr":
        print(response.text, end="", file=sys.stderr)
        return response.returncode
    return response.returncode
