"""Helpers for planning a project-local Torch pin adjustment."""

from __future__ import annotations

from src.core.dependency_status import get_dependency_status
from src.io.audio import get_runtime_status


def _base_torch_version(torch_version: str | None) -> str | None:
    """Return the base Torch version without local CUDA build suffix."""
    if torch_version is None:
        return None
    return torch_version.split("+", 1)[0]


def _recommended_cuda_family(
    driver_version: str | None,
    torch_cuda_version: str | None,
) -> str | None:
    """Infer a conservative CUDA family suggestion from local status."""
    if driver_version is None or torch_cuda_version is None:
        return None

    try:
        driver_major = int(driver_version.split(".", 1)[0])
    except ValueError:
        return None

    if driver_major <= 535:
        return "cu121"
    return None


def get_torch_pin_plan() -> dict[str, object]:
    """Return a project-local plan for making Torch explicit in pyproject."""
    runtime = get_runtime_status()
    dependencies = get_dependency_status()

    torch_version = runtime.get("torch_version")
    driver_version = runtime.get("nvidia_driver_version")
    torch_cuda_version = runtime.get("torch_cuda_version")
    recommended_cuda_family = _recommended_cuda_family(
        driver_version if isinstance(driver_version, str) else None,
        torch_cuda_version if isinstance(torch_cuda_version, str) else None,
    )
    recommended_torch_spec = None
    base_version = _base_torch_version(
        torch_version if isinstance(torch_version, str) else None
    )
    if base_version is not None:
        recommended_torch_spec = f"torch=={base_version}"

    steps = [
        "Confirm the current state with `uv run python -m src.main --doctor`.",
        "Add torch as an explicit dependency inside pyproject.toml instead of relying on the transitive openai-whisper resolution.",
        "Prefer a driver-compatible Torch CUDA build inside .venv before changing system NVIDIA drivers.",
        "Re-lock and sync the environment with uv after pinning torch.",
        "Verify `torch.cuda.is_available()` and `src.main --show-runtime-status` after the change.",
    ]

    if recommended_cuda_family is not None:
        steps.insert(
            3,
            f"For the current driver generation, try a {recommended_cuda_family}-class Torch build rather than the current CUDA {torch_cuda_version} build.",
        )

    command_examples = [
        "uv run python -m src.main --doctor --doctor-format json",
        "uv lock",
        "uv sync",
        'uv run python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"',
        "uv run python -m src.main --show-runtime-status",
    ]

    return {
        "torch_direct_dependency": dependencies["torch_direct_dependency"],
        "current_torch_version": torch_version,
        "current_torch_cuda_version": torch_cuda_version,
        "current_driver_version": driver_version,
        "recommended_torch_spec": recommended_torch_spec,
        "recommended_cuda_family": recommended_cuda_family,
        "steps": steps,
        "command_examples": command_examples,
        "plan_note": (
            "This plan is project-local. Adjust Torch inside .venv first and avoid "
            "changing system-wide NVIDIA drivers unless the local pin still fails."
        ),
    }


def format_torch_pin_plan(plan: dict[str, object]) -> str:
    """Render the Torch pin plan for terminal output."""
    lines = ["Torch pin plan:"]
    lines.append(f"- torch_direct_dependency: {plan['torch_direct_dependency']}")
    lines.append(f"- current_torch_version: {plan['current_torch_version']}")
    lines.append(f"- current_torch_cuda_version: {plan['current_torch_cuda_version']}")
    lines.append(f"- current_driver_version: {plan['current_driver_version']}")
    lines.append(f"- recommended_torch_spec: {plan['recommended_torch_spec']}")
    lines.append(f"- recommended_cuda_family: {plan['recommended_cuda_family']}")
    lines.append("- steps:")
    for step in plan["steps"]:
        lines.append(f"  - {step}")
    lines.append("- command_examples:")
    for command in plan["command_examples"]:
        lines.append(f"  - {command}")
    lines.append(f"- plan_note: {plan['plan_note']}")
    return "\n".join(lines)
