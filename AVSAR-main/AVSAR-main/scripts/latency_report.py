"""scripts/latency_report.py — measured per-stage p50/p95 against the budget.

TECH_STACK.md section 8:
    Instrument each stage with ``time.monotonic()`` around: upload_end->asr_final,
    retrieval_start->end, llm_first_token, tts_first_byte. Emit to logs +
    ``/metrics``. Targets: p50 <=9 s, p95 <=15 s end-to-end; regression alert in
    CI if unit-test harness sim exceeds budgets by >20%.

ARCHITECTURE.md section 3 breaks that budget down per stage; section 10 asks for
p50/p95 to be reported.

What the script measures, and how it stays honest about each number:

A. **This run, client-side.** It drives complete beneficiary journeys over HTTP
   — the same ``POST /sessions`` + ``POST /sessions/{id}/turn`` SSE path the PWA
   uses, with real WAV audio on the aspiration turn so ASR does actual work —
   and times each turn from request to last SSE byte. That is the number a user
   would feel, attributable to this run alone.
B. **Server-side per stage**, read from ``/metrics``. These ring buffers are
   *cumulative since the core process started*, so they may include earlier
   traffic (tests, the drill, a judge clicking around). Labelled as such.
C. **Persisted**, from ``transcripts.latency_ms`` — the durable per-turn ASR
   record, which survives a core restart.

The harness paces itself under ``rate_limit_turn_per_min`` and backs off on a
429 rather than pretending the limiter is not there: a rate-limited turn is a
real turn the beneficiary would have to repeat, not a measurement artefact to
be configured away.

HONESTY NOTE, and it matters for the demo: these numbers reflect whatever
providers are configured. Under ``VOICE_PROVIDER=mock`` / ``LLM_PROVIDER=mock``
the ASR/TTS/LLM stages are local synthesis and are much faster than Bhashini or
a hosted LLM. The report prints the active providers beside every number and
refuses to describe a mock run as a provider-grade measurement. PLAN.md
section 14's "with real Bhashini keys, same flow completes with measured
p50 <= 9 s" can only be closed by a keyed run.

    python scripts/latency_report.py               # drive 6 journeys, report
    python scripts/latency_report.py --n 20
    python scripts/latency_report.py --no-drive    # report only
    python scripts/latency_report.py --json        # machine-readable
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import statistics
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))

import httpx  # noqa: E402

#: Per-stage budgets, ARCHITECTURE.md section 3 ("ASR final <=2.5 s (short
#: utterances) - retrieval+scoring <=0.5 s - LLM first token <=1.5 s - TTS first
#: byte <=1.5 s") and the end-to-end target from PLAN.md section 5.
#: (p50_budget_ms, p95_budget_ms, citation)
BUDGETS: dict[str, tuple[float, float, str]] = {
    "asr": (2500.0, 2500.0, "ARCHITECTURE.md S3 - ASR final <=2.5 s"),
    "retrieval": (500.0, 500.0, "ARCHITECTURE.md S3 - retrieval+scoring <=0.5 s"),
    "scoring": (500.0, 500.0, "ARCHITECTURE.md S3 - retrieval+scoring <=0.5 s"),
    "llm_first_token": (1500.0, 1500.0, "ARCHITECTURE.md S3 - LLM first token <=1.5 s"),
    "tts_first_byte": (1500.0, 1500.0, "ARCHITECTURE.md S3 - TTS first byte <=1.5 s"),
    "turn_total": (9000.0, 15000.0, "PLAN.md S5 - end-to-end p50 <=9 s, p95 <=15 s"),
}

#: The end-to-end budget applied to the client-side measurement of this run.
CLIENT_BUDGET = (9000.0, 15000.0, "PLAN.md S5 - end-to-end p50 <=9 s, p95 <=15 s")

#: TECH_STACK.md section 8: "regression alert in CI if unit-test harness sim
#: exceeds budgets by >20%".
REGRESSION_MARGIN = 1.20

#: One journey's answers, keyed by the FSM step the core reports.
ANSWERS: dict[str, dict] = {
    "language_select": {"choice": "hi"},
    "consent": {"choice": "yes"},
    "profile_district": {"choice": "270481"},
    "profile_age_band": {"choice": "18_30"},
    "profile_gender": {"choice": "female"},
    "profile_education": {"choice": "8th_10th"},
    "profile_current_work": {"choice": "unemployed"},
    "confirm_intent": {"choice": "yes"},
    # "1" at the recommendation step is *replay* — it deliberately keeps the
    # beneficiary on the same screen. "3" closes the loop with the summary.
    "recommendation": {"choice": "3"},
}

MAX_TURNS = 16


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[index]


def audio_sample() -> str:
    """A real 16 kHz mono WAV, so the ASR stage does actual work."""
    from core.speech.mock import _wav_bytes

    return base64.b64encode(_wav_bytes(2.0)).decode("ascii")


class Pacer:
    """Keep the harness under the server's turn limit instead of tripping it.

    ``rate_limit_turn_per_min`` is a 60-second sliding window. Spacing turns by
    ``60 / limit`` (with a little headroom) never trips it; if a 429 arrives
    anyway — someone else using the same core, say — the caller waits out the
    window rather than recording the rejection as latency.
    """

    def __init__(self, per_min: int) -> None:
        self.per_min = max(1, per_min)
        self.gap = (60.0 / self.per_min) * 1.08
        self.last = 0.0
        self.waits = 0

    def wait(self) -> None:
        delta = time.monotonic() - self.last
        if self.last and delta < self.gap:
            time.sleep(self.gap - delta)
        self.last = time.monotonic()

    def backoff(self, response: httpx.Response) -> float:
        self.waits += 1
        try:
            pause = float(response.headers.get("retry-after", "")) or 61.0
        except ValueError:
            pause = 61.0
        time.sleep(min(pause, 61.0))
        self.last = 0.0
        return pause


def read_sse(response: httpx.Response) -> list[tuple[str, dict]]:
    """Collect ``(event, data)`` pairs from one SSE turn response."""
    events: list[tuple[str, dict]] = []
    name: str | None = None
    for raw in response.iter_lines():
        line = raw.rstrip("\r")
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            body = line[5:].strip()
            try:
                events.append((name or "message", json.loads(body)))
            except json.JSONDecodeError:
                events.append((name or "message", {"raw": body}))
            name = None
    return events


def one_turn(
    client: httpx.Client, session_id: str, payload: dict, pacer: Pacer
) -> tuple[list[tuple[str, dict]], float]:
    """Run one turn, return its events and the client-side wall time in ms.

    A 429 is waited out and the turn retried once; the rejected attempt is not
    counted as a latency sample.
    """
    for attempt in (1, 2):
        pacer.wait()
        started = time.monotonic()
        with client.stream(
            "POST", f"/sessions/{session_id}/turn", json=payload, timeout=90.0
        ) as response:
            if response.status_code == 429 and attempt == 1:
                response.read()
                pacer.backoff(response)
                continue
            response.raise_for_status()
            events = read_sse(response)
        return events, (time.monotonic() - started) * 1000.0
    raise RuntimeError("rate limited twice in a row")


def drive_one(
    client: httpx.Client, lang: str, spoken_audio: str, pacer: Pacer
) -> dict:
    """Run one beneficiary journey to a recommendation."""
    created = client.post("/sessions", json={"channel": "pwa", "lang": lang}, timeout=30.0)
    created.raise_for_status()
    body = created.json()
    session_id = body["session_id"]
    step = (body.get("state") or {}).get("step", "consent")

    reached_recs = False
    turn_ms: list[float] = []

    for _ in range(MAX_TURNS):
        if step in ("summary", "ended", "declined"):
            break
        if step in ("aspiration", "clarify"):
            payload: dict = {"audio_b64": spoken_audio}
        else:
            payload = dict(ANSWERS.get(step, {"choice": "1"}))

        events, elapsed_ms = one_turn(client, session_id, payload, pacer)
        turn_ms.append(elapsed_ms)

        previous = step
        for name, data in events:
            if name == "state":
                step = data.get("step", step)
            elif name == "recs" and data.get("items"):
                reached_recs = True
            elif name == "error":
                return {
                    "session_id": session_id,
                    "turn_ms": turn_ms,
                    "reached_recs": reached_recs,
                    "error": data.get("code"),
                }
        if step == previous and previous not in ("clarify", "aspiration"):
            return {
                "session_id": session_id,
                "turn_ms": turn_ms,
                "reached_recs": reached_recs,
                "error": f"stuck at {previous}",
            }

    return {"session_id": session_id, "turn_ms": turn_ms, "reached_recs": reached_recs}


def parse_metrics(text: str) -> dict[str, dict[str, float]]:
    """Parse the Prometheus exposition back into ``{stage: {p50, p95, max, count}}``."""
    out: dict[str, dict[str, float]] = {}
    pattern = re.compile(r'^avsar_stage_(\w+?)\{stage="([^"]+)"\}\s+([0-9.]+)$')
    keys = {
        "latency_ms_p50": "p50_ms",
        "latency_ms_p95": "p95_ms",
        "latency_ms_max": "max_ms",
        "observations": "count",
    }
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        metric, stage, value = match.group(1), match.group(2), float(match.group(3))
        if metric in keys:
            out.setdefault(stage, {})[keys[metric]] = value
    return out


def db_asr_latency() -> dict:
    """Durable ASR latency from ``transcripts.latency_ms`` (ARCHITECTURE.md S4)."""
    from core.db import SessionLocal
    from sqlalchemy import text as sql

    db = SessionLocal()
    try:
        row = db.execute(
            sql(
                """
                SELECT count(*)                                                 AS n,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)  AS p50,
                       percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95,
                       max(latency_ms)                                          AS worst
                FROM transcripts
                WHERE latency_ms IS NOT NULL AND latency_ms > 0
                """
            )
        ).one()
        return {
            "count": int(row.n or 0),
            "p50_ms": round(float(row.p50), 1) if row.p50 is not None else 0.0,
            "p95_ms": round(float(row.p95), 1) if row.p95 is not None else 0.0,
            "max_ms": round(float(row.worst), 1) if row.worst is not None else 0.0,
        }
    finally:
        db.close()


def verdict(stats: dict[str, float], budget: tuple[float, float, str]) -> tuple[str, bool]:
    """OK / OVER / ALERT for one stage. ALERT is the CI regression trigger."""
    p50_budget, p95_budget, _ = budget
    p50 = stats.get("p50_ms", 0.0)
    p95 = stats.get("p95_ms", 0.0)
    if p50 > p50_budget * REGRESSION_MARGIN or p95 > p95_budget * REGRESSION_MARGIN:
        return "ALERT", True
    if p50 > p50_budget or p95 > p95_budget:
        return "OVER", False
    return "OK", False


def main() -> int:
    from core.config import settings

    parser = argparse.ArgumentParser(description="per-stage latency vs budget")
    parser.add_argument("--n", type=int, default=6, help="journeys to drive (default 6)")
    parser.add_argument("--no-drive", action="store_true", help="report only, drive nothing")
    parser.add_argument("--base", default="http://localhost:8000", help="core base URL")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--turn-limit",
        type=int,
        default=settings.rate_limit_turn_per_min,
        help="server turn limit per minute to pace under",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when a stage exceeds its budget at all, not only by the margin",
    )
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base, timeout=30.0)

    try:
        ready = client.get("/readyz", timeout=15.0).json()
    except Exception as exc:
        print(f"core not reachable at {args.base}: {type(exc).__name__}: {exc}")
        print("start it with `make up`, then re-run `make latency`.")
        return 2

    checks = ready.get("checks", {}) or {}
    providers = {
        "speech": (checks.get("speech") or {}).get("provider", "?"),
        "llm": (checks.get("llm") or {}).get("provider", "?"),
        "degraded": bool((checks.get("speech") or {}).get("degraded")),
    }
    mock_run = providers["speech"] == "mock" or providers["llm"] == "mock"

    driven: list[dict] = []
    client_ms: list[float] = []
    pacer = Pacer(args.turn_limit)
    warm_first_ms: float | None = None

    if not args.no_drive:
        sample = audio_sample()
        langs = ("hi", "mr", "te", "en")
        started = time.monotonic()

        # Warm-up journey: discarded from the sample. The core warms the embedder
        # at startup (main.py warm_start), but a cold page cache or a core that
        # was started with WARM_START=false would otherwise charge the first
        # measured journey for a one-off model load.
        try:
            warm = drive_one(client, "hi", sample, pacer)
            warm_first_ms = warm["turn_ms"][0] if warm.get("turn_ms") else None
        except Exception as exc:
            print(f"warm-up journey failed: {type(exc).__name__}: {exc}")
            return 1

        for index in range(args.n):
            try:
                row = drive_one(client, langs[index % len(langs)], sample, pacer)
                driven.append(row)
                if row.get("reached_recs"):
                    client_ms.extend(row["turn_ms"])
            except Exception as exc:
                driven.append({"error": f"{type(exc).__name__}: {exc}"})
        wall = time.monotonic() - started
        completed = sum(1 for d in driven if d.get("reached_recs"))
        if not args.json:
            print(
                f"drove {len(driven)} journeys (+1 warm-up) in {wall:.1f}s - "
                f"{completed} reached a recommendation, "
                f"{pacer.waits} rate-limit backoff(s)"
            )
        if completed == 0:
            print("NO journey reached a recommendation; the numbers below would be meaningless.")
            for row in driven[:3]:
                print(f"  {row}")
            return 1

    stages = parse_metrics(client.get("/metrics").text)

    try:
        persisted: dict = db_asr_latency()
    except Exception as exc:
        persisted = {"error": f"{type(exc).__name__}: {exc}"}

    client_stats: dict | None = None
    if client_ms:
        client_stats = {
            "count": len(client_ms),
            "p50_ms": round(percentile(client_ms, 50), 1),
            "p95_ms": round(percentile(client_ms, 95), 1),
            "max_ms": round(max(client_ms), 1),
            "mean_ms": round(statistics.fmean(client_ms), 1),
        }
        state, client_alert = verdict(client_stats, CLIENT_BUDGET)
        client_stats["verdict"] = state
    else:
        client_alert = False

    rows: list[tuple[str, dict | None, tuple[float, float, str]]] = []
    any_alert = client_alert
    any_over = bool(client_stats and client_stats["verdict"] != "OK")
    for stage, budget in BUDGETS.items():
        stats = stages.get(stage)
        if not stats or not stats.get("count"):
            rows.append((stage, None, budget))
            continue
        state, alert = verdict(stats, budget)
        any_alert = any_alert or alert
        any_over = any_over or state != "OK"
        rows.append((stage, {**stats, "verdict": state}, budget))

    if args.json:
        print(
            json.dumps(
                {
                    "providers": providers,
                    "mock_run": mock_run,
                    "journeys_driven": len(driven),
                    "client_side_this_run": client_stats,
                    "warm_up_first_turn_ms": warm_first_ms,
                    "server_side_cumulative": {s: v for s, v, _ in rows if v},
                    "persisted_asr": persisted,
                    "alert": any_alert,
                },
                indent=2,
            )
        )
        return 1 if (any_alert or (args.strict and any_over)) else 0

    margin_pct = round((REGRESSION_MARGIN - 1) * 100)
    print()
    print("AVSAR latency report - measured p50/p95 against the documented budget")
    print(
        f"  speech provider: {providers['speech']}    llm provider: {providers['llm']}"
        f"    degraded: {providers['degraded']}"
    )
    if mock_run:
        print(
            "  NOTE: mock provider(s) active. These are MOCK-MODE numbers and are NOT a\n"
            "        measurement of Bhashini/hosted-LLM latency. PLAN.md S14's keyed-run\n"
            "        item stays open until this report is produced with real keys."
        )

    print()
    print("A. END-TO-END, CLIENT-SIDE, THIS RUN (request -> last SSE byte)")
    if client_stats:
        print(
            f"   turns={client_stats['count']}  p50={client_stats['p50_ms']}ms  "
            f"p95={client_stats['p95_ms']}ms  max={client_stats['max_ms']}ms  "
            f"mean={client_stats['mean_ms']}ms  -> {client_stats['verdict']}"
        )
        print(f"   budget {CLIENT_BUDGET[0]:.0f}/{CLIENT_BUDGET[1]:.0f} ms  ({CLIENT_BUDGET[2]})")
    else:
        print("   not measured (--no-drive)")
    if warm_first_ms is not None:
        print(
            f"   first turn of the discarded warm-up journey: {warm_first_ms:.1f}ms "
            "(cold-start reference, excluded from the numbers above)"
        )

    print()
    print("B. PER STAGE, SERVER-SIDE - CUMULATIVE SINCE THE CORE PROCESS STARTED")
    print("   (may include traffic from tests, the drill or manual use, not only this run)")
    header = (
        f"   {'stage':<18}{'n':>6}{'p50 ms':>10}{'p95 ms':>10}"
        f"{'max ms':>10}{'budget p50/p95':>20}  verdict"
    )
    print(header)
    print("   " + "-" * 86)
    for stage, stats, budget in rows:
        if stats is None:
            print(f"   {stage:<18}{'-':>6}      (no observations recorded)")
            continue
        budget_text = f"{budget[0]:.0f}/{budget[1]:.0f}"
        print(
            f"   {stage:<18}{int(stats['count']):>6}{stats['p50_ms']:>10.1f}"
            f"{stats['p95_ms']:>10.1f}{stats.get('max_ms', 0.0):>10.1f}"
            f"{budget_text:>20}  {stats['verdict']}"
        )
    print()
    for stage, _, budget in rows:
        print(f"   {stage:<18}{budget[2]}")

    print()
    print("C. PERSISTED PER-TURN ASR LATENCY (transcripts.latency_ms, survives restart)")
    if "error" in persisted:
        print(f"   unavailable ({persisted['error']})")
    else:
        print(
            f"   n={persisted['count']}  p50={persisted['p50_ms']}ms  "
            f"p95={persisted['p95_ms']}ms  max={persisted['max_ms']}ms"
        )

    print()
    if any_alert:
        print(
            "REGRESSION ALERT - a measurement exceeds its budget by more than "
            f"{margin_pct}% (TECH_STACK.md S8)."
        )
        return 1
    if any_over:
        print(f"OVER BUDGET, but within the {margin_pct}% regression margin - not an alert.")
        return 1 if args.strict else 0
    print("ALL MEASUREMENTS WITHIN BUDGET.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
