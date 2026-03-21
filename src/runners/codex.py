"""Compatibility wrapper for the shared agent runner implementation."""

from src.runners.agent import (
    STATIC_TEMPLATES,
    build_parser,
    build_template_command,
    main,
    normalize_command_args,
    resolve_runner_command,
    validate_runner_command_available,
)

__all__ = [
    "STATIC_TEMPLATES",
    "build_parser",
    "build_template_command",
    "main",
    "normalize_command_args",
    "resolve_runner_command",
    "validate_runner_command_available",
]
