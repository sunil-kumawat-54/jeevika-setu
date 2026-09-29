"""Portable Phase 1 preflight for hosts without Docker or GNU Make."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 1 runtime prerequisites")
    parser.add_argument("--compose", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()

    missing = [str(path) for path in (args.compose, args.env_file) if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL", "missing": missing}))
        return 1

    docker = shutil.which("docker") is not None
    make = shutil.which("make") is not None
    result = {
        "status": "PASS" if docker and make else "BLOCKED_RUNTIME",
        "compose_config": str(args.compose),
        "env_file": str(args.env_file),
        "docker": docker,
        "make": make,
        "runtime_note": (
            "Docker and GNU Make available"
            if docker and make
            else "Portable config checks passed; Compose startup and Make targets require a Docker-capable host"
        ),
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
