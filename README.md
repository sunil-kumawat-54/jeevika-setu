# Jeevikasetu (जीविकासेतु) — Bridging Skills to Brighter Futures

> **Smart India Hackathon 2026** · Problem Statement ID 97 (Software)  
> **Ministry of Social Justice and Empowerment (MoSJE)** — PM-AJAY (Pradhan Mantri Anusuchit Jaati Abhyuday Yojana)  
> **Tagline:** From Voice → Skills → Better Livelihood Opportunities

---

## 📋 Table of Contents

1. [Project Title & Description](#-project-title--description)
2. [Technical Approach](#-technical-approach)
   - [Architectural Paradigm](#architectural-paradigm)
   - [Technology Stack](#technology-stack)
   - [Core Systems & Safeguards](#core-systems--safeguards)
3. [Project Workflow](#-project-workflow)
   - [End-to-End Execution Flow](#end-to-end-execution-flow)
   - [Data Flow Diagram](#data-flow-diagram)
   - [Detailed Processing Stages](#detailed-processing-stages)
4. [Installation & Setup](#-installation--setup)
   - [Prerequisites](#prerequisites)
   - [Environment Configuration](#environment-configuration)
   - [Quickstart with Docker Compose](#quickstart-with-docker-compose)
   - [Manual / Local Development Setup](#manual--local-development-setup)
   - [Seeding & Ingestion](#seeding--ingestion)
5. [Usage](#-usage)
   - [Beneficiary Voice Journey](#1-beneficiary-voice-journey)
   - [Officer & Organization Portal](#2-officer--organization-portal)
   - [API Usage & Code Snippets](#3-api-usage--code-snippets)
   - [Operational Make Commands](#4-operational-make-commands)
6. [Project Structure](#-project-structure)
7. [Contributing](#-contributing)
8. [License](#-license)

---

## 🎯 Project Title & Description

**Jeevikasetu (जीविकाseतु)** is an AI-driven, voice-first, multilingual livelihood mapping and skilling recommendation platform specifically engineered for scheduled caste (SC) communities under the Grant-in-Aid (GIA) component of PM-AJAY.

### The Challenge
Beneficiaries in rural and semi-urban regions frequently face critical barriers:
- **Literacy & Technical Friction:** Traditional job portals and government forms require complex text inputs, English proficiency, and navigation through non-intuitive UI forms.
- **Informal Skill Recognition:** Informal skills (e.g., motor repair, solar component installation, tailoring, agricultural equipment maintenance) are rarely mapped to formal qualifications.
- **Information Asymmetry:** Lack of visibility into nearby training centres, Recognition of Prior Learning (RPL) pathways, and verified job opportunities within a realistic mobility radius.
- **Connectivity & System Reliability:** Remote areas often suffer from spotty network coverage and third-party API instability.

### The Solution
Jeevikasetu bridges these gaps through a voice-first conversational AI interface:
- **Voice-First Interaction:** Beneficiaries speak naturally in their local language (Hindi, English, Marathi, Telugu, etc.). The system auto-detects dialect/language, requests spoken consent, and captures background, skills, and aspirations.
- **Deterministic NSQF Mapping:** Converts informal descriptions into structured profiles and performs semantic matching against National Skills Qualifications Framework (NSQF) Qualification Packs (QPs).
- **Explainable & Grounded Pathways:** Recommends personalized training or RPL pathways, pinpoints nearby PostGIS-verified training centres, and surfaces local job demand—accompanied by clear, human-readable "why this was recommended" explanations.
- **Guaranteed Reliability & Privacy:** Incorporates a 100% offline mock mode for zero-connectivity/zero-API-key fallback, strict server-side grounding verifiers to eliminate AI hallucinations, and privacy-by-design data protection.
- **Outcome Tracking & Officer Analytics:** Tracks beneficiary progression from enrolment to certification and employment while equipping district officers with spatial skill-gap heatmaps and decision-support analytics.

---

## 🔬 Technical Approach

Jeevikasetu is designed around an **Offline-First, Grounded, Micro-Service & Modular Monorepo Architecture**.

```
+-----------------------------------------------------------------------------------+
|                                  USER INTERFACE                                   |
|   +------------------------------------+    +---------------------------------+   |
|   |  Beneficiary PWA / App (Voice UI)  |    |  Officer & Org Portal (Next.js) |   |
|   +------------------------------------+    +---------------------------------+   |
+------------------------------------------+----------------------------------------+
                                           | HTTPS / WebSockets / JSON
+------------------------------------------v----------------------------------------+
|                            BACKEND CORE (FastAPI Service)                         |
|  +-------------------+  +-------------------+  +--------------------------------+ |
|  | Speech Router     |  | Session FSM       |  | Recommendation & Gap Engine    | |
|  | (Bhashini/Whisper)|  | (Slot Extraction) |  | (Multi-Factor Scoring)         | |
|  +-------------------+  +-------------------+  +--------------------------------+ |
|  +-------------------+  +-------------------+  +--------------------------------+ |
|  | Grounding Check   |  | RAG / Vector Engine| | Outcome & Audit Logger         | |
|  | (Fact Guardrail)  |  | (pgvector / BM25) |  | (Synthetic Tracking)           | |
|  +-------------------+  +-------------------+  +--------------------------------+ |
+------------------------------------------+----------------------------------------+
                                           | SQL / Spatial / Vector
+------------------------------------------v----------------------------------------+
|                                DATA & STORAGE LAYER                               |
|   +---------------------------------------------------------------------------+   |
|   | PostgreSQL 16 + PostGIS (Spatial Geometry) + pgvector (Semantic Index)    |   |
|   +---------------------------------------------------------------------------+   |
|   | Redis (Session Cache, Rate Limiting, Audio Phrase Caching)                |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

### Architectural Paradigm

#### 1. "Deterministic Core, Generative Shell"
A major failure mode in government AI projects is LLM hallucination (inventing nonexistent training courses, false stipend amounts, or invalid contact numbers). Jeevikasetu enforces a strict separation:
- **Deterministic Core:** Database queries, vector search, PostGIS distance calculations, eligibility filters, and scoring logic determine **all hard facts**.
- **Generative Shell:** The LLM is restricted to verbalizing structured JSON tool outputs into empathetic, natural local language.
- **Post-Hoc Grounding Verifier:** A server-side guardrail parses generated responses. Every numeric value, qualification code, course title, or location in the spoken output **must** exist in the underlying tool output. If a discrepancy is detected, the system automatically falls back to a deterministic, pre-approved template.

#### 2. Provider Abstraction with Mock-First Capability
Every external service dependency (Speech-to-Text, Text-to-Speech, LLM, Embeddings) is implemented behind an abstracted interface:
- **Voice Adapters:** Primary: Bhashini ULCA API; Fallbacks: Sarvam AI, OpenAI Whisper, Azure Speech, and a **Mock Speech Provider**.
- **LLM Adapters:** LangChain-backed adapters for OpenAI GPT-4o, Anthropic Claude, Ollama (local Llama 3), and a **Mock Rule-Based Verbalizer**.
- **Mock Mode:** Setting `VOICE_PROVIDER=mock` and `LLM_PROVIDER=mock` allows the entire end-to-end journey to run offline with zero external API keys and zero internet access.

### Technology Stack

| Layer | Technology | Rationale / Why Chosen |
|---|---|---|
| **Core API** | Python 3.11 + FastAPI | Async I/O for streaming audio/WebSockets, native Python ML/NLP integration, high throughput, and automatic OpenAPI schema generation. |
| **Database** | PostgreSQL 16 | Enterprise-grade relational stability with ACID compliance for sensitive beneficiary profiles and audit logs. |
| **Spatial Engine** | PostGIS Extension | Enables precise geospatial queries (e.g., `ST_DWithin`, `ST_Distance`) to match beneficiaries with training centres within a dynamic mobility radius (e.g., 15 km). |
| **Vector Engine** | pgvector Extension | Direct vector search inside PostgreSQL. Eliminates the operational overhead of running a separate vector database while ensuring transactional consistency between embeddings and relational data. |
| **Caching Layer** | Redis 7 | High-performance session state management, rate limiting, and TTS audio phrase caching to reduce audio latency. |
| **Frontend Portal** | Next.js 14 (React, TypeScript) | Server-Side Rendering (SSR) for fast loading, progressive web app (PWA) capabilities, responsive layout, and seamless role-based routing. |
| **Maps & Data Vis** | Leaflet.js + Recharts | Lightweight spatial rendering for officer heatmaps and responsive charting without heavy commercial API keys. |
| **AI / Embeddings** | LangChain + `multilingual-e5-small` | High-quality multilingual semantic embeddings for cross-lingual matching (e.g., mapping Hindi informal spoken skill descriptions to English NSQF standards). |
| **DevOps / Containers** | Docker Compose + Make | Standardized environment isolation across development, offline hackathon demonstrations, and production deployments. |

### Core Systems & Safeguards

- **Privacy by Design:** Explicit spoken and tap consent is logged before profile creation. Raw audio files are discarded immediately after transcription processing unless debug logging is explicitly enabled.
- **Honest Data Provenance:** Synthetic or seed records carry a persistent `synthetic=true` flag through the database schema, API responses, UI badges, and CSV/XLSX exports.
- **Latency Budgeting:** Enforces a p95 target of <4 seconds per conversational turn, monitored via `make latency` testing.

---

## 🔄 Project Workflow

### End-to-End Execution Flow

```
   [1. Voice / Text Input]
              │
              ▼
   [2. STT & Language Detection] (Bhashini / Whisper / Mock)
              │
              ▼
   [3. Session FSM & Intent Parser] ◄── Slot-filling state machine
              │
              ▼
   [4. Livelihood Profile Construction] (Skills, Education, Location, Aspiration)
              │
              ▼
   [5. Hybrid RAG & NSQF Skill Gap Analysis] (pgvector + BM25 keyword matching)
              │
              ▼
   [6. PostGIS Spatial & Multi-Factor Scoring] (Centres < 15km, RPL vs Training)
              │
              ▼
   [7. Grounding Safeguard & LLM Verbalization] (Strict fact verification)
              │
              ▼
   [8. TTS Synthesis & Audio Output]
              │
              ▼
   [9. Outcome Tracking & Portal Analytics]
```

### Detailed Processing Stages

#### Stage 1: Onboarding & Consent
1. Beneficiary opens the mic-first PWA interface or a Facilitator launches the app on a shared device.
2. The system prompts for language selection (Hindi, Marathi, Telugu, English, etc.) or auto-detects language from the initial utterance.
3. Spoken + tap consent is requested: *"Do you agree to let Jeevikasetu map your skills to PM-AJAY opportunities?"* Consent status is stored with a timestamp.

#### Stage 2: Spoken Profile Extraction (Slot Filling FSM)
1. The beneficiary speaks naturally about their work history, education, interests, and location (e.g., *"Main 10th pass hoon, solar panel install karna seekhna chahta hoon, Jaipur ke paas rehta hoon"*).
2. The core API executes Speech-to-Text (STT).
3. The Finite State Machine (FSM) updates the beneficiary's session state, extracting structured slots:
   - `education_level`: 10th Pass
   - `informal_skills`: ["basic electrical work", "hand tools"]
   - `aspiration`: "solar technician"
   - `location`: Geometry coordinates / District: Jaipur / Mobility Radius: 15 km
4. If mandatory slots are missing or low-confidence, the bot asks targeted follow-up questions.

#### Stage 3: Hybrid NSQF Skill Gap Analysis
1. Informal skill descriptions are converted into dense vector embeddings using `multilingual-e5-small`.
2. A hybrid retrieval engine (combining `pgvector` cosine similarity with BM25 keyword search) queries the **NSQF Knowledge Base**.
3. Matches the beneficiary's profile to candidate Qualification Packs (e.g., *Solar PV Installer - ELE/Q5901*, NSQF Level 4).
4. Calculates the skill gap:
   - **Matched Skills:** Hand tool operation, basic wiring logic.
   - **Missing Skills:** Photovoltaic array sizing, inverter grid connection safety.

#### Stage 4: Spatial Matching & Multi-Factor Recommendation
1. **Spatial Filtering:** PostGIS runs a spatial query (`ST_DWithin`) against verified PM-AJAY training centres within the beneficiary's mobility radius.
2. **Multi-Factor Scoring Engine:** Scores candidates using a weighted formula:
   $$\text{Score} = (W_{\text{skill}} \times S_{\text{skill}}) + (W_{\text{dist}} \times S_{\text{dist}}) + (W_{\text{elig}} \times S_{\text{elig}}) + (W_{\text{demand}} \times S_{\text{demand}})$$
3. **Pathway Determination:** Recommends either:
   - **Full Training Pathway:** For new skills requiring formal instruction.
   - **RPL (Recognition of Prior Learning) Pathway:** For experienced candidates needing certification only.

#### Stage 5: Grounded Response & Audio Playback
1. Recommendation results are formatted into a rigid JSON structure containing verified centre names, distances, course durations, and QP codes.
2. The LLM verbalizes the JSON into a conversational, empathetic response in the beneficiary's local language.
3. The response passes through the **Grounding Verifier**.
4. The verified text is converted to speech via Text-to-Speech (TTS) and played back with on-screen captions.

#### Stage 6: Outcome Tracking & Officer Analytics
1. The beneficiary can tap "Enroll" or request a facilitator follow-up.
2. Status transitions are logged: `Recommended` → `Enrolled` → `In Training` → `Certified` → `Employed`.
3. District officers view aggregated analytics (skill-gap maps, demand vs. supply charts, program completion funnels) on the portal.

---

## ⚙️ Installation & Setup

### Prerequisites

Ensure you have the following installed on your host system:
- **Git** (v2.38+)
- **Docker** (v24.0+) & **Docker Compose** (v2.20+)
- **Python** (v3.11+) *(Required for local non-Docker development)*
- **Node.js** (v18+) & **npm** (v9+) *(Required for local portal development)*
- **Make** (standard build tool)

---

### Environment Configuration

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/jeevikasetu.git
   cd jeevikasetu
   ```

2. Copy the sample environment file:
   ```bash
   cp .env.example .env
   ```

3. Configure variables in `.env`:
   ```ini
   # Service Providers (Set to 'mock' for 100% offline development/demo)
   VOICE_PROVIDER=mock
   LLM_PROVIDER=mock
   EMBEDDING_PROVIDER=mock

   # Real Provider Credentials (Optional for live mode)
   BHASHINI_API_KEY=your_bhashini_key
   BHASHINI_USER_ID=your_user_id
   OPENAI_API_KEY=your_openai_key

   # Database Configuration
   POSTGRES_USER=jeevikasetu
   POSTGRES_PASSWORD=jeevikasetu_secure_pass
   POSTGRES_DB=jeevikasetu_db
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432
   DATABASE_URL=postgresql://jeevikasetu:jeevikasetu_secure_pass@postgres:5432/jeevikasetu_db

   # Redis Configuration
   REDIS_URL=redis://redis:6379/0

   # Application Options
   LOG_LEVEL=INFO
   ENVIRONMENT=development
   ```

---

### Quickstart with Docker Compose

The simplest way to run Jeevikasetu is using the automated Makefile target with Docker:

```bash
# Start all containers (PostgreSQL+PostGIS+pgvector, Redis, Core API, Web Portal)
make up

# Seed database with NSQF Qualification Packs, PM-AJAY centres, and demo persona
make seed
```

Once running, access the services:
- **Beneficiary Voice PWA:** [http://localhost:3000](http://localhost:3000)
- **Officer & Org Portal:** [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- **FastAPI Core OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

To stop the stack:
```bash
make down
```

---

### Manual / Local Development Setup

If you prefer running services directly on your host machine:

#### 1. Database & Infrastructure
Run PostgreSQL and Redis via Docker:
```bash
docker compose up -d postgres redis
```

#### 2. Backend Core API (FastAPI)
```bash
# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r services/core/requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI dev server
uvicorn services.core.main:app --reload --port 8000
```

#### 3. Frontend Web Application (Next.js)
```bash
cd apps/web
npm install
npm run dev
```

---

### Seeding & Ingestion

Jeevikasetu comes with pre-committed seed snapshots containing verified NSQF job roles, PM-AJAY training centre coordinates, and local demand metrics.

To execute the idempotent seed pipelines:
```bash
# Via Make (Docker)
make seed

# Or manually via Python script
python pipelines/01_ingest_nsqf.py
python pipelines/02_ingest_centres.py
python pipelines/03_seed_demo_persona.py
```

---

## 💻 Usage

### 1. Beneficiary Voice Journey

1. Open `http://localhost:3000` on a mobile browser or desktop.
2. Select your language (e.g., **Hindi - हिंदी**).
3. Press and hold the **Microphone Button** (or tap text mode) and say:
   > *"Namaste, mera naam Sita hai. Main 10th pass hoon. Mujhe solar panel ka kaam seekhna hai."*
4. The system will process your voice input, generate a structured profile, execute spatial & skill-gap analysis, and respond both visually and audibly:
   - **Recommended Course:** Solar PV Installer (ELE/Q5901) — NSQF Level 4
   - **Nearest Centre:** PM-AJAY Skilling Hub, Sanganer (11.2 km away)
   - **Pathway:** 300 Hours Classroom Training + RPL Certification Assessment
   - **Reason:** Matches 10th pass qualification, fills gap in electrical safety, high district demand.

---

### 2. Officer & Organization Portal

1. Navigate to `http://localhost:3000/dashboard`.
2. **Officer Analytics:** View district-level skill gap heatmaps powered by Leaflet, supply vs. demand charts, and demographic funnel stats.
3. **Organization Management:** Post new training courses or job vacancies and filter candidate profiles by skill, district, and NSQF eligibility.
4. **Data Export:** Click **Export Data** to download CSV/XLSX summaries containing complete audit trails and `synthetic=true` data tags.

---

### 3. API Usage & Code Snippets

#### Create a Beneficiary Session
```bash
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "preferred_language": "hi",
    "facilitator_id": null
  }'
```

#### Process a Spoken / Text Turn
```bash
curl -X POST "http://localhost:8000/api/v1/sessions/SESS-10928/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Main 10th pass hoon, wiring ka kaam janta hoon aur solar job chahta hoon",
    "location": {
      "latitude": 26.9124,
      "longitude": 75.7873
    }
  }'
```

#### Example Python Client SDK Integration
```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. Create Session
session_resp = requests.post(f"{BASE_URL}/sessions", json={"preferred_language": "hi"})
session_id = session_resp.json()["session_id"]

# 2. Post Conversational Turn
turn_payload = {
    "text": "I fix agricultural pumps and want a certified electrical job nearby",
    "location": {"latitude": 26.9124, "longitude": 75.7873}
}
response = requests.post(f"{BASE_URL}/sessions/{session_id}/turn", json=turn_payload)
result = response.json()

print(f"Assistant Reply: {result['spoken_response']}")
print(f"Grounding Check Passed: {result['grounding_passed']}")
print(f"Recommended Pathway: {result['recommendation']['pathway_name']}")
```

---

### 4. Operational Make Commands

Jeevikasetu provides a robust Makefile for operational workflows:

```bash
make up         # Build and start all services via Docker Compose
make down       # Stop and remove containers
make seed       # Populate database with NSQF QPs, centres, & demo personas
make test       # Run unit and integration test suite via pytest
make grounding  # Execute the 50-session automated grounding verification test
make latency    # Measure audio processing stage latencies (ASR -> RAG -> LLM -> TTS)
make lint       # Run ruff and black code formatters
make logs       # Tail real-time system logs across services
```

---

## 📂 Project Structure

```
jeevikasetu/
├── .planning/                  # GSD Framework specs, requirements, and roadmap
│   ├── PROJECT.md              # Project vision, active scope, and key decisions
│   ├── REQUIREMENTS.md         # Full v1 requirements traceability matrix
│   ├── ROADMAP.md              # Multi-phase execution roadmap & state tracking
│   └── STATE.md                # Real-time state of verification & milestone progress
├── apps/
│   ├── web/                    # Next.js 14 Frontend Application
│   │   ├── app/                # App router (beneficiary voice UI, dashboard, admin)
│   │   ├── components/         # UI components (audio player, mic button, maps)
│   │   └── public/             # Static assets and icons
│   └── mobile/                 # Flutter mobile beneficiary app (Optional target)
├── services/
│   └── core/                   # FastAPI Backend Core Service
│       ├── api/                # API Endpoints (sessions, recommendations, analytics, auth)
│       ├── domain/             # Core business logic (skill gap analysis, scoring rules)
│       ├── llm/                # LLM adapters, prompt templates, & grounding guardrails
│       ├── speech/             # Speech adapters (Bhashini, Sarvam, Whisper, Mock)
│       ├── rag/                # Retrieval engine (pgvector hybrid search, BM25)
│       └── models/             # SQLAlchemy ORM schemas and Pydantic DTO models
├── pipelines/                  # Data Ingestion Pipelines
│   ├── 01_ingest_nsqf.py       # NSQF Qualification Packs ingestion script
│   ├── 02_ingest_centres.py    # PM-AJAY training centre geo-ingestion script
│   └── 03_seed_demo_persona.py # Demo persona (Sita) seeder
├── seeds/                      # Committed Snapshot Datasets
│   ├── nsqf_qualifications.json
│   ├── pmajay_centres.json
│   └── local_demand.json
├── data/                       # Domain Mappings & Curated Prompts
│   └── crosswalk/              # Aspiration-to-NSQF mapping rules
├── infra/                      # Infrastructure Configuration
│   ├── docker-compose.yml      # Orchestration file (PostgreSQL, Redis, Core, Web)
│   └── Dockerfile.core         # Core API container build instructions
├── scripts/                    # Verification & Audit Tools
│   ├── verify_grounding.py     # Automated fact grounding test harness
│   └── measure_latency.py      # Audio pipeline latency profiling tool
├── JEEVIKASETU-GSD-PRD.md      # Product Requirements & Acceptance Document
├── Makefile                    # Operational task runner commands
├── pyproject.toml              # Python project metadata and ruff/pytest config
└── README.md                   # System documentation (This file)
```

---

## 🤝 Contributing

We welcome contributions to Jeevikasetu from developers, data scientists, domain experts, and accessibility advocates.

### Guidelines

1. **Fork & Branching:**
   - Create a feature branch off `main`: `git checkout -b feature/your-feature-name`.
2. **Coding Standards:**
   - **Python:** Follow PEP 8 guidelines. Format with `black` and lint with `ruff`.
   - **TypeScript/React:** Adhere to standard Next.js best practices and ESLint rules.
3. **Grounding & Safeguard Rule:**
   - Any modification to recommendation logic **must** pass the automated grounding suite (`make grounding`).
4. **Testing:**
   - Ensure all unit and integration tests pass before submitting a pull request (`make test`).
5. **Pull Request Process:**
   - Provide a clear PR description outlining the changes, rationale, and issue references.
   - Maintain synthetic data tags (`synthetic=true`) on any added mock fixtures.

---

## 📜 License

This project is open-source and released under the **[Apache License 2.0](LICENSE)**.

```
Copyright (c) 2026 Jeevikasetu Team / MoSJE PM-AJAY SIH 2026

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

<p align="center">
  <b>Bridging Skills to Brighter Futures · Jeevikasetu (जीविकासेतु)</b>
</p>
