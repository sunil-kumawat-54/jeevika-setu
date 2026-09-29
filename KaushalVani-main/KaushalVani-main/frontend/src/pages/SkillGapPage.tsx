import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { resolveQualification } from '../utils/nqrResolver';
import { Award, ArrowRight, CheckCircle2, AlertTriangle } from 'lucide-react';

export const SkillGapPage: React.FC = () => {
  const { beneficiary } = useBeneficiary();
  const navigate = useNavigate();

  const userName = beneficiary?.name || 'Beneficiary User';
  const desired = beneficiary?.desired_occupation || 'Technical & Vocational Skills';
  const existingSkills = beneficiary?.existing_skills || [];

  // Dynamic Skill Gap Matrix based on user's actual desired role
  const resolved = resolveQualification(desired, existingSkills, beneficiary?.education || '10th Class Pass');
  const targetQP = resolved.qp_code;
  const targetRole = resolved.job_role;
  const targetSector = resolved.sector;
  const requiredSkillList = resolved.missing_skills;

  // Append user's existing skills as matched skills
  const matchedSkills = existingSkills.map((s: string) => ({
    skill: `${s} (Captured Experience)`,
    severity: 'Low' as const,
    missing: false
  }));

  const allDisplaySkills = [...requiredSkillList, ...matchedSkills];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      
      {/* Title */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
        <div>
          <span className="text-blue-900 font-bold text-xs uppercase tracking-wider bg-blue-100 px-2.5 py-0.5 rounded">
            Dynamic AI Skill Gap Analysis (NSQF Level 4)
          </span>
          <h1 className="text-2xl font-extrabold text-blue-950 mt-1">
            {userName} - कौशल्य फरक विश्लेषण (Skill Gap)
          </h1>
          <p className="text-xs text-slate-600 mt-1">
            Comparing {userName}'s existing practical skills against {targetRole} ({targetQP}) requirements.
          </p>
        </div>
        <Award className="w-12 h-12 text-blue-900 hidden sm:block" />
      </div>

      {/* Main Analysis Card */}
      <div className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-6">
        
        {/* Target Qualification Summary */}
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-900">
              लक्ष्य राष्ट्रीय पात्रता (Target NQR Qualification)
            </span>
            <h3 className="text-lg font-bold text-amber-950">
              {targetRole} (QP Code: {targetQP})
            </h3>
            <p className="text-xs text-amber-900 font-medium">
              Sector: {targetSector} | NSQF Level 4 | Duration: 350 Hours
            </p>
          </div>
          <span className="bg-amber-200 text-amber-950 text-xs font-extrabold px-3 py-1.5 rounded-full border border-amber-400">
            Moderate Skill Gap
          </span>
        </div>

        {/* Skill Gap Comparison Grid */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            कौशल्य तुलना तक्ता (Required vs Existing Skill Breakdown for {userName}):
          </h3>

          <div className="divide-y border rounded-lg overflow-hidden">
            {allDisplaySkills.map((item, idx) => (
              <div key={idx} className="p-3.5 bg-white flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center space-x-3">
                  {item.missing ? (
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                  )}
                  <div>
                    <span className="text-sm font-bold text-slate-900 block">{item.skill}</span>
                    <span className="text-xs text-slate-500">
                      {item.missing ? 'प्रशिक्षणाची आवश्यकता आहे (Training Module Needed)' : 'सध्या उपलब्ध कौशल्य (Captured Transferable Experience)'}
                    </span>
                  </div>
                </div>

                <span className={`text-xs font-bold px-2.5 py-1 rounded border ${
                  item.missing
                    ? (item.severity === 'High' ? 'bg-red-50 text-red-800 border-red-200' : 'bg-amber-50 text-amber-800 border-amber-200')
                    : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                }`}>
                  {item.missing ? `Gap: ${item.severity}` : 'Matched'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <div className="border-t pt-4 flex justify-end">
          <button
            onClick={() => navigate('/recommendations')}
            className="bg-blue-900 hover:bg-blue-800 text-white font-bold text-base px-6 py-3 rounded-lg shadow-sm flex items-center space-x-2 transition cursor-pointer"
          >
            <span>योग्य राष्ट्रीय प्रमाणपत्रे पहा (View Recommended Qualifications)</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>

      </div>

    </div>
  );
};
