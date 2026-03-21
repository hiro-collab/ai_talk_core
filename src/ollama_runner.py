"""Compatibility wrapper for the Ollama runner CLI."""

from src.runners.ollama import build_ollama_command, build_parser, main


if __name__ == "__main__":
    raise SystemExit(main())
