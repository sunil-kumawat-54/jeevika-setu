"""In-process metrics + per-stage latency instrumentation.

TECH_STACK.md §8 requires `time.monotonic()` around upload_end→asr_final,
retrieval_start→end, llm_first_token, tts_first_byte, emitted to logs and
/metrics, with p50/p95 reported (ARCHITECTURE.md §10).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Any

log = logging.getLogger("avsar.metrics")

_LOCK = threading.Lock()
_COUNTERS: dict[str, int] = defaultdict(int)
_TIMINGS: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=2000))

STAGES = ("asr", "retrieval", "scoring", "llm_first_token", "tts_first_byte", "turn_total")


def incr(name: str, value: int = 1, **labels: Any) -> None:
    key = name if not labels else name + "{" + ",".join(f'{k}="{v}"' for k, v in sorted(labels.items())) + "}"
    with _LOCK:
        _COUNTERS[key] += value


def observe(stage: str, ms: float, session_id: str | None = None) -> None:
    with _LOCK:
        _TIMINGS[stage].append(ms)
    log.info("stage timing", extra={"stage": stage, "latency_ms": round(ms, 1), "session_id": session_id})


@contextmanager
def timed(stage: str, session_id: str | None = None):
    """Time a pipeline stage and record it. Yields a dict you may mutate."""
    started = time.monotonic()
    holder: dict[str, float] = {}
    try:
        yield holder
    finally:
        ms = (time.monotonic() - started) * 1000.0
        holder["ms"] = ms
        observe(stage, ms, session_id)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def summary() -> dict[str, dict[str, float]]:
    """p50/p95/count per stage — used by /metrics and the latency report."""
    with _LOCK:
        snapshot = {k: list(v) for k, v in _TIMINGS.items()}
    return {
        stage: {
            "count": len(vals),
            "p50_ms": round(_percentile(vals, 50), 1),
            "p95_ms": round(_percentile(vals, 95), 1),
            "max_ms": round(max(vals), 1) if vals else 0.0,
        }
        for stage, vals in snapshot.items()
    }


def counters() -> dict[str, int]:
    with _LOCK:
        return dict(_COUNTERS)


def prometheus_text() -> str:
    """Prometheus exposition format (ARCHITECTURE.md §10)."""
    lines: list[str] = []
    for key, val in sorted(counters().items()):
        name = key.split("{")[0]
        lines.append(f"# TYPE avsar_{name} counter")
        lines.append(f"avsar_{key} {val}")
    for stage, stats in sorted(summary().items()):
        lines.append("# TYPE avsar_stage_latency_ms_p50 gauge")
        lines.append(f'avsar_stage_latency_ms_p50{{stage="{stage}"}} {stats["p50_ms"]}')
        lines.append(f'avsar_stage_latency_ms_p95{{stage="{stage}"}} {stats["p95_ms"]}')
        lines.append("# TYPE avsar_stage_latency_ms_max gauge")
        lines.append(f'avsar_stage_latency_ms_max{{stage="{stage}"}} {stats["max_ms"]}')
        lines.append(f'avsar_stage_observations{{stage="{stage}"}} {stats["count"]}')
    return "\n".join(lines) + "\n"


def reset() -> None:
    with _LOCK:
        _COUNTERS.clear()
        _TIMINGS.clear()
