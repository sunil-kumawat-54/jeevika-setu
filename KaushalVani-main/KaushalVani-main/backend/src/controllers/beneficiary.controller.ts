import { Request, Response } from 'express';
import { store, Beneficiary } from '../db/store';

export const createBeneficiary = (req: Request, res: Response) => {
  const {
    name, age, gender, location, district, state, pincode, language,
    education, current_occupation, previous_occupation, family_occupation,
    existing_skills, experience_years, desired_occupation, interests,
    employment_preference, mobility_km, physical_constraints, digital_literacy
  } = req.body;

  const id = `ben-${Date.now()}`;
  const newBeneficiary: Beneficiary = {
    id,
    name: name || 'Beneficiary User',
    age: Number(age) || 24,
    gender: gender || 'Female',
    location: location || 'Chhatrapati Sambhajinagar',
    district: district || 'Aurangabad',
    state: state || 'Maharashtra',
    pincode: pincode || '431006',
    language: language || 'Marathi',
    education: education || '10th Class Pass',
    current_occupation: current_occupation || 'Agricultural Laborer',
    previous_occupation: previous_occupation || 'Seasonal farm hand',
    family_occupation: family_occupation || 'Farming',
    existing_skills: Array.isArray(existing_skills) ? existing_skills : ['Basic farming'],
    experience_years: Number(experience_years) || 2,
    desired_occupation: desired_occupation || 'Electrical / Solar Work',
    interests: Array.isArray(interests) ? interests : ['Solar Energy', 'Electrical Wiring'],
    employment_preference: employment_preference || 'wage',
    mobility_km: Number(mobility_km) || 15,
    physical_constraints: physical_constraints || 'None',
    digital_literacy: digital_literacy || 'basic',
    status: 'profiled',
    created_at: new Date().toISOString()
  };

  store.beneficiaries.set(id, newBeneficiary);

  // Initialize outcome record
  store.outcomes.set(id, {
    id: `out-${Date.now()}`,
    beneficiary_id: id,
    training_status: 'Not Started',
    certification_status: 'Pending',
    employment_status: 'Unemployed',
    enterprise_status: 'None',
    last_updated: new Date().toISOString()
  });

  return res.status(201).json({ success: true, beneficiary: newBeneficiary });
};

export const getBeneficiary = (req: Request, res: Response) => {
  const { id } = req.params;
  const beneficiary = store.beneficiaries.get(id);

  if (!beneficiary) {
    return res.status(404).json({ error: 'Beneficiary profile not found' });
  }

  res.json({ beneficiary });
};

export const updateBeneficiary = (req: Request, res: Response) => {
  const { id } = req.params;
  const beneficiary = store.beneficiaries.get(id);

  if (!beneficiary) {
    return res.status(404).json({ error: 'Beneficiary not found' });
  }

  const updated: Beneficiary = {
    ...beneficiary,
    ...req.body
  };

  store.beneficiaries.set(id, updated);
  res.json({ success: true, beneficiary: updated });
};

export const listBeneficiaries = (req: Request, res: Response) => {
  const list = Array.from(store.beneficiaries.values());
  res.json({ beneficiaries: list.slice(0, 50), total: list.length });
};
