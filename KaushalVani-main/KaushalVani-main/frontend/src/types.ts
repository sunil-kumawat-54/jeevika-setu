export interface Beneficiary {
  id: string;
  name: string;
  age: number;
  gender: string;
  location: string;
  district: string;
  state: string;
  pincode: string;
  language: string;
  education: string;
  current_occupation: string;
  previous_occupation?: string;
  family_occupation?: string;
  existing_skills: string[];
  experience_years: number;
  desired_occupation: string;
  interests: string[];
  employment_preference: 'wage' | 'self_employment' | 'either';
  mobility_km: number;
  physical_constraints?: string;
  digital_literacy: 'basic' | 'intermediate' | 'advanced' | 'none';
  income_category?: string;
  status: 'draft' | 'profiled' | 'analyzed' | 'enrolled' | 'placed' | 'self_employed';
  created_at: string;
}

export interface Qualification {
  id: string;
  qp_code: string;
  job_role: string;
  sector: string;
  nsqf_level: number;
  eligibility: string;
  education_req: string;
  experience_req: string;
  duration_hours: number;
  skills: string[];
  nos_modules: string[];
  progression: string;
  awarding_body: string;
  source_url: string;
  source_name: string;
  last_verified_at: string;
}

export interface TrainingCentre {
  id: string;
  provider_name: string;
  centre_name: string;
  district: string;
  state: string;
  address: string;
  lat: number;
  lng: number;
  contact_phone: string;
  contact_email: string;
  courses: string[];
  source_url: string;
  distance_km?: number;
}

export interface EmploymentOpportunity {
  id: string;
  title: string;
  employer: string;
  sector: string;
  district: string;
  state: string;
  lat: number;
  lng: number;
  salary_range: string;
  experience_req: string;
  education_req: string;
  vacancies: number;
  job_type: string;
  verified: boolean;
  source_url: string;
}

export interface EnterprisePathway {
  id: string;
  title: string;
  sector: string;
  suitable_for_skills: string[];
  min_education: string;
  equipment_required: string[];
  target_market: string;
  estimated_investment: string;
  potential_revenue: string;
  key_steps: string[];
  guidance_url: string;
}

export interface RecommendationFactor {
  factor: string;
  score: number;
  description: string;
}

export interface Recommendation {
  id: string;
  beneficiary_id: string;
  qualification_id: string;
  score: number;
  match_reasons: string[];
  factors: RecommendationFactor[];
  skill_gap: {
    required_skills: string[];
    existing_skills: string[];
    missing_skills: string[];
    gap_severity: 'Low' | 'Moderate' | 'High';
  };
  nearby_centres: {
    centre: TrainingCentre;
    distance_km: number;
  }[];
  employment_pathways: EmploymentOpportunity[];
  enterprise_pathways: EnterprisePathway[];
  created_at: string;
}

export interface RoadmapStep {
  step_number: number;
  title: string;
  description: string;
  duration?: string;
  details?: string;
}

export interface Roadmap {
  id: string;
  beneficiary_id: string;
  recommendation_id: string;
  qualification_id: string;
  pathway_type: 'wage' | 'self_employment' | 'combined';
  title: string;
  steps: RoadmapStep[];
  explanation: string;
  created_at: string;
}

export interface Outcome {
  id: string;
  beneficiary_id: string;
  training_status: 'Not Started' | 'Enrolled' | 'In Progress' | 'Completed' | 'Dropped Out';
  completion_date?: string;
  certification_status: 'Pending' | 'Certified' | 'Not Certified';
  employment_status: 'Unemployed' | 'Wage Employed' | 'Self Employed' | 'Apprentice';
  enterprise_status: 'None' | 'Planning' | 'Operational';
  placement_date?: string;
  income_band?: string;
  feedback?: string;
  last_updated: string;
}
