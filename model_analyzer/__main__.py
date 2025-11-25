"""CLI for manual testing."""

from __future__ import annotations

import sys

from .core import analyze_model


def _read_input() -> str:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


if __name__ == "__main__":
    raw = _read_input()
    print(analyze_model(raw))
