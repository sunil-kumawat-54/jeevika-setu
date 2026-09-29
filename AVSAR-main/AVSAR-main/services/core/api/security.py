"""Password hashing, JWTs and RBAC primitives.

ARCHITECTURE.md section 9:
* Beneficiary: phone -> OTP-lite (mock OTP printed to server log in demo;
  pluggable SMS adapter for prod). No password. Minimal PII: no name required.
* Officers: email+password (**argon2id**), roles viewer/officer/admin;
  route-level guards + row-level (individual beneficiary rows hidden from
  ``viewer``).
* JWT access 30 min + refresh 12 h; all admin mutations audited.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from core.db import get_db
from core.errors import AvsarError
from core.models.tables import AuditLog, Role, User

log = logging.getLogger("avsar.security")

ALGORITHM = "HS256"
ACCESS = "access"
REFRESH = "refresh"

#: argon2**id** explicitly (Type.ID), not argon2i/argon2d.
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

bearer = HTTPBearer(auto_error=False)


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def create_token(
    subject: str,
    role: str,
    kind: str = ACCESS,
    *,
    lang: str = "hi",
    extra: dict[str, Any] | None = None,
) -> str:
    if kind == ACCESS:
        expires = _now() + dt.timedelta(minutes=settings.jwt_access_min)
    else:
        expires = _now() + dt.timedelta(hours=settings.jwt_refresh_h)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "typ": kind,
        "lang": lang,
        "iat": int(_now().timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_token_pair(subject: str, role: str, lang: str = "hi") -> dict[str, Any]:
    return {
        "access_token": create_token(subject, role, ACCESS, lang=lang),
        "refresh_token": create_token(subject, role, REFRESH, lang=lang),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_min * 60,
        "role": role,
    }


def decode_token(token: str, *, expected: str | None = ACCESS, lang: str = "hi") -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AvsarError(401, "unauthorized", lang, "token expired")
    except jwt.InvalidTokenError as exc:
        raise AvsarError(401, "unauthorized", lang, f"invalid token: {type(exc).__name__}")
    if expected and payload.get("typ") != expected:
        raise AvsarError(401, "unauthorized", lang, f"expected a {expected} token")
    return payload


# --------------------------------------------------------------------------
# Principals & RBAC
# --------------------------------------------------------------------------


class Principal:
    """The authenticated caller, resolved from a bearer token."""

    __slots__ = ("user_id", "role", "lang", "claims")

    def __init__(self, user_id: int | None, role: str, lang: str, claims: dict):
        self.user_id = user_id
        self.role = role
        self.lang = lang
        self.claims = claims

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Principal(user_id={self.user_id}, role={self.role!r})"

    @property
    def is_beneficiary(self) -> bool:
        return self.role == Role.beneficiary.value

    @property
    def is_staff(self) -> bool:
        return self.role in {Role.viewer.value, Role.officer.value, Role.admin.value}

    def at_least(self, minimum: Role) -> bool:
        return RANK.get(self.role, -1) >= RANK[minimum.value]


#: viewer < officer < admin. Beneficiary sits outside the staff ladder.
RANK: dict[str, int] = {
    Role.beneficiary.value: 0,
    Role.viewer.value: 1,
    Role.officer.value: 2,
    Role.admin.value: 3,
}


def _lang_from_request(request: Request) -> str:
    lang = request.headers.get("x-avsar-lang") or request.query_params.get("lang") or "hi"
    return lang if lang in ("hi", "mr", "te", "en") else "hi"


def current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    """Require a valid access token. 401 with a speakable body when absent."""
    lang = _lang_from_request(request)
    if credentials is None or not credentials.credentials:
        raise AvsarError(401, "unauthorized", lang, "missing bearer token")
    claims = decode_token(credentials.credentials, expected=ACCESS, lang=lang)
    raw_id = claims.get("sub")
    user_id: int | None
    try:
        user_id = int(raw_id) if raw_id not in (None, "", "anonymous") else None
    except (TypeError, ValueError):
        user_id = None
    return Principal(user_id, claims.get("role", Role.beneficiary.value), claims.get("lang", lang), claims)


def optional_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal | None:
    """For endpoints an anonymous beneficiary may also reach."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return current_principal(request, credentials)
    except AvsarError:
        return None


def require_role(*allowed: Role):
    """Route guard. 403 with a speakable body when the role is insufficient."""
    allowed_values = {r.value for r in allowed}

    def dependency(
        request: Request, principal: Principal = Depends(current_principal)
    ) -> Principal:
        if principal.role not in allowed_values:
            raise AvsarError(
                403,
                "forbidden",
                _lang_from_request(request),
                f"role '{principal.role}' is not one of {sorted(allowed_values)}",
            )
        return principal

    return dependency


def require_min_role(minimum: Role):
    """Route guard on the viewer < officer < admin ladder."""

    def dependency(
        request: Request, principal: Principal = Depends(current_principal)
    ) -> Principal:
        if not principal.at_least(minimum):
            raise AvsarError(
                403,
                "forbidden",
                _lang_from_request(request),
                f"role '{principal.role}' is below required '{minimum.value}'",
            )
        return principal

    return dependency


require_viewer = require_min_role(Role.viewer)
require_officer = require_min_role(Role.officer)
require_admin = require_min_role(Role.admin)


def load_user(db: Session, user_id: int | None) -> User | None:
    if user_id is None:
        return None
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


# --------------------------------------------------------------------------
# Audit
# --------------------------------------------------------------------------


def audit(
    db: Session,
    principal: Principal | None,
    action: str,
    entity: str,
    entity_id: str | int | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    """Write an ``audit_log`` row.

    ARCHITECTURE.md section 9: *"all admin mutations are audited"*. Gate 6 and
    Gate 9 tests assert a row appears for every admin write, so this must never
    be optional or best-effort on a mutation path.
    """
    entry = AuditLog(
        actor=principal.user_id if principal else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=before,
        after=after,
    )
    db.add(entry)
    db.flush()
    log.info(
        "audit %s %s#%s by %s",
        action,
        entity,
        entity_id,
        principal.user_id if principal else "anonymous",
        extra={"event": "audit"},
    )
    return entry


__all__ = [
    "ACCESS",
    "REFRESH",
    "Principal",
    "audit",
    "create_token",
    "create_token_pair",
    "current_principal",
    "decode_token",
    "get_db",
    "hash_password",
    "load_user",
    "needs_rehash",
    "optional_principal",
    "require_admin",
    "require_officer",
    "require_role",
    "require_viewer",
    "verify_password",
]
