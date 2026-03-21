"""Compatibility wrapper for the shared agent runner CLI."""

from src.runners.agent import (
    STATIC_TEMPLATES,
    build_parser,
    build_template_command,
    main,
    normalize_command_args,
    resolve_runner_command,
    validate_runner_command_available,
)


if __name__ == "__main__":
    raise SystemExit(main())
