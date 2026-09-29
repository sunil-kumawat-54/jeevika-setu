# KaushalVani Production Deployment Guide

## Quick Start (Docker Compose)
```bash
docker compose up --build
```
Access the services:
- **Frontend Portal**: http://localhost:3000
- **Backend API**: http://localhost:5000/health
- **Python AI Engine**: http://localhost:8000/health

## Local Developer Start (Without Docker)
1. **Backend**:
   ```bash
   cd backend
   npm install
   npm run dev
   ```
2. **AI Service**:
   ```bash
   cd ai-service
   pip install -r requirements.txt
   python main.py
   ```
3. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
