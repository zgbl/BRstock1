#!/usr/bin/env python3
"""Publish local option-chain calibration parameters into the deployable package.

This copies only synthetic-chain correction factors. It does not copy Schwab
OAuth tokens, client secrets, refresh tokens, or account data.
"""

import argparse
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = PROJECT_ROOT / "Data" / "option_synth_calibration.json"
DEFAULT_DESTINATION = PROJECT_ROOT / "services" / "backend_api" / "config_data" / "option_synth_calibration.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish non-sensitive option synth calibration parameters.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Local calibration JSON path.")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION, help="Deployable calibration JSON path.")
    args = parser.parse_args()

    source = args.source.expanduser()
    destination = args.destination.expanduser()
    if not source.exists():
        raise SystemExit(f"Calibration file not found: {source}")

    model = json.loads(source.read_text())
    if not isinstance(model, dict) or not isinstance(model.get("buckets"), dict):
        raise SystemExit(f"Invalid calibration file: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    print(
        f"Published calibration v{model.get('version', 0)} "
        f"with {len(model.get('buckets') or {})} buckets to {destination}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
