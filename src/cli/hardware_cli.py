"""CLI for hardware analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analyzers.hardware.core import analyze_hardware_spec
from exceptions.hardware_exceptions import HardwareValidationError
from utils.logging import get_logger

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for hardware analysis CLI.

    Args:
        argv: Command line arguments. If None, uses sys.argv[1:]

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Normalize hardware capabilities and compute throughput metrics."
    )
    parser.add_argument(
        "input_path",
        help="Path to hardware specification JSON file",
        type=Path,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output path (default: stdout)",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--indent",
        help="JSON indentation (default: 2)",
        type=int,
        default=2,
    )

    args = parser.parse_args(argv)

    try:
        # Read input
        if not args.input_path.exists():
            logger.error(f"Input file not found: {args.input_path}")
            return 1

        with open(args.input_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # Analyze hardware
        result = analyze_hardware_spec(raw)

        # Format output
        output_json = json.dumps(result, indent=args.indent, sort_keys=True)

        # Write output
        if args.output:
            args.output.write_text(output_json, encoding="utf-8")
            logger.info(f"Results written to {args.output}")
        else:
            print(output_json)

        return 0

    except HardwareValidationError as exc:
        logger.error(f"Validation error: {exc}")
        return 1
    except FileNotFoundError:
        logger.error(f"Input file not found: {args.input_path}")
        return 1
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid JSON in input file: {exc}")
        return 1
    except Exception as exc:
        logger.exception(f"Unexpected error: {exc}")
        return 1


def cli_entry() -> None:
    """Entry point for console script."""
    sys.exit(main())


if __name__ == "__main__":
    cli_entry()
