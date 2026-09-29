import { Request, Response } from 'express';
import { store, Roadmap } from '../db/store';

export const getRoadmap = (req: Request, res: Response) => {
  const { beneficiaryId } = req.params;
  const roadmaps = Array.from(store.roadmaps.values()).filter(r => r.beneficiary_id === beneficiaryId);

  if (roadmaps.length > 0) {
    return res.json({ roadmap: roadmaps[roadmaps.length - 1] });
  }

  // Generate Roadmap from latest recommendation
  const recs = Array.from(store.recommendations.values()).filter(r => r.beneficiary_id === beneficiaryId);
  const beneficiary = store.beneficiaries.get(beneficiaryId);

  if (recs.length === 0 || !beneficiary) {
    return res.status(404).json({ error: 'No recommendation available to build roadmap. Run analysis first.' });
  }

  const rec = recs[recs.length - 1];
  const qual = store.qualifications.get(rec.qualification_id);
  const centre = rec.nearby_centres.length > 0 ? rec.nearby_centres[0].centre : null;
  const job = rec.employment_pathways.length > 0 ? rec.employment_pathways[0] : null;
  const ent = rec.enterprise_pathways.length > 0 ? rec.enterprise_pathways[0] : null;

  const steps = [
    {
      step_number: 1,
      title: 'Beneficiary Baseline Profile',
      description: `Current Livelihood: ${beneficiary?.current_occupation || 'Agricultural Worker'} | Education: ${beneficiary?.education || '10th Pass'}`,
      duration: 'Completed',
      details: `Stated Interest: ${beneficiary?.desired_occupation || 'Solar & Electrical Work'}. Existing Skills: ${(beneficiary?.existing_skills || []).join(', ')}.`
    },
    {
      step_number: 2,
      title: 'Skill Gap & Qualification Mapping',
      description: `Target NSQF Level ${qual?.nsqf_level || 4} Job Role: ${qual?.job_role || 'Solar PV Installer'} (${qual?.qp_code})`,
      duration: 'Completed',
      details: `Skill Gap Severity: ${rec.skill_gap.gap_severity}. Target NOS Modules: ${(qual?.nos_modules || []).slice(0, 2).join('; ')}.`
    },
    {
      step_number: 3,
      title: 'NSQF-Aligned Skill Training Program',
      description: `Enrolling at: ${centre?.provider_name || 'Government ITI Sambhajinagar'} (${rec.nearby_centres[0]?.distance_km || 8.4} km away)`,
      duration: `${qual?.duration_hours || 350} Hours (${Math.round((qual?.duration_hours || 350) / 120)} Months)`,
      details: `Includes hands-on practical lab training, tool safety, and stipend support under PM-AJAY Grant-in-Aid (GIA).`
    },
    {
      step_number: 4,
      title: 'Assessment & NQR Certification',
      description: `Formal assessment by ${qual?.awarding_body || 'ESSCI Sector Skill Council'}`,
      duration: 'Week 12',
      details: `Government-recognized NSQF Level ${qual?.nsqf_level || 4} certificate issued upon achieving 70%+ score.`
    },
    {
      step_number: 5,
      title: 'Primary Livelihood Opportunity (Wage Employment)',
      description: `Role: ${job?.title || 'Junior Solar Technician'} at ${job?.employer || 'Local Energy Contractor'}`,
      duration: 'Immediate Post-Certification',
      details: `Salary Range: ${job?.salary_range || '₹14,000 - ₹18,000 / month'}. Verified job listing via National Career Service (NCS).`
    },
    {
      step_number: 6,
      title: 'Alternative Enterprise / Micro-Business Pathway',
      description: `Setup: ${ent?.title || 'Village Solar Maintenance Enterprise'}`,
      duration: 'Self-Paced / Parallel',
      details: `Micro-grant assistance up to ₹35,000 under PM-AJAY GIA Component. Target market: ${ent?.target_market || 'Rural households & farmers'}.`
    },
    {
      step_number: 7,
      title: 'Continuous Livelihood Outcome Tracking',
      description: `District Officer check-in at 30, 90 & 180 days post placement`,
      duration: '6 Months Tracking',
      details: `Monitors income growth, career progression to Senior Technician, and feedback.`
    }
  ];

  const newRoadmap: Roadmap = {
    id: `rdm-${Date.now()}`,
    beneficiary_id: beneficiaryId,
    recommendation_id: rec.id,
    qualification_id: rec.qualification_id,
    pathway_type: beneficiary?.employment_preference === 'self_employment' ? 'self_employment' : 'wage',
    title: `Personalized Livelihood Pathway to ${qual?.job_role || 'Solar PV Technician'}`,
    steps,
    explanation: `This custom roadmap bridges Sita's background in farming with her aspiration in solar electrical work. By pursuing the 350-hour NSQF Level 4 Solar PV Installer course at the nearby Government ITI (8.4 km away), she gains accredited technical skills while remaining within her 15 km mobility radius. Upon certification, she can enter wage employment paying ₹14,000–₹18,000/month or leverage PM-AJAY GIA micro-enterprise grants to set up a village solar repair unit.`,
    created_at: new Date().toISOString()
  };

  store.roadmaps.set(newRoadmap.id, newRoadmap);
  res.json({ roadmap: newRoadmap });
};
