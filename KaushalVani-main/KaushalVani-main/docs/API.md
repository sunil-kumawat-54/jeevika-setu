# KaushalVani REST API Documentation

## Endpoints Summary

### Beneficiary & Interview
- `POST /api/beneficiaries`: Create structured beneficiary profile.
- `GET /api/beneficiaries/:id`: Fetch beneficiary profile.
- `POST /api/voice/transcribe`: Speech-to-text proxy forwarding to BHASHINI ASR.
- `POST /api/voice/synthesize`: Text-to-speech audio synthesis.

### Intelligence & Recommendation
- `POST /api/recommendations/generate`: Computes multi-factor score and explainability factors.
- `GET /api/roadmap/:beneficiaryId`: Generates 7-step personalized livelihood roadmap.

### Government Data Registries
- `GET /api/qualifications`: Search NQR NSQF qualifications.
- `GET /api/training-centres/nearby`: Geospatial distance radius search for accredited training centres.
- `GET /api/jobs`: Query National Career Service verified job listings.
- `GET /api/enterprise-pathways`: Micro-business setup guidelines under PM-AJAY GIA scheme.

### Admin Dashboard & Outcomes
- `GET /api/admin/dashboard`: Metrics funnel, sector demand, and outcome summary.
- `GET /api/admin/sources`: Data quality and integration status monitor.
- `PATCH /api/outcomes/:id`: Update beneficiary training and placement status.
