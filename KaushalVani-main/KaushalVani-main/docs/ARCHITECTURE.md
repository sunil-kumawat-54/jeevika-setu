# KaushalVani Architecture Specification

KaushalVani is built on a modular monolith backend architecture paired with a dedicated Python AI Service and PostgreSQL database.

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    BENEFICIARY INTERFACE                    │
│      React.js + Vite + TypeScript (Voice & Accessibility)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND API GATEWAY                     │
│               Node.js + Express + TypeScript                │
│    • Auth & Session Manager   • Qualification Router        │
│    • Beneficiary Profile DB   • Distance & Map Matching     │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐ ┌─────────────────────────────┐
│      PYTHON AI SERVICE       │ │     POSTGRESQL DATABASE     │
│   FastAPI + Pydantic Engine  │ │  • Beneficiary Profiles     │
│ • Structured Profile Extractor│ │  • NQR Qualifications       │
│ • BHASHINI Voice STT/TTS Proxy│ │  • Training Centres         │
│ • Configurable Recommendation │ │  • Verified NCS Jobs        │
└──────────────────────────────┘ └─────────────────────────────┘
```

## Key Architectural Principles
1. **No LLM Hallucinations for Facts**: Government qualification titles, NSQF levels, training centre locations, and job opportunities are queried directly from verified datasets.
2. **Modular Monolith**: Simple, single-command deployment without microservices or complex event buses.
3. **Accessibility First**: WCAG AAA high contrast, Devanagari open font stack, 72px+ touch target voice recorder.
4. **Source Transparency**: Retains `source_name`, `source_url`, and `last_verified_at` metadata on all qualification records.
