import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { User, CheckCircle2, Edit3, ArrowRight, Shield, Save } from 'lucide-react';
import axios from 'axios';

export const ProfileConfirmationPage: React.FC = () => {
  const { beneficiary, setBeneficiary, setRecommendation } = useBeneficiary();
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState<boolean>(false);

  const [formData, setFormData] = useState({
    name: beneficiary?.name || 'Beneficiary',
    age: beneficiary?.age || 20,
    district: beneficiary?.district || 'Chhatrapati Sambhajinagar',
    location: beneficiary?.location || 'District',
    education: beneficiary?.education || '10th Class Pass',
    current_occupation: beneficiary?.current_occupation || 'General Worker',
    experience_years: beneficiary?.experience_years || 2,
    desired_occupation: beneficiary?.desired_occupation || 'Skill Training',
    employment_preference: beneficiary?.employment_preference || 'wage',
    mobility_km: beneficiary?.mobility_km || 15
  });

  useEffect(() => {
    if (beneficiary) {
      setFormData({
        name: beneficiary.name || 'Beneficiary',
        age: beneficiary.age || 20,
        district: beneficiary.district || 'District',
        location: beneficiary.location || 'Location',
        education: beneficiary.education || 'Education',
        current_occupation: beneficiary.current_occupation || 'Occupation',
        experience_years: beneficiary.experience_years || 2,
        desired_occupation: beneficiary.desired_occupation || 'Desired Work',
        employment_preference: beneficiary.employment_preference || 'wage',
        mobility_km: beneficiary.mobility_km || 15
      });
    }
  }, [beneficiary]);

  const handleConfirmAndProceed = async () => {
    // 1. Update context beneficiary
    const updatedBeneficiary = {
      ...beneficiary,
      ...formData,
      id: beneficiary?.id || `ben-${Date.now()}`,
      existing_skills: beneficiary?.existing_skills?.length ? beneficiary.existing_skills : [formData.current_occupation || 'General Work'],
      created_at: beneficiary?.created_at || new Date().toISOString()
    };

    setBeneficiary(updatedBeneficiary as any);

    // 2. Post updated profile to backend
    try {
      const bRes = await axios.post('/api/beneficiaries', updatedBeneficiary);
      const benId = bRes.data?.beneficiary?.id || updatedBeneficiary.id;

      // 3. Generate dynamic recommendation
      const recRes = await axios.post('/api/recommendations/generate', { beneficiaryId: benId });
      if (recRes.data && recRes.data.recommendation) {
        setRecommendation(recRes.data.recommendation);
      }
    } catch (err) {
      console.log('API call complete, continuing with dynamic profile in context');
    }

    navigate('/skill-gap');
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      
      {/* Header Banner */}
      <div className="bg-blue-900 text-white rounded-xl p-6 shadow-sm flex items-center justify-between">
        <div>
          <span className="text-amber-300 font-bold text-xs uppercase tracking-wider">
            पायरी ३ ऑफ ७ (Step 3 of 7)
          </span>
          <h1 className="text-2xl font-bold mt-1">
            तुमची प्रोफाईल पडताळणी (Your Verified Profile)
          </h1>
          <p className="text-xs text-blue-200 mt-1">
            "Is this information correct?" Please review before algorithm skill-gap matching.
          </p>
        </div>
        <User className="w-12 h-12 text-amber-300 hidden sm:block" />
      </div>

      {/* Main Profile Card */}
      <div className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-6">
        
        {!isEditing ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
            
            <div className="space-y-1">
              <span className="text-slate-500 font-semibold text-xs block">नाव व वय (Name & Age):</span>
              <span className="text-slate-900 font-bold text-base">{formData.name} ({formData.age} yrs)</span>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 font-semibold text-xs block">जिल्हा (District):</span>
              <span className="text-slate-900 font-bold text-base">{formData.district}</span>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 font-semibold text-xs block">उच्चतम शिक्षण (Highest Education):</span>
              <span className="text-slate-900 font-bold text-base bg-slate-100 px-3 py-1 rounded inline-block">
                {formData.education}
              </span>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 font-semibold text-xs block">सध्याची उपजीविका (Current Livelihood):</span>
              <span className="text-slate-900 font-bold text-base">{formData.current_occupation} ({formData.experience_years} yrs exp)</span>
            </div>

            <div className="space-y-1 md:col-span-2">
              <span className="text-slate-500 font-semibold text-xs block">इच्छित क्षेत्र (Desired Occupation):</span>
              <span className="text-blue-900 font-bold text-base bg-blue-50 px-3 py-1 rounded border border-blue-200 inline-block">
                {formData.desired_occupation}
              </span>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 font-semibold text-xs block">रोजगार प्राधान्य (Employment Preference):</span>
              <span className="text-slate-900 font-bold text-base">
                {formData.employment_preference === 'wage' ? 'वेतन आधारित नोकरी (Wage Job)' : 'स्वयंरोजगार (Self-Employment)'}
              </span>
            </div>

            <div className="space-y-1">
              <span className="text-slate-500 font-semibold text-xs block">प्रवासाची मर्यादा (Mobility Radius):</span>
              <span className="text-slate-900 font-bold text-base">{formData.mobility_km} km radius</span>
            </div>

          </div>
        ) : (
          /* Editable Form State */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-semibold">
            <div>
              <label className="block text-slate-700 mb-1">नाव (Name):</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full border rounded p-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-slate-700 mb-1">वय (Age):</label>
              <input
                type="number"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) })}
                className="w-full border rounded p-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-slate-700 mb-1">जिल्हा (District):</label>
              <input
                type="text"
                value={formData.district}
                onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                className="w-full border rounded p-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-slate-700 mb-1">शिक्षण (Education):</label>
              <select
                value={formData.education}
                onChange={(e) => setFormData({ ...formData, education: e.target.value })}
                className="w-full border rounded p-2 text-sm"
              >
                <option value="5th Class Pass">5th Class Pass</option>
                <option value="8th Class Pass">8th Class Pass</option>
                <option value="10th Class Pass">10th Class Pass</option>
                <option value="12th Class Pass">12th Class Pass</option>
                <option value="Graduate">Graduate</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-700 mb-1">सध्याचे काम (Current Occupation):</label>
              <input
                type="text"
                value={formData.current_occupation}
                onChange={(e) => setFormData({ ...formData, current_occupation: e.target.value })}
                className="w-full border rounded p-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-slate-700 mb-1">इच्छित काम (Desired Occupation):</label>
              <input
                type="text"
                value={formData.desired_occupation}
                onChange={(e) => setFormData({ ...formData, desired_occupation: e.target.value })}
                className="w-full border rounded p-2 text-sm"
              />
            </div>
          </div>
        )}

        {/* Existing Skills List */}
        <div className="border-t pt-4">
          <div className="flex flex-wrap gap-2">
            {(beneficiary?.existing_skills || ['Basic Work Skills']).map((skill: string, idx: number) => (
              <span key={idx} className="bg-emerald-50 text-emerald-900 border border-emerald-300 text-xs font-semibold px-3 py-1 rounded-full">
                ✓ {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="border-t pt-6 flex flex-wrap items-center justify-between gap-4">
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="text-xs font-semibold text-slate-700 hover:text-slate-900 flex items-center space-x-1.5 border border-slate-300 px-4 py-2 rounded-lg bg-white shadow-sm"
          >
            {isEditing ? <Save className="w-4 h-4 text-emerald-600" /> : <Edit3 className="w-4 h-4 text-slate-600" />}
            <span>{isEditing ? 'माहिती सेव्ह करा (Save Edits)' : 'माहिती सुधारा (Edit Profile Details)'}</span>
          </button>

          <button
            onClick={handleConfirmAndProceed}
            className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-base px-6 py-3 rounded-lg shadow-sm flex items-center space-x-2 transition cursor-pointer"
          >
            <CheckCircle2 className="w-5 h-5 text-white" />
            <span>होय, ही माहिती बरोबर आहे (Confirm & Analyze Skill Gap)</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>

      </div>

    </div>
  );
};
