from __future__ import annotations

import pathlib
import re

SW = pathlib.Path(__file__).resolve().parents[1] / "apps" / "web" / "public" / "sw.js"


def main() -> int:
    text = SW.read_text(encoding="utf-8")
    non_get_guard = re.search(r"if \(request\.method !== 'GET'\) return;", text)
    cache_after_guard = non_get_guard and text.find("event.respondWith", non_get_guard.end()) > non_get_guard.end()
    if not non_get_guard or not cache_after_guard:
        print("service-worker safety contract failed: non-GET guard is missing or misplaced")
        return 1
    if "cache.put(request" not in text or "request.method !== 'GET'" not in text:
        print("service-worker safety contract failed: cache policy is incomplete")
        return 1
    print(f"service-worker safety contract: OK ({SW})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
