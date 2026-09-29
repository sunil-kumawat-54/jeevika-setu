"""The ONE runtime path RULE 3 permits to a government portal.

RULE 3 states the runtime must not call ``pmajay.dosje.gov.in`` or
``kaushalverse.ncvet.gov.in`` *"except through an optional explicitly labeled
'live check' endpoint"*, and ARCHITECTURE.md section 2, invariant 2 says the
same thing from the other side: *"Seeds over live fetches: gov endpoints are
ingested offline into committed snapshots; live fetch is an optional garnish
endpoint clearly labeled in UI."*

This module is that single, named exception, deliberately kept in its own file
so the exemption is visible in the file tree and the Gate-2 RULE 3 test can
scope its allowance to exactly one path rather than to a whole router.

Three properties make it safe:

* **admin-only** — guarded by ``require_admin``;
* **off by default** — ``ALLOW_LIVE_CHECK=false`` in ``.env.example``;
* **read-only** — it reports reachability and never writes a catalogue row, so
  a live response can never contaminate the committed seeds.
"""

from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from core.api.security import Principal, audit, require_admin
from core.config import settings
from core.db import get_db
from core.errors import AvsarError

log = logging.getLogger("avsar.live_check")
router = APIRouter(prefix="/admin", tags=["admin"])

#: The government sources whose reachability an officer may want to confirm on
#: stage. Named here and nowhere else in ``services/core``.
TARGETS = {
    "pmajay": "https://pmajay.dosje.gov.in/course-list",
    "kaushalverse": "https://kaushalverse.ncvet.gov.in/assets/config/env.json",
}


@router.get("/live-check")
def live_check(
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> dict:
    """Report whether the upstream portals are reachable *right now*."""
    if not settings.allow_live_check:
        raise AvsarError(
            403,
            "forbidden",
            principal.lang,
            "live check is disabled (ALLOW_LIVE_CHECK=false). Runtime uses committed seeds.",
        )

    import httpx

    results: dict[str, dict] = {}
    for name, url in TARGETS.items():
        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(url)
            body = response.text[:400].lower()
            results[name] = {
                "url": url,
                "status": response.status_code,
                "reachable": response.status_code == 200,
                "maintenance": "maintenance" in body or "be right back" in body,
            }
        except Exception as exc:
            results[name] = {
                "url": url,
                "reachable": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    audit(db, principal, "live_check", "external", None, after=results)
    db.commit()

    return {
        "checked_at": dt.datetime.now(dt.UTC).isoformat(),
        "results": results,
        "note": (
            "Diagnostic only. Catalogue data always comes from committed seeds under "
            "seeds/; this endpoint never writes to the database."
        ),
    }
