"""Helpers for runtime, dependency, and doctor status reporting."""

from __future__ import annotations

from src.core.dependency_status import format_dependency_status, get_dependency_status
from src.core.torch_pin_plan import format_torch_pin_plan, get_torch_pin_plan
from src.io.audio import get_runtime_status


def format_runtime_status(status: dict[str, str | bool | None]) -> str:
    """Format the local runtime status for terminal output."""
    lines = ["Runtime status:"]
    for key, value in status.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_doctor_status() -> dict[str, object]:
    """Return a combined diagnosis view for runtime and dependency state."""
    return {
        "runtime": get_runtime_status(),
        "dependencies": get_dependency_status(),
    }


def format_doctor_status(status: dict[str, object]) -> str:
    """Format the combined diagnosis view for terminal output."""
    runtime = status["runtime"]
    dependencies = status["dependencies"]
    assert isinstance(runtime, dict)
    assert isinstance(dependencies, dict)
    return "\n\n".join(
        [
            "Doctor summary:",
            format_runtime_status(runtime),
            format_dependency_status(dependencies),
        ]
    )


def build_torch_pin_status() -> dict[str, object]:
    """Return a project-local Torch pin plan."""
    return get_torch_pin_plan()


def print_status_command(args: object) -> bool:
    """Print one of the inspection-style status commands when requested."""
    runtime_status_format = getattr(args, "runtime_status_format", "text")
    dependency_status_format = getattr(args, "dependency_status_format", "text")
    doctor_format = getattr(args, "doctor_format", "text")
    torch_pin_plan_format = getattr(args, "torch_pin_plan_format", "text")

    if getattr(args, "show_runtime_status", False):
        status = get_runtime_status()
        if runtime_status_format == "json":
            import json

            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(format_runtime_status(status))
        return True
    if getattr(args, "show_dependency_status", False):
        status = get_dependency_status()
        if dependency_status_format == "json":
            import json

            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(format_dependency_status(status))
        return True
    if getattr(args, "doctor", False):
        status = build_doctor_status()
        if doctor_format == "json":
            import json

            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(format_doctor_status(status))
        return True
    if getattr(args, "show_torch_pin_plan", False):
        status = build_torch_pin_status()
        if torch_pin_plan_format == "json":
            import json

            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            print(format_torch_pin_plan(status))
        return True
    return False
