"""Common driver request/result contracts for backend dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from src.io.audio import AudioInputError


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
    command_name: str

    @property
    def succeeded(self) -> bool:
        """Return True when the backend process exited successfully."""
        return self.returncode == 0

    @property
    def has_output(self) -> bool:
        """Return True when either stdout or stderr contains content."""
        return bool(self.stdout or self.stderr)


def validate_driver_command_available(command: list[str]) -> None:
    """Validate that the backend command is available before execution."""
    if not command:
        return
    executable = command[0]
    if "/" in executable:
        if not Path(executable).exists():
            raise AudioInputError(f"runner command not found: {executable}")
        return
    if shutil.which(executable) is None:
        raise AudioInputError(f"runner command not found in PATH: {executable}")


def validate_runner_command_available(command: list[str]) -> None:
    """Compatibility alias for existing runner command validation callers."""
    validate_driver_command_available(command)


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
        command_name=request.command[0] if request.command else "",
    )
