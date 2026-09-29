"""Pipeline 00 — district seed.

ARCHITECTURE.md section 4, final paragraph:
    "District codes: use Census 2011 LGD-style codes (state+district); a static
     districts(code,name_hi,name_en) seed ships in-repo."

Source: **Local Government Directory (LGD) — Districts** on data.gov.in,
resource ``37231365-78ba-44d5-ac22-3deec40b9197``. research.md section 7.2
verified the data.gov.in API end-to-end:
``GET https://api.data.gov.in/resource/{id}?api-key=...&format=json&offset=&limit=``
and noted that the widely-published demo key currently grants read access.

Each record carries both the LGD code and the Census-2011 code, plus the real
local-script district name. AVSAR never transliterates: ``name_hi`` / ``name_mr``
/ ``name_te`` are filled **only** where the state's official language is that
language, and the UI falls back name_<lang> -> name_local -> name_en.

If data.gov.in is unreachable the pipeline writes a structurally identical
synthetic snapshot covering the five demo districts with ``synthetic: true``.
"""

from __future__ import annotations

import logging
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from pipelines.common import (  # noqa: E402
    SEEDS,
    PipelineResult,
    Provenance,
    RateLimiter,
    build_client,
    clean,
    env,
    env_float,
    record_run,
    write_seed,
)

log = logging.getLogger("00_districts")

NAME = "00_fetch_districts"
RESOURCE_ID = "37231365-78ba-44d5-ac22-3deec40b9197"
DATA_GOV_BASE = "https://api.data.gov.in/resource"
#: data.gov.in's published sample key (research.md section 7.2). Overridable via
#: DATA_GOV_API_KEY; it is a public demo credential, not a secret.
DEFAULT_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
PAGE = 200

SEED_PATH = SEEDS / "districts.json"

#: State -> the language AVSAR can safely claim the local name is written in.
#: Only states whose official language is one of our four UI languages appear;
#: everything else keeps name_local without asserting a language.
STATE_LANG = {
    "hi": {
        "BIHAR", "CHHATTISGARH", "DELHI", "HARYANA", "HIMACHAL PRADESH",
        "JHARKHAND", "MADHYA PRADESH", "RAJASTHAN", "UTTAR PRADESH",
        "UTTARAKHAND", "THE GOVERNMENT OF NCT OF DELHI",
    },
    "mr": {"MAHARASHTRA"},
    "te": {"TELANGANA", "ANDHRA PRADESH"},
}

#: The five demo districts the dashboard is seeded across (PLAN.md section 5.1
#: pipeline 07). Used as the synthetic fallback and by the demo seeder.
DEMO_DISTRICTS = [
    {"state": "MAHARASHTRA", "name_en": "Latur", "lang": "mr"},
    {"state": "MAHARASHTRA", "name_en": "Nanded", "lang": "mr"},
    {"state": "UTTAR PRADESH", "name_en": "Varanasi", "lang": "hi"},
    {"state": "TELANGANA", "name_en": "Nalgonda", "lang": "te"},
    {"state": "BIHAR", "name_en": "Gaya", "lang": "hi"},
]


#: Unicode blocks we can verify a local name actually belongs to. LGD has not
#: localised every district (some ``district_name_local`` values are still plain
#: Latin, e.g. "VARANASI"), and calling a Latin string "the Hindi name" would be
#: a fabrication. A name is only claimed for a language when its script matches.
SCRIPT_RANGES = {
    "hi": ((0x0900, 0x097F),),  # Devanagari
    "mr": ((0x0900, 0x097F),),  # Devanagari
    "te": ((0x0C00, 0x0C7F),),  # Telugu
}


def _is_script(text: str, lang: str) -> bool:
    ranges = SCRIPT_RANGES.get(lang)
    if not ranges or not text:
        return False
    return any(
        any(low <= ord(ch) <= high for low, high in ranges)
        for ch in text
    )


def _lang_for_state(state_name: str) -> str | None:
    upper = (state_name or "").upper()
    for lang, states in STATE_LANG.items():
        if upper in states:
            return lang
    return None


def _compose_code(state_code: str, district_code: str) -> str:
    """state+district composite, as ARCHITECTURE section 4 requires."""
    return f"{int(state_code):02d}{int(district_code):04d}"


