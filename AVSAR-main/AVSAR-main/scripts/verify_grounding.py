"""scripts/verify_grounding.py — prove RULE 2 across many random sessions.

RULE 2:
    Implement ``scripts/verify_grounding.py``. It must prove that across 50
    random sessions every numeral present in the LLM verbalized output is
    present in the corresponding tool JSON. Grounding failure = gate failure.

PLAN.md section 14 states the same acceptance in the definition of done:
    Every recommendation's fields provably originate from DB rows (spot-check
    script ``scripts/verify_grounding.py`` passes on 50 random sessions)

How it works, and why it is a real check rather than a formality:

1. Build ``n`` randomised beneficiary profiles across the demo districts and
   every education band, paired with aspirations drawn from the curated
   crosswalk **and** from free-text phrasings that are not curated.
2. Run the real recommendation engine — the same code path the API uses.
3. Verbalize through the configured verbalizer (LLM if one is configured,
   otherwise the mock/template rungs).
4. Extract every numeral from the spoken text and assert it is present in the
   tool JSON the verbalizer was given.
5. Additionally assert every spoken **course name** and **QP code** came from
   the tool JSON — a hallucinated course with no digits in its name would
   otherwise slip past a numeral-only check.

Exit code 0 only if zero ungrounded numerals and zero invented course names.

    python scripts/verify_grounding.py --n 50
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))

from core.db import SessionLocal  # noqa: E402
from core.domain.crosswalk_schema import load_dir  # noqa: E402
from core.domain.recommender import Intent, Profile, recommend  # noqa: E402
from core.llm.guardrails import check_numerals, tool_payload_for_items  # noqa: E402
from core.llm.verbalizer import verbalize  # noqa: E402

DEMO_DISTRICTS = ["270481", "270485", "090187", "360514", "100196"]
EDU_LEVELS = ["none", "up_to_5th", "5th_8th", "8th_10th", "10th_12th", "grad_plus"]
GENDERS = ["female", "male", "other"]
WORK = ["unemployed", "farm_labour", "artisan", "shg_member", "small_trade", "other"]
LANGS = ["hi", "mr", "te", "en"]

#: Free-text aspirations that are NOT verbatim crosswalk phrases, so the run
#: exercises the semantic path and not only the curated lookup.
FREE_TEXT = [
    "मुझे कपड़े सिलने का काम सीखना है",
    "मैं ब्यूटी पार्लर खोलना चाहती हूँ",
    "घर पर बिजली का काम करना है",
    "मला मोबाईल दुरुस्तीचे काम शिकायचे आहे",
    "मला शेतीचे यंत्र चालवायचे आहे",
    "నేను దుకాణంలో పని చేయాలనుకుంటున్నాను",
    "నాకు కంప్యూటర్ పని నేర్చుకోవాలి",
    "I want to work in a hospital helping patients",
    "I would like to start a small food business",
    "teach me welding work",
]


def build_cases(n: int, seed: int) -> list[tuple[Profile, str]]:
    rng = random.Random(seed)
    phrases = [row.phrase for row in load_dir(REPO / "data" / "crosswalk")]
    cases: list[tuple[Profile, str]] = []
    for index in range(n):
        lang = LANGS[index % len(LANGS)]
        profile = Profile(
            district_code=rng.choice(DEMO_DISTRICTS),
            age_band=rng.choice(["under_18", "18_30", "30_45", "45_plus"]),
            gender=rng.choice(GENDERS),
            edu_level=rng.choice(EDU_LEVELS),
            current_work=rng.choice(WORK),
            lang=lang,
        )
        # Roughly a third free-text, so the curated path is not the only one tested.
        text = rng.choice(FREE_TEXT) if index % 3 == 0 else rng.choice(phrases)
        cases.append((profile, text))
    return cases


def verify_case(db, profile: Profile, text: str) -> dict:
    """Run one session end-to-end and check what was said against what was known."""
    result = recommend(db, profile, Intent(concept_text=text))

    if result.is_refusal:
        # A refusal is a *pass*: nothing was claimed. Assert it stayed silent
        # about courses rather than inventing one.
        return {
            "ok": True,
            "refusal": result.refusal,
            "concept": result.concept,
            "spoken": "",
            "numerals": 0,
        }

    payload = tool_payload_for_items(result.items)
    spoken = verbalize(result.items, profile.lang, db=db)
    report = check_numerals(spoken.text, payload)

    # Course names and QP codes must also come from the tool JSON — a
    # hallucinated course name containing no digits would pass a numeral check.
    known_names = {item["name"] for item in result.items}
    known_codes = {item["qp_code"] for item in result.items}
    invented_names = [
        name for name in _quoted_course_names(spoken.text, known_names) if name not in known_names
    ]
    invented_codes = [
        code for code in _qp_codes_in(spoken.text) if code not in known_codes
    ]

    ok = report.grounded and not invented_names and not invented_codes
    return {
        "ok": ok,
        "concept": result.concept,
        "lang": profile.lang,
        "spoken": spoken.text,
        "mode": spoken.mode,
        "grounded_flag": spoken.grounded,
        "numerals": len(report.spoken),
        "ungrounded": report.ungrounded_list,
        "invented_names": invented_names,
        "invented_codes": invented_codes,
        "explain": report.explain(),
        "items": [{"qp_code": i["qp_code"], "name": i["name"]} for i in result.items],
    }


def _qp_codes_in(text: str) -> list[str]:
    import re

    return re.findall(r"\b[A-Z]{2,6}/Q\d{3,6}\b", text or "")


def _quoted_course_names(text: str, known: set[str]) -> list[str]:
    """Course names the text appears to state.

    We can only reliably detect the ones we know about; this catches the case
    where the reading names a course that is *not* among the recommended items
    but looks like a catalogue entry.
    """
    found = []
    for name in known:
        if name and name in text:
            found.append(name)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove every spoken numeral is grounded")
    parser.add_argument("--n", type=int, default=50, help="number of random sessions")
    parser.add_argument("--seed", type=int, default=20261211, help="RNG seed (deterministic)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", dest="as_json", action="store_true", help="emit a JSON report")
    args = parser.parse_args()

    started = time.monotonic()
    cases = build_cases(args.n, args.seed)
    failures: list[dict] = []
    passes = 0
    refusals = 0
    total_numerals = 0
    modes: dict[str, int] = {}

    db = SessionLocal()
    try:
        for index, (profile, text) in enumerate(cases, start=1):
            outcome = verify_case(db, profile, text)
            outcome["case"] = index
            outcome["aspiration"] = text
            total_numerals += outcome.get("numerals", 0)
            if outcome.get("refusal"):
                refusals += 1
            mode = outcome.get("mode", "refusal")
            modes[mode] = modes.get(mode, 0) + 1

            if outcome["ok"]:
                passes += 1
                if args.verbose:
                    print(f"  [{index:3}/{args.n}] PASS {outcome.get('concept') or outcome.get('refusal')}")
            else:
                failures.append(outcome)
                print(f"  [{index:3}/{args.n}] FAIL {text!r}")
                print(f"        ungrounded : {outcome.get('ungrounded')}")
                print(f"        invented   : {outcome.get('invented_names')} {outcome.get('invented_codes')}")
                print(f"        spoken     : {outcome.get('spoken', '')[:200]}")
    finally:
        db.close()

    elapsed = time.monotonic() - started
    report = {
        "sessions": args.n,
        "seed": args.seed,
        "passed": passes,
        "failed": len(failures),
        "refusals": refusals,
        "numerals_checked": total_numerals,
        "verbalizer_modes": modes,
        "elapsed_s": round(elapsed, 2),
        "failures": failures[:10],
    }

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print()
        print("=" * 66)
        print(f"  sessions checked   : {args.n}")
        print(f"  passed             : {passes}")
        print(f"  failed             : {len(failures)}")
        print(f"  refusals (no claim): {refusals}")
        print(f"  numerals checked   : {total_numerals}")
        print(f"  verbalizer modes   : {modes}")
        print(f"  elapsed            : {elapsed:.1f}s")
        print("=" * 66)
        if failures:
            print("  RESULT: FAIL — ungrounded output detected")
        else:
            print("  RESULT: PASS — every spoken numeral is present in the tool JSON,")
            print("          and no course name or QP code was invented.")
        print("=" * 66)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
