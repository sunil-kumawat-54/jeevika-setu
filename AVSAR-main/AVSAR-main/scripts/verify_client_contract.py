from __future__ import annotations

import argparse
import json

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe the versioned mock beneficiary contract")
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--lang", choices=("hi", "mr", "te", "en"), default="hi")
    args = parser.parse_args()

    with httpx.Client(timeout=15.0) as client:
        health = client.get(f"{args.base_url}/healthz")
        if health.status_code != 200 or health.json().get("status") != "ok":
            print(f"health contract failed: {health.status_code} {health.text}")
            return 1
        created = client.post(
            f"{args.base_url}/sessions",
            headers={"x-avsar-lang": args.lang},
            json={"channel": "pwa", "lang": args.lang},
        )
        if created.status_code != 200:
            print(f"session contract failed: {created.status_code} {created.text}")
            return 1
        session = created.json()
        session_id = session.get("session_id")
        if not session_id or session.get("state", {}).get("step") != "consent":
            print(f"session envelope failed: {json.dumps(session)}")
            return 1
        turn = client.post(
            f"{args.base_url}/sessions/{session_id}/turn",
            headers={"x-avsar-lang": args.lang, "accept": "text/event-stream"},
            json={"text": "yes"},
        )
        if turn.status_code != 200:
            print(f"turn contract failed: {turn.status_code} {turn.text}")
            return 1
        events = {line[7:].strip() for line in turn.text.splitlines() if line.startswith("event: ")}
        if "state" not in events and "error" not in events:
            print(f"SSE envelope failed: events={sorted(events)}")
            return 1

    print(f"client contract: OK ({args.base_url}, events={sorted(events)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
