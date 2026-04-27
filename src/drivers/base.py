"""Common driver request/result contracts for backend dispatch."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from src.io.audio import AudioInputError

DEFAULT_DRIVER_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True)
class DriverRequest:
    """Normalized input for one backend dispatch."""

    backend_name: str
    command: list[str]
    payload: str
    timeout_seconds: float | None = DEFAULT_DRIVER_TIMEOUT_SECONDS


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
    if _is_path_command(executable):
        if not Path(executable).exists():
            raise AudioInputError(f"runner command not found: {executable}")
        return
    if shutil.which(executable) is None:
        raise AudioInputError(f"runner command not found in PATH: {executable}")


def _is_path_command(executable: str) -> bool:
    """Return whether a command name is an explicit filesystem path."""
    return Path(executable).is_absolute() or "/" in executable or "\\" in executable


def resolve_driver_timeout_seconds() -> float | None:
    """Return the subprocess timeout for external runner commands."""
    raw_value = os.environ.get("AI_CORE_RUNNER_TIMEOUT_SECONDS")
    if raw_value is None:
        return DEFAULT_DRIVER_TIMEOUT_SECONDS
    try:
        timeout_seconds = float(raw_value)
    except ValueError as exc:
        raise AudioInputError("AI_CORE_RUNNER_TIMEOUT_SECONDS must be numeric") from exc
    if timeout_seconds <= 0:
        return None
    return timeout_seconds


def dispatch_driver_request(request: DriverRequest) -> DriverResult:
    """Validate and execute one backend request via subprocess."""
    validate_driver_command_available(request.command)
    timeout_seconds = (
        resolve_driver_timeout_seconds()
        if request.timeout_seconds == DEFAULT_DRIVER_TIMEOUT_SECONDS
        else request.timeout_seconds
    )
    try:
        completed = subprocess.run(
            request.command,
            input=request.payload,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise AudioInputError(f"runner command not found: {exc.filename}") from exc
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timeout_message = (
            "runner command timed out"
            if timeout_seconds is None
            else f"runner command timed out after {timeout_seconds:g} seconds"
        )
        return DriverResult(
            backend_name=request.backend_name,
            command=request.command,
            payload=request.payload,
            returncode=124,
            stdout=stdout,
            stderr=(stderr + "\n" if stderr else "") + timeout_message,
            command_name=request.command[0] if request.command else "",
        )
    return DriverResult(
        backend_name=request.backend_name,
        command=request.command,
        payload=request.payload,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        command_name=request.command[0] if request.command else "",
    )
