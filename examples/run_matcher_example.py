"""Run model/hardware analyzer + matcher on bundled examples."""

from __future__ import annotations

import json
from pathlib import Path

from hardware_analyzer.core import analyze_hardware_spec
from model_analyzer.core import analyze_model, ValidationError as ModelValidationError
from matcher.core import match_model_to_hardware, MatcherError


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    examples_dir = repo_root / "examples"

    model_path = examples_dir / "model_analyzer_input.json"
    hardware_path = examples_dir / "hardware_spec.json"

    try:
        model_input = model_path.read_text()
        hardware_spec = json.loads(hardware_path.read_text())
    except FileNotFoundError as exc:
        print(f"Missing example file: {exc}")
        return 1

    try:
        model_report = json.loads(analyze_model(model_input))
    except ModelValidationError as exc:
        print(f"Model validation failed: {exc}")
        return 1

    hardware_report = analyze_hardware_spec(hardware_spec)["hardware_analysis"]

    inf = model_report.get("inference_scenario", {})
    matcher_input = {
        "model": model_report,
        "hardware_analysis": hardware_report,
        "requirements": {
            "worst_case": {
                "batch_size": inf.get("batch_size"),
                "sequence_length": inf.get("sequence_length"),
                "qps": 1.0,
                "latency_seconds": 0.1,
            },
            "constraints": {
                "max_hourly_cost_usd": None,
                "allowed_regions": [],
                "disallow_kinds": [],
            },
        },
    }

    try:
        matches = match_model_to_hardware(matcher_input)
    except MatcherError as exc:
        print(f"Matcher failed: {exc}")
        return 1

    print(json.dumps(matches, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
