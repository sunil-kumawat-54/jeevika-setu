import { Router } from 'express';
import multer from 'multer';
import { createBeneficiary, getBeneficiary, updateBeneficiary, listBeneficiaries } from '../controllers/beneficiary.controller';
import { transcribeAudio, synthesizeSpeech } from '../controllers/voice.controller';
import { getQualifications, getQualificationById } from '../controllers/qualifications.controller';
import { getTrainingCentres, getNearbyTrainingCentres } from '../controllers/training.controller';
import { getJobs, getEnterprisePathways } from '../controllers/job.controller';
import { generateRecommendation, getRecommendationByBeneficiary } from '../controllers/recommendation.controller';
import { getRoadmap } from '../controllers/roadmap.controller';
import { updateOutcome, getOutcomeByBeneficiary } from '../controllers/outcome.controller';
import { getDashboardAnalytics, getDataSourcesStatus } from '../controllers/admin.controller';

const upload = multer({ limits: { fileSize: 10 * 1024 * 1024 } });
const router = Router();

// Auth / Health
router.post('/auth/login', (req, res) => {
  const { username, password } = req.body;
  if (username === 'official' && password === 'pmajay2026') {
    return res.json({ token: 'mock-jwt-token-official', role: 'official', name: 'District Development Officer' });
  }
  res.json({ token: 'mock-jwt-token-admin', role: 'admin', name: 'PM-AJAY Administrator' });
});

// Beneficiary routes
router.post('/beneficiaries', createBeneficiary);
router.get('/beneficiaries', listBeneficiaries);
router.get('/beneficiaries/:id', getBeneficiary);
router.patch('/beneficiaries/:id', updateBeneficiary);

// Voice routes
router.post('/voice/transcribe', upload.single('audio'), transcribeAudio);
router.post('/voice/synthesize', synthesizeSpeech);

// Qualifications routes (NQR / NSQF)
router.get('/qualifications', getQualifications);
router.get('/qualifications/:id', getQualificationById);

// Training Centres
router.get('/training-centres', getTrainingCentres);
router.get('/training-centres/nearby', getNearbyTrainingCentres);

// Jobs & Enterprise
router.get('/jobs', getJobs);
router.get('/enterprise-pathways', getEnterprisePathways);

// Recommendations & Roadmap
router.post('/recommendations/generate', generateRecommendation);
router.get('/recommendations/:beneficiaryId', getRecommendationByBeneficiary);
router.get('/roadmap/:beneficiaryId', getRoadmap);

// Outcome tracking
router.patch('/outcomes/:id', updateOutcome);
router.get('/outcomes/:beneficiaryId', getOutcomeByBeneficiary);

// Admin Dashboard & Data Sources
router.get('/admin/dashboard', getDashboardAnalytics);
router.get('/admin/sources', getDataSourcesStatus);

export default router;
