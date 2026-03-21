"""Compatibility wrapper for the shared handoff reader CLI."""

from src.runners.handoff import build_parser, main, render_handoff_output


if __name__ == "__main__":
    raise SystemExit(main())
