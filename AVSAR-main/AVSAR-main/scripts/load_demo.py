"""`make seed` — load committed seeds, create demo accounts, build vector indexes.

TECH_STACK.md section 7:
    seed  # load seeds/*.json into DB, create demo users, build vector indexes

Everything here is idempotent: run it as many times as you like and the
database converges to the same state. It never reaches the network.
"""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))

from core.config import settings  # noqa: E402
from core.db import session_scope  # noqa: E402
from core.models.tables import Role, User  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from pipelines.load_to_db import load_all, table_counts  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
log = logging.getLogger("load_demo")


def _load_pipeline(filename: str):
    """Import a numbered pipeline module by path (``07_x.py`` is not a valid name)."""
    import importlib.util

    path = REPO / "pipelines" / filename
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def ensure_demo_users(db) -> dict[str, str]:
    """Create officer/viewer/admin accounts from env (ARCHITECTURE section 9).

    Passwords come from the environment, never from a literal in git (RULE 9).
    Beneficiaries are NOT created here — they arrive via OTP-lite and are
    phone-only rows with no password and no name (RULE 6).
    """
    from core.api.security import hash_password

    wanted = [
        (settings.demo_officer_email, settings.demo_officer_password, Role.officer),
        (settings.demo_viewer_email, settings.demo_viewer_password, Role.viewer),
        (settings.demo_admin_email, settings.demo_admin_password, Role.admin),
    ]
    created = {}
    for email, password, role in wanted:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            user = User(email=email, role=role, password_hash=hash_password(password), lang_pref="en")
            db.add(user)
            created[email] = "created"
        else:
            # Keep the password in sync with .env so a judge is never locked out.
            user.password_hash = hash_password(password)
            user.role = role
            created[email] = "updated"
    db.flush()
    return created


def reindex_vectors(db) -> None:
    """ANALYZE the vector tables so HNSW planning is sane after a bulk load."""
    for table in ("qp_descriptions", "doc_chunks", "crosswalk", "courses", "centre_supply"):
        db.execute(text(f"ANALYZE {table}"))
    log.info("analyzed vector + catalogue tables")


def main() -> int:
    parser = argparse.ArgumentParser(description="Load AVSAR seeds and demo accounts")
    parser.add_argument("--skip-users", action="store_true", help="do not touch demo accounts")
    parser.add_argument("--skip-sessions", action="store_true", help="do not seed demo sessions")
    args = parser.parse_args()

    with session_scope() as db:
        counts = load_all(db)
        log.info("seed load: %s", json.dumps(counts))

        if not args.skip_users and settings.seed_demo_users:
            try:
                status = ensure_demo_users(db)
                log.info("demo users: %s", json.dumps(status))
            except ImportError:
                log.warning("auth module not built yet — skipping demo users")

        if not args.skip_sessions:
            # Pipeline modules are numbered (07_...), so they are not importable
            # by name — load by path.
            module = _load_pipeline("07_seed_users_demo.py")
            if module is None:
                log.info("demo-session seeder not present — skipping")
            else:
                made = module.seed_sessions(db)
                module.attach_recommendations(db)
                log.info("demo sessions: %d present", made)

        reindex_vectors(db)
        final = table_counts(db)

    print(json.dumps(final, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
