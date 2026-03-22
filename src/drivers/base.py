"""Common driver request/result contracts for backend dispatch."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess

from src.io.audio import AudioInputError
from src.runners.common import validate_runner_command_available


@dataclass(frozen=True)
class DriverRequest:
    """Normalized input for one backend dispatch."""

    backend_name: str
    command: list[str]
    payload: str


@dataclass(frozen=True)
class DriverResult:
    """Normalized subprocess result for one backend dispatch."""

    backend_name: str
    command: list[str]
    payload: str
    returncode: int
    stdout: str
    stderr: str


def dispatch_driver_request(request: DriverRequest) -> DriverResult:
    """Validate and execute one backend request via subprocess."""
    validate_runner_command_available(request.command)
    try:
        completed = subprocess.run(
            request.command,
            input=request.payload,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AudioInputError(f"runner command not found: {exc.filename}") from exc
    return DriverResult(
        backend_name=request.backend_name,
        command=request.command,
        payload=request.payload,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
