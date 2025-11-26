"""CLI for model analysis."""

from __future__ import annotations

import sys
from pathlib import Path

from analyzers.model.core import analyze_model
from exceptions.model_exceptions import ModelValidationError
from utils.logging import get_logger

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for model analysis CLI.

    Args:
        argv: Command line arguments. If None, uses sys.argv[1:]

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if argv is None:
        argv = sys.argv[1:]

    try:
        # Read input
        if len(argv) > 0:
            input_path = Path(argv[0])
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return 1
            raw = input_path.read_text(encoding="utf-8")
        else:
            # Read from stdin
            raw = sys.stdin.read()

        # Analyze model
        result = analyze_model(raw)
        
        # Output result
        print(result)
        return 0

    except ModelValidationError as exc:
        logger.error(f"Validation error: {exc}")
        return 1
    except Exception as exc:
        logger.exception(f"Unexpected error: {exc}")
        return 1


def cli_entry() -> None:
    """Entry point for console script."""
    sys.exit(main())


if __name__ == "__main__":
    cli_entry()
