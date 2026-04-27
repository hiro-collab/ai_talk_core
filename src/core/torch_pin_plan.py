"""Helpers for planning a project-local Torch pin adjustment."""

from __future__ import annotations

from src.core.dependency_status import get_dependency_status
from src.io.audio import get_runtime_status


def _base_torch_version(torch_version: str | None) -> str | None:
    """Return the base Torch version without local CUDA build suffix."""
    if torch_version is None:
        return None
    return torch_version.split("+", 1)[0]


def _torch_build_suffix(torch_version: str | None) -> str | None:
    """Return the local build suffix from a Torch version string."""
    if torch_version is None or "+" not in torch_version:
        return None
    return torch_version.split("+", 1)[1]


def _recommended_cuda_family(
    driver_version: str | None,
    torch_cuda_version: str | None,
) -> str | None:
    """Infer a conservative CUDA family suggestion from local status."""
    if driver_version is None:
        return None

    try:
        driver_major = int(driver_version.split(".", 1)[0])
    except ValueError:
        return None

    if driver_major >= 570:
        return "cu128"
    if driver_major >= 560:
        return "cu126"
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
    build_suffix = _torch_build_suffix(
        torch_version if isinstance(torch_version, str) else None
    )
    if base_version is not None:
        recommended_torch_spec = f"torch=={base_version}"

    pytorch_index_url = (
        f"https://download.pytorch.org/whl/{recommended_cuda_family}"
        if recommended_cuda_family is not None
        else None
    )
    uv_pip_install_command = (
        f"uv pip install --upgrade torch --index-url {pytorch_index_url}"
        if pytorch_index_url is not None
        else None
    )
    explicit_build_selection_needed = bool(
        recommended_cuda_family is not None
        and (build_suffix is not None or runtime.get("nvidia_smi_available"))
    )

    steps = [
        "Confirm the current state with `uv run python -m src.main --doctor`.",
        "Add torch as an explicit dependency inside pyproject.toml instead of relying on the transitive openai-whisper resolution.",
        "Prefer a driver-compatible Torch CUDA build inside .venv before changing system NVIDIA drivers.",
        "Re-lock and sync the environment with uv after pinning torch.",
        "Verify `torch.cuda.is_available()` and `src.main --show-runtime-status` after the change.",
    ]

    if recommended_cuda_family is not None:
        if torch_cuda_version is None:
            cuda_step = (
                f"For the current driver generation, try a {recommended_cuda_family}-class "
                "Torch CUDA build instead of the installed CPU-only Torch build."
            )
        else:
            cuda_step = (
                f"For the current driver generation, try a {recommended_cuda_family}-class "
                f"Torch build rather than the current CUDA {torch_cuda_version} build."
            )
        steps.insert(
            3,
            cuda_step,
        )
    if explicit_build_selection_needed:
        steps.insert(
            4,
            "Use an explicit PyTorch build/source choice instead of a version-only pin when selecting a CUDA wheel.",
        )
    if runtime.get("nvidia_smi_available") and runtime.get("torch_cuda_version") is None:
        steps.insert(
            3,
            "This machine can see an NVIDIA GPU, but the installed Torch build is CPU-only; use the project helper script or PyTorch selector to install a CUDA wheel in .venv.",
        )

    command_examples = [
        "uv run python -m src.main --doctor --doctor-format json",
        ".\\setup_gpu_windows.ps1",
        "uv add 'torch==<base-version>'",
        "uv pip install --upgrade torch --index-url https://download.pytorch.org/whl/<cu-family>",
        "uv lock",
        "uv sync",
        'uv run python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"',
        "uv run python -m src.main --show-runtime-status",
    ]

    return {
        "torch_direct_dependency": dependencies["torch_direct_dependency"],
        "current_torch_version": torch_version,
        "current_torch_base_version": base_version,
        "current_torch_build_suffix": build_suffix,
        "current_torch_cuda_version": torch_cuda_version,
        "current_driver_version": driver_version,
        "recommended_torch_spec": recommended_torch_spec,
        "recommended_cuda_family": recommended_cuda_family,
        "pytorch_index_url": pytorch_index_url,
        "uv_pip_install_command": uv_pip_install_command,
        "setup_script_command": (
            f".\\setup_gpu_windows.ps1 -Cuda {recommended_cuda_family}"
            if recommended_cuda_family is not None
            else ".\\setup_gpu_windows.ps1"
        ),
        "explicit_build_selection_needed": explicit_build_selection_needed,
        "pyproject_dependency_entry": recommended_torch_spec,
        "uv_add_command": (
            f"uv add '{recommended_torch_spec}'"
            if recommended_torch_spec is not None
            else None
        ),
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
    lines.append(f"- current_torch_base_version: {plan['current_torch_base_version']}")
    lines.append(f"- current_torch_build_suffix: {plan['current_torch_build_suffix']}")
    lines.append(f"- current_torch_cuda_version: {plan['current_torch_cuda_version']}")
    lines.append(f"- current_driver_version: {plan['current_driver_version']}")
    lines.append(f"- recommended_torch_spec: {plan['recommended_torch_spec']}")
    lines.append(f"- recommended_cuda_family: {plan['recommended_cuda_family']}")
    lines.append(f"- pytorch_index_url: {plan['pytorch_index_url']}")
    lines.append(f"- uv_pip_install_command: {plan['uv_pip_install_command']}")
    lines.append(f"- setup_script_command: {plan['setup_script_command']}")
    lines.append(
        f"- explicit_build_selection_needed: {plan['explicit_build_selection_needed']}"
    )
    lines.append(f"- pyproject_dependency_entry: {plan['pyproject_dependency_entry']}")
    lines.append(f"- uv_add_command: {plan['uv_add_command']}")
    lines.append("- steps:")
    for step in plan["steps"]:
        lines.append(f"  - {step}")
    lines.append("- command_examples:")
    for command in plan["command_examples"]:
        lines.append(f"  - {command}")
    lines.append(f"- plan_note: {plan['plan_note']}")
    return "\n".join(lines)