def _normalise(record: dict) -> dict | None:
    state_code = clean(record.get("state_code"))
    district_code = clean(record.get("district_code"))
    name_en = clean(record.get("district_name_english"))
    state_name = clean(record.get("state_name_english"))
    if not (state_code and district_code and name_en and state_name):
        return None
    try:
        code = _compose_code(state_code, district_code)
    except (TypeError, ValueError):
        return None

    name_local = clean(record.get("district_name_local"))
    lang = _lang_for_state(state_name)
    row = {
        "code": code,
        "state_code": str(int(state_code)),
        "state_name": state_name.title(),
        "lgd_district_code": str(int(district_code)),
        "census2011_state_code": clean(record.get("state_census2011_code")),
        "census2011_district_code": clean(record.get("district_census2011_code")),
        "name_en": name_en.title(),
        "name_local": name_local,
        "name_hi": None,
        "name_mr": None,
        "name_te": None,
        "synthetic": False,
    }
    if lang and name_local and _is_script(name_local, lang):
        row[f"name_{lang}"] = name_local
    return row


def fetch_live() -> tuple[list[dict], Provenance]:
    key = env("DATA_GOV_API_KEY", DEFAULT_KEY)
    url = f"{DATA_GOV_BASE}/{RESOURCE_ID}"
    prov = Provenance(pipeline=NAME, source_url=url, mode="live")
    limiter = RateLimiter(env_float("INGEST_QPS", 1.0))
    rows: list[dict] = []

    with build_client(env("INGEST_UA", "AVSAR-SIH-Research/1.0"), timeout=60.0) as client:
        offset = 0
        total = None
        while True:
            limiter.wait()
            resp = client.get(
                url,
                params={"api-key": key, "format": "json", "offset": offset, "limit": PAGE},
            )
            prov.http_status = resp.status_code
            resp.raise_for_status()
            payload = resp.json()
            if total is None:
                total = int(payload.get("total") or 0)
                prov.notes.append(f"data.gov.in reports total={total} districts")
            batch = payload.get("records") or []
            if not batch:
                break
            for raw in batch:
                row = _normalise(raw)
                if row:
                    rows.append(row)
            offset += len(batch)
            log.info("fetched %d/%s districts", offset, total)
            if total and offset >= total:
                break

    # Deduplicate on the composite code, keeping the first occurrence.
    seen: set[str] = set()
    unique = []
    for row in sorted(rows, key=lambda r: r["code"]):
        if row["code"] in seen:
            continue
        seen.add(row["code"])
        unique.append(row)
    prov.notes.append(f"{len(unique)} unique state+district codes after dedupe")
    prov.notes.append("Local-script names are LGD's own; no transliteration was generated.")
    return unique, prov


def synthetic_snapshot(reason: str, status: int | None) -> tuple[list[dict], Provenance]:
    """Structurally identical fallback — RULE: never dress invented rows as official."""
    prov = Provenance(
        pipeline=NAME,
        source_url=f"{DATA_GOV_BASE}/{RESOURCE_ID}",
        mode="synthetic",
        synthetic=True,
        http_status=status,
        failure_reason=reason,
        fallback_note=(
            "data.gov.in LGD districts resource unreachable; emitted a structurally "
            "identical snapshot limited to the five demo districts. Every record has "
            "synthetic=true and no code is presented as an official LGD/Census value."
        ),
    )
    rows = []
    for idx, demo in enumerate(DEMO_DISTRICTS, start=1):
        code = f"99{idx:04d}"  # 99 = reserved synthetic state code, never a real LGD state
        row = {
            "code": code,
            "state_code": "99",
            "state_name": demo["state"].title(),
            "lgd_district_code": str(idx),
            "census2011_state_code": None,
            "census2011_district_code": None,
            "name_en": demo["name_en"],
            "name_local": None,
            "name_hi": None,
            "name_mr": None,
            "name_te": None,
            "synthetic": True,
        }
        rows.append(row)
    return rows, prov


def run() -> PipelineResult:
    try:
        rows, prov = fetch_live()
        if len(rows) < 100:
            raise RuntimeError(f"only {len(rows)} districts returned; refusing a partial snapshot")
    except Exception as exc:
        log.warning("live district fetch failed (%s: %s) — falling back", type(exc).__name__, exc)
        status = getattr(getattr(exc, "response", None), "status_code", None)
        rows, prov = synthetic_snapshot(f"{type(exc).__name__}: {exc}", status)

    write_seed(SEED_PATH, rows, prov)
    result = PipelineResult(name=NAME, seed_path=SEED_PATH, provenance=prov)
    record_run(result)
    log.info("wrote %s (%d rows, mode=%s)", SEED_PATH.name, prov.rows, prov.mode)
    return result


if __name__ == "__main__":
    run()
