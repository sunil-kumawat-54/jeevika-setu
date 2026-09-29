"""scripts/purge_old.py — apply the retention policy.

ARCHITECTURE.md section 11 (Privacy & compliance posture):
    Retention: sessions purgeable by script after N days
    (``scripts/purge_old.py``) for the pilot story.

What it deletes, and what it deliberately keeps:

DELETED with the session
    ``transcripts``     — raw ASR text, the most personal thing the system holds
    ``recommendations`` — per-session output rows
    ``consents``        — the consent record is *about* that session; keeping a
                          consent record after deleting what it consented to
                          would be a record of a person with nothing to justify
                          holding it
    the ``sessions`` row itself

KEPT
    ``audit_log`` — the tamper-evidence trail for officer/admin actions. It
    holds actor ids and actions, never beneficiary speech. Deleting it with the
    data it describes would destroy the accountability record that makes the
    deletion itself demonstrable. A purge writes its OWN audit row, so a
    reviewer can see that data was removed, when, and how much.

    ``users`` — a beneficiary row is phone-only and nameless (RULE 6). Use
    ``--orphan-users`` to also remove beneficiary users left with no sessions;
    it is off by default so that a repeat caller's OTP history is not silently
    rewritten mid-pilot.

Safety: a dry run is the default. Nothing is deleted unless ``--apply`` is
passed, and the script prints exactly what it would remove first.

    python scripts/purge_old.py --days 90                 # dry run
    python scripts/purge_old.py --days 90 --apply
    python scripts/purge_old.py --days 90 --apply --orphan-users
    make purge DAYS=30
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))

from core.config import settings  # noqa: E402
from core.db import session_scope  # noqa: E402
from core.models.tables import (  # noqa: E402
    AuditLog,
    Consent,
    Recommendation,
    Role,
    Transcript,
    User,
)
from core.models.tables import Session as SessionRow  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
log = logging.getLogger("purge")


def survey(db, cutoff: dt.datetime) -> dict:
    """Count exactly what a purge would remove, without removing anything."""
    old_ids = [
        row[0]
        for row in db.execute(
            select(SessionRow.id).where(SessionRow.created_at < cutoff)
        ).all()
    ]
    if not old_ids:
        return {"sessions": 0, "transcripts": 0, "recommendations": 0, "consents": 0, "ids": []}

    def count(model) -> int:
        return int(
            db.execute(
                select(func.count())
                .select_from(model)
                .where(model.session_id.in_(old_ids))
            ).scalar_one()
        )

    return {
        "sessions": len(old_ids),
        "transcripts": count(Transcript),
        "recommendations": count(Recommendation),
        "consents": count(Consent),
        "ids": old_ids,
    }


def purge(db, cutoff: dt.datetime, orphan_users: bool) -> dict:
    """Delete sessions older than ``cutoff`` and everything bound to them."""
    plan = survey(db, cutoff)
    old_ids = plan.pop("ids")
    if not old_ids:
        return {**plan, "users": 0}

    # sessions.consent_id references consents, and consents.session_id
    # references sessions — break the cycle before deleting either side.
    db.execute(
        SessionRow.__table__.update()
        .where(SessionRow.id.in_(old_ids))
        .values(consent_id=None)
    )
    db.execute(delete(Transcript).where(Transcript.session_id.in_(old_ids)))
    db.execute(delete(Recommendation).where(Recommendation.session_id.in_(old_ids)))
    db.execute(delete(Consent).where(Consent.session_id.in_(old_ids)))
    db.execute(delete(SessionRow).where(SessionRow.id.in_(old_ids)))

    removed_users = 0
    if orphan_users:
        orphans = [
            row[0]
            for row in db.execute(
                select(User.id).where(
                    User.role == Role.beneficiary,
                    ~select(SessionRow.id)
                    .where(SessionRow.user_id == User.id)
                    .exists(),
                )
            ).all()
        ]
        if orphans:
            db.execute(delete(User).where(User.id.in_(orphans)))
            removed_users = len(orphans)

    # The purge audits itself: the retention action stays visible even though
    # the data it acted on is gone.
    db.add(
        AuditLog(
            actor=None,
            action="retention_purge",
            entity="sessions",
            entity_id=None,
            before={"cutoff": cutoff.isoformat(), **plan},
            after={"users_removed": removed_users},
        )
    )
    return {**plan, "users": removed_users}


def main() -> int:
    parser = argparse.ArgumentParser(description="apply the retention policy")
    parser.add_argument(
        "--days",
        type=int,
        default=settings.retention_days,
        help=f"delete sessions older than N days (default {settings.retention_days} from RETENTION_DAYS)",
    )
    parser.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    parser.add_argument(
        "--orphan-users",
        action="store_true",
        help="also delete beneficiary users left with no sessions",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    if args.days < 0:
        print("--days must be >= 0")
        return 2

    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=args.days)

    with session_scope() as db:
        total = int(db.execute(select(func.count()).select_from(SessionRow)).scalar_one())
        if args.apply:
            result = purge(db, cutoff, args.orphan_users)
            action = "DELETED"
        else:
            result = survey(db, cutoff)
            result.pop("ids", None)
            result["users"] = 0
            action = "WOULD DELETE (dry run)"

    payload = {
        "retention_days": args.days,
        "cutoff_utc": cutoff.isoformat(),
        "applied": bool(args.apply),
        "sessions_before": total,
        **result,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print()
    print("AVSAR retention purge (ARCHITECTURE.md S11)")
    print(f"  retention: {args.days} days     cutoff: {cutoff.isoformat(timespec='seconds')}")
    print(f"  sessions in database before: {total}")
    print()
    print(f"  {action}:")
    print(f"    sessions        {result['sessions']}")
    print(f"    transcripts     {result['transcripts']}")
    print(f"    recommendations {result['recommendations']}")
    print(f"    consents        {result['consents']}")
    if args.orphan_users or result.get("users"):
        print(f"    orphan users    {result['users']}")
    print()
    print("  kept: audit_log (accountability trail; holds no beneficiary speech)")
    if args.apply:
        print("  an audit_log row records this purge.")
    else:
        print("  dry run — nothing was deleted. Re-run with --apply to delete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
