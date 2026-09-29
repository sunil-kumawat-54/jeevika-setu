"""Central configuration for services/core.

Every external dependency is switchable to a `mock` twin by env var
(ARCHITECTURE.md §2, design invariant 1) so the demo never hard-depends on a
vendor.  Variable names mirror TECH_STACK.md §5 exactly.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Core
    env: str = "demo"
    database_url: str = "postgresql+psycopg://avsar:avsar@localhost:5432/avsar"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-prod-avsar-demo-secret"
    jwt_access_min: int = 30
    jwt_refresh_h: int = 12
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"

    # LLM
    llm_provider: str = "mock"  # mock|anthropic|template
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"
    llm_max_tokens: int = 512

    # Speech
    voice_provider: str = "mock"  # bhashini|sarvam|azure|whisper|mock
    voice_provider_order: str = "sarvam,bhashini,azure,whisper,mock"
    bhashini_user_id: str = ""
    bhashini_api_key: str = ""
    bhashini_config_url: str = (
        "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
    )
    bhashini_config_cache_s: int = 600
    sarvam_api_key: str = ""
    sarvam_base: str = "https://api.sarvam.ai"
    #: Verified against the published API, not against the TECH_STACK summary
    #: (docs/decisions.md D-047). saarika:* is legacy; saaras:v3 is the current
    #: default model and takes a mode. mode=transcribe keeps the transcript in
    #: the beneficiary's own language — translate would return English.
    sarvam_stt_model: str = "saaras:v3"
    sarvam_stt_mode: str = "transcribe"
    #: TECH_STACK section 2.2 chose bulbul:v2 on cost (Rs 15 vs Rs 30/10K chars),
    #: but the live API now rejects it: HTTP 400 "Model 'bulbul:v2' has been
    #: deprecated. Please use 'bulbul:v3' instead." Verified 2026-09-12; see
    #: docs/decisions.md D-048. Speakers are model-specific, so these two move
    #: together: `anushka` is a v2 voice and is not valid for v3.
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    voice_timeout_s: float = 8.0
    provider_demote_after: int = 2

    # Embeddings
    embedding_backend: str = "auto"  # auto|e5|hashing
    embedding_model: str = "intfloat/multilingual-e5-base"
    embedding_dim: int = 768

    # RULE 3 — the government source hostnames (PMAJAY_BASE, KAUSHALVERSE_BASE,
    # INGEST_QPS, INGEST_UA) deliberately do NOT appear in this class. They are
    # ingestion-only and are read straight from the environment by
    # pipelines/common.py, so the runtime settings object cannot even name a
    # government portal, let alone call one.
    allow_live_check: bool = False

    # Demo switches
    mock_otp: str = "123456"
    seed_demo_users: bool = True
    demo_officer_email: str = "officer@demo"
    demo_officer_password: str = "avsar-demo-2026"
    demo_viewer_email: str = "viewer@demo"
    demo_viewer_password: str = "avsar-demo-2026"
    demo_admin_email: str = "admin@demo"
    demo_admin_password: str = "avsar-demo-2026"

    # Retention / limits
    retention_days: int = 90
    #: Load the embedding model in a background thread at startup. Without it the
    #: FIRST beneficiary turn after a cold boot pays the whole sentence-transformer
    #: load (measured 11.3 s on this machine) — a demo-losing first impression.
    warm_start: bool = True
    rate_limit_auth_per_min: int = 10
    rate_limit_turn_per_min: int = 30

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_mock_voice(self) -> bool:
        return self.voice_provider.lower() == "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
