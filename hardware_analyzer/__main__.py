"""CLI entrypoint for hardware analyzer."""

from __future__ import annotations

import argparse
import json
import sys

from .core import analyze_hardware_spec
from .utils import ValidationError


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Normalize hardware capabilities.")
    parser.add_argument("input_path", help="Path to hardware spec JSON.")
    args = parser.parse_args(argv)
    try:
        with open(args.input_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        result = analyze_hardware_spec(raw)
    except ValidationError as exc:
        sys.stderr.write(f"ValidationError: {exc}\n")
        return 1
    except FileNotFoundError:
        sys.stderr.write("Input file not found.\n")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
