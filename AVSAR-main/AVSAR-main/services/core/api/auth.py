"""Authentication — ARCHITECTURE.md sections 5 and 9.

    POST /auth/request-otp {phone}      -> {otp_hint}   # mock mode returns fixed OTP
    POST /auth/verify-otp  {phone, otp} -> {access_token}
    POST /auth/login       {email, password} -> {access_token}   # officers/admin

Posture, straight from ARCHITECTURE section 9:

* Beneficiary: phone -> OTP-lite, **no password**, minimal PII, *"no name
  required ever"* (RULE 6). The demo OTP is printed to the server log rather
  than sent, so no SMS provider is needed and no credential leaves the machine.
* Officers: email + password hashed with **argon2id**, roles viewer/officer/admin.
* JWT access 30 min + refresh 12 h.

Rate limiting on ``/auth/*`` is required by TECH_STACK section 9 and is applied
by the shared Redis token bucket, which degrades to in-process counting when
Redis is down (a dead cache must not lock everyone out mid-demo).
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.api.ratelimit import rate_limit
from core.api.security import (
    Principal,
    create_token,
    create_token_pair,
    current_principal,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from core.config import settings
from core.db import get_db
from core.errors import AvsarError
from core.metrics import incr
from core.models.tables import Role, User

log = logging.getLogger("avsar.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

PHONE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian mobile numbering


def _lang(request: Request) -> str:
    lang = request.headers.get("x-avsar-lang") or request.query_params.get("lang") or "hi"
    return lang if lang in ("hi", "mr", "te", "en") else "hi"


class OtpRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=13)

    @field_validator("phone")
    @classmethod
    def _normalise(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if not PHONE_RE.match(digits):
            raise ValueError("not a valid 10-digit Indian mobile number")
        return digits


class OtpVerify(OtpRequest):
    otp: str = Field(min_length=4, max_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/request-otp")
def request_otp(
    payload: OtpRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("auth", settings.rate_limit_auth_per_min)),
) -> dict:
    """OTP-lite. In demo mode the OTP is fixed and printed to the server log.

    No SMS provider is contacted, so this works airplane-mode (RULE 1). A real
    deployment swaps in an SMS adapter behind this same endpoint.
    """
    otp = settings.mock_otp
    log.info(
        "OTP for %s is %s (demo mode — printed, never sent)",
        payload.phone,
        otp,
        extra={"event": "otp_issued"},
    )
    incr("auth_otp_requested_total")

    # Create the beneficiary row lazily. RULE 6: phone only, no name, no password.
    user = db.execute(select(User).where(User.phone == payload.phone)).scalar_one_or_none()
    if user is None:
        user = User(phone=payload.phone, role=Role.beneficiary, lang_pref=_lang(request))
        db.add(user)
        db.commit()

    body = {
        "sent": True,
        "channel": "log" if settings.env == "demo" else "sms",
        "expires_in": 300,
    }
    if settings.env == "demo":
        # Demo only: surface the OTP so a judge can complete the flow unaided.
        body["otp_hint"] = otp
        body["note"] = "demo mode — OTP is fixed via MOCK_OTP and is not sent by SMS"
    return body


@router.post("/verify-otp")
def verify_otp(
    payload: OtpVerify,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("auth", settings.rate_limit_auth_per_min)),
) -> dict:
    lang = _lang(request)
    if payload.otp != settings.mock_otp:
        incr("auth_otp_failed_total")
        raise AvsarError(401, "invalid_otp", lang)

    user = db.execute(select(User).where(User.phone == payload.phone)).scalar_one_or_none()
    if user is None:
        user = User(phone=payload.phone, role=Role.beneficiary, lang_pref=lang)
        db.add(user)
        db.commit()

    incr("auth_otp_verified_total")
    tokens = create_token_pair(str(user.id), user.role.value, lang=user.lang_pref or lang)
    return {**tokens, "user_id": user.id, "role": user.role.value}


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("auth", settings.rate_limit_auth_per_min)),
) -> dict:
    """Officer / viewer / admin login. argon2id verification."""
    lang = _lang(request)
    email = payload.email.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        # Same response either way — never reveal whether the account exists.
        incr("auth_login_failed_total")
        raise AvsarError(401, "unauthorized", lang, "invalid email or password")

    if user.role == Role.beneficiary:
        raise AvsarError(403, "forbidden", lang, "beneficiaries sign in with a phone OTP")

    if needs_rehash(user.password_hash or ""):
        user.password_hash = hash_password(payload.password)
        db.commit()

    incr("auth_login_total", role=user.role.value)
    tokens = create_token_pair(str(user.id), user.role.value, lang=user.lang_pref or lang)
    return {**tokens, "user_id": user.id, "role": user.role.value, "email": user.email}


@router.post("/refresh")
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("auth", settings.rate_limit_auth_per_min)),
) -> dict:
    """Exchange a refresh token for a new access token (JWT access 30 min)."""
    lang = _lang(request)
    from core.api.security import REFRESH

    claims = decode_token(payload.refresh_token, expected=REFRESH, lang=lang)
    user = db.execute(select(User).where(User.id == int(claims["sub"]))).scalar_one_or_none()
    if user is None:
        raise AvsarError(401, "unauthorized", lang, "user no longer exists")
    return {
        "access_token": create_token(
            str(user.id), user.role.value, lang=claims.get("lang", lang)
        ),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_min * 60,
        "role": user.role.value,
    }


@router.get("/me")
def me(principal: Principal = Depends(current_principal), db: Session = Depends(get_db)) -> dict:
    """Who am I? Returns no name, because no name is ever collected (RULE 6)."""
    user = db.execute(select(User).where(User.id == principal.user_id)).scalar_one_or_none()
    return {
        "user_id": principal.user_id,
        "role": principal.role,
        "lang": principal.lang,
        "email": user.email if user else None,
        "phone": user.phone if user else None,
    }
