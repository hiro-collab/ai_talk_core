"""Common driver request/result contracts for backend dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
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
class DriverResponse:
    """Backend-neutral response view for downstream runner consumers."""

    backend_name: str
    command_name: str
    command_line: str
    returncode: int
    status: str
    succeeded: bool
    has_output: bool
    stdout_text: str
    stderr_text: str
    stream: str
    text: str


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

    @property
    def status(self) -> str:
        """Return a backend-neutral execution status label."""
        if self.succeeded:
            return "ok" if self.has_output else "ok_no_output"
        return "error" if self.has_output else "error_no_output"

    @property
    def response_stream(self) -> str:
        """Return the preferred output stream name for backend-neutral consumers."""
        if self.stdout:
            return "stdout"
        if self.stderr:
            return "stderr"
        return ""

    @property
    def response_text(self) -> str:
        """Return the preferred response text for backend-neutral consumers."""
        if self.stdout:
            return self.stdout
        if self.stderr:
            return self.stderr
        return ""

    @property
    def command_line(self) -> str:
        """Return a display-ready command line for backend-neutral consumers."""
        return shlex.join(self.command)

    @property
    def response(self) -> DriverResponse:
        """Return a backend-neutral response view for downstream consumers."""
        return DriverResponse(
            backend_name=self.backend_name,
            command_name=self.command_name,
            command_line=self.command_line,
            returncode=self.returncode,
            status=self.status,
            succeeded=self.succeeded,
            has_output=self.has_output,
            stdout_text=self.stdout,
            stderr_text=self.stderr,
            stream=self.response_stream,
            text=self.response_text,
        )


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


def dispatch_driver_request(request: DriverRequest) -> DriverResult:
    """Validate and execute one backend request via subprocess."""
    validate_driver_command_available(request.command)
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
