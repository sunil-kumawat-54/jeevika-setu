# KaushalVani (कौशलवाणी)
> **"Your Voice. Your Skills. Your Livelihood Path."**

AI-Powered Multilingual Voice-First Livelihood Decision-Support System for PM-AJAY Grant-in-Aid (GIA) Beneficiaries.

---

## 🌟 Core Value Proposition

KaushalVani is **not an AI chatbot**. It is a deployable, practical decision-support system designed specifically for beneficiaries under PM-AJAY's Grant-in-Aid (GIA) component.

It moves a regional beneficiary seamlessly through:
`ASPIRATION` → `BENEFICIARY PROFILE` → `SKILL GAP` → `NSQF-ALIGNED QUALIFICATION` → `TRAINING OPPORTUNITY` → `LOCAL EMPLOYMENT / ENTERPRISE OPPORTUNITY` → `PERSONALIZED LIVELIHOOD ROADMAP` → `OUTCOME TRACKING`.

---

## 🚀 Key Differentiators & Principles

1. **Voice-First Interaction**: Accessible to low-literacy users with >=72px touch target hold-to-speak button, audio replay, and BHASHINI Multilingual ASR/TTS. Supports Marathi, Hindi, and English out of the box.
2. **Zero Government Data Hallucination**: Qualifications, NSQF levels, duration, and job listings are queried strictly from authoritative sources (NQR, Skill India Digital, NCS, PM-AJAY).
3. **Credible Government UI**: Built using UX4G & GIGW accessibility standards with light theme, high contrast controls, and scalable typography.
4. **Transparent Explainability**: Every recommendation includes a multi-factor score breakdown and explicit "WHY THIS IS RECOMMENDED" justifications.
5. **Personalized Livelihood Roadmap**: Visually projects the beneficiary's step-by-step pathway from current profile -> training -> certification -> wage placement -> enterprise option.
6. **Government Administrator Dashboard**: Enables District Development Officers to track cohort funnels, sector demand, and outcome statuses.

---

## 🏗 System Architecture

KaushalVani uses a **Modular Monolith Architecture**:
- **/frontend**: React.js + Vite + TypeScript (UX4G Government Light Theme, High Contrast Accessibility Toolbar).
- **/backend**: Node.js + Express + TypeScript (API Gateway, Unified Data Store, Distance Calculation, Auth).
- **/ai-service**: Python + FastAPI (Interview Extraction Engine, Skill Gap Matcher, Bhashini Proxy).
- **/database**: PostgreSQL schema and initial seeds.
- **/scripts**: Data ingestion and synthetic demo cohort generator scripts.

---

## 🛠 Quick Execution Guide

### Option 1: Docker Compose (Single Command)
```bash
docker compose up --build
```
Access the application at:
- **Frontend Portal**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:5000/health](http://localhost:5000/health)
- **Python AI Engine**: [http://localhost:8000/health](http://localhost:8000/health)

### Option 2: Local Developer Run (Without Docker)

1. **Backend Service**:
   ```bash
   cd backend
   npm install
   npm run dev
   ```

2. **Python AI Service**:
   ```bash
   cd ai-service
   pip install -r requirements.txt
   python main.py
   ```

3. **Frontend React App**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 👤 Primary Demo Persona: Sita

For hackathon evaluation, click **"Primary Demonstration (Demo Persona: Sita)"** on the landing page or start a fresh voice assessment:
- **Name**: Sita (24 years old)
- **Location**: Chhatrapati Sambhajinagar (Aurangabad Rural)
- **Education**: 10th Class Pass
- **Current Occupation**: Agricultural Laborer
- **Aspiration**: Solar Energy & Electrical Installation
- **Mobility Radius**: 15 km
- **Target Qualification**: Solar PV System Installer (ELE/Q5901) - NSQF Level 4
- **Matched Training Centre**: PMKVK Government ITI Aurangabad (8.4 km away)
- **Verified Placement**: Junior Solar Installation Technician (SunPower Marathwada, ₹14,000–₹18,000/mo)

---

## 📜 Documentation Index
- [Architecture Specification](./docs/ARCHITECTURE.md)
- [REST API Reference](./docs/API.md)
- [Government Data Sources](./docs/DATA_SOURCES.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)

---
*Built for Smart India Hackathon / PM-AJAY AI Livelihood Grant-in-Aid Component.*
