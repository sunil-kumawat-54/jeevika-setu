from __future__ import annotations

import sys
from pathlib import Path

REQUIRED = (
    "grounding",
    "VOICE_PROVIDER: mock",
    "LLM_PROVIDER: mock",
)
FORBIDDEN = ("KaushalVani", "ai-service", "node backend")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".github/workflows/ci.yml")
    text = path.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in text]
    forbidden = [item for item in FORBIDDEN if item.lower() in text.lower()]
    if missing or forbidden:
        if missing:
            print(f"missing CI requirements: {', '.join(missing)}")
        if forbidden:
            print(f"forbidden duplicate runtime references: {', '.join(forbidden)}")
        return 1
    print(f"CI grounding contract: OK ({path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
