import React, { createContext, useContext, useState } from 'react';
import { Beneficiary, Recommendation, Roadmap } from '../types';

interface BeneficiaryContextType {
  beneficiary: Beneficiary | null;
  setBeneficiary: React.Dispatch<React.SetStateAction<Beneficiary | null>>;
  recommendation: Recommendation | null;
  setRecommendation: React.Dispatch<React.SetStateAction<Recommendation | null>>;
  roadmap: Roadmap | null;
  setRoadmap: React.Dispatch<React.SetStateAction<Roadmap | null>>;
  interviewStep: number;
  setInterviewStep: (step: number) => void;
  resetSession: () => void;
  loadDemoPersona: () => void;
}

const defaultSitaBeneficiary: Beneficiary = {
  id: 'ben-sita-001',
  name: 'Sita',
  age: 24,
  gender: 'Female',
  location: 'Chhatrapati Sambhajinagar (Aurangabad Rural)',
  district: 'Aurangabad',
  state: 'Maharashtra',
  pincode: '431006',
  language: 'Marathi',
  education: '10th Class Pass',
  current_occupation: 'Agricultural Laborer',
  previous_occupation: 'Seasonal farm hand',
  family_occupation: 'Smallholder Agriculture',
  existing_skills: ['Basic Farming', 'Pumphouse Operations', 'Hand Tools Handling'],
  experience_years: 3,
  desired_occupation: 'Electrical & Solar Work',
  interests: ['Solar Energy', 'Electrical Wiring', 'Appliance Repair'],
  employment_preference: 'wage',
  mobility_km: 15,
  physical_constraints: 'None',
  digital_literacy: 'basic',
  status: 'analyzed',
  created_at: new Date().toISOString()
};

const BeneficiaryContext = createContext<BeneficiaryContextType | undefined>(undefined);

export const BeneficiaryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [beneficiary, setBeneficiary] = useState<Beneficiary | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [interviewStep, setInterviewStep] = useState<number>(1);

  const resetSession = () => {
    setBeneficiary(null);
    setRecommendation(null);
    setRoadmap(null);
    setInterviewStep(1);
  };

  const loadDemoPersona = () => {
    setBeneficiary(defaultSitaBeneficiary);
    setInterviewStep(7);
  };

  return (
    <BeneficiaryContext.Provider value={{
      beneficiary,
      setBeneficiary,
      recommendation,
      setRecommendation,
      roadmap,
      setRoadmap,
      interviewStep,
      setInterviewStep,
      resetSession,
      loadDemoPersona
    }}>
      {children}
    </BeneficiaryContext.Provider>
  );
};

export const useBeneficiary = () => {
  const context = useContext(BeneficiaryContext);
  if (!context) throw new Error('useBeneficiary must be used within BeneficiaryProvider');
  return context;
};
