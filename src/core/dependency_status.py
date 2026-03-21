"""Helpers for reporting project dependency status."""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

TRACKED_PACKAGES = (
    "flask",
    "openai-whisper",
    "setuptools",
    "torch",
    "webrtcvad",
)


def _normalize_requirement_name(requirement: str) -> str:
    """Extract a normalized package name from a requirement string."""
    lowered = requirement.strip().lower()
    for separator in ("<=", ">=", "==", "~=", "!=", "<", ">", "=", ";", "["):
        if separator in lowered:
            lowered = lowered.split(separator, 1)[0]
            break
    return lowered.strip()


def get_dependency_status() -> dict[str, object]:
    """Return direct dependency and installed package status."""
    with PYPROJECT_PATH.open("rb") as handle:
        pyproject = tomllib.load(handle)

    dependencies = pyproject.get("project", {}).get("dependencies", [])
    direct_dependencies = [str(item) for item in dependencies]
    direct_dependency_names = [
        _normalize_requirement_name(requirement)
        for requirement in direct_dependencies
    ]

    installed_versions: dict[str, str | None] = {}
    for package_name in TRACKED_PACKAGES:
        try:
            installed_versions[package_name] = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            installed_versions[package_name] = None

    return {
        "pyproject_path": str(PYPROJECT_PATH),
        "direct_dependencies": direct_dependencies,
        "direct_dependency_names": direct_dependency_names,
        "torch_direct_dependency": "torch" in direct_dependency_names,
        "installed_versions": installed_versions,
        "dependency_note": (
            "torch is currently resolved transitively via openai-whisper unless it is "
            "added explicitly to pyproject.toml."
        ),
    }


def format_dependency_status(status: dict[str, object]) -> str:
    """Render dependency status for terminal output."""
    lines = ["Dependency status:"]
    lines.append(f"- pyproject_path: {status['pyproject_path']}")
    lines.append("- direct_dependencies:")
    for requirement in status["direct_dependencies"]:
        lines.append(f"  - {requirement}")
    lines.append(f"- torch_direct_dependency: {status['torch_direct_dependency']}")
    lines.append("- installed_versions:")
    installed_versions = status["installed_versions"]
    assert isinstance(installed_versions, dict)
    for package_name, version in installed_versions.items():
        lines.append(f"  - {package_name}: {version}")
    lines.append(f"- dependency_note: {status['dependency_note']}")
    return "\n".join(lines)
