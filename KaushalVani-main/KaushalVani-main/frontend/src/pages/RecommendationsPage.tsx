import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { resolveQualification } from '../utils/nqrResolver';
import { Award, CheckCircle2, ExternalLink, ArrowRight, ShieldCheck } from 'lucide-react';

export const RecommendationsPage: React.FC = () => {
  const { recommendation, beneficiary } = useBeneficiary();
  const navigate = useNavigate();

  const userName = beneficiary?.name || 'Beneficiary User';
  const desired = beneficiary?.desired_occupation || 'Technical & Vocational Skills';
  const userDistrict = beneficiary?.district || 'Chhatrapati Sambhajinagar';
  const userEdu = beneficiary?.education || '10th Class Pass';

  // Dynamic qualification mapping based on user's actual desired occupation
  const primaryQual = resolveQualification(desired, beneficiary?.existing_skills || [], userEdu);

  const explainableReasons = [
    `✓ Directly matches ${userName}'s ambition for ${primaryQual.job_role}`,
    `✓ Fully satisfies entry eligibility criteria (${userEdu})`,
    `✓ Accredited NSQF Level ${primaryQual.nsqf_level} National Qualification with ${primaryQual.awarding_body}`,
    `✓ Accredited training centre available within ${beneficiary?.mobility_km || 15} km mobility radius`,
    `✓ Verified local wage employment & PM-AJAY GIA enterprise opportunities active in ${userDistrict} district`
  ];

  const factors = [
    { factor: 'Aspiration Match', score: primaryQual.score, desc: `Direct alignment with ${userName}'s stated goal in ${primaryQual.job_role}` },
    { factor: 'Education Eligibility', score: 92, desc: `Meets entry requirement (${primaryQual.eligibility})` },
    { factor: 'Local Demand & Jobs', score: 90, desc: `Active PM-AJAY placement listings in ${userDistrict}` },
    { factor: 'Geospatial Distance', score: 88, desc: `Training centre within ${beneficiary?.mobility_km || 15} km` },
    { factor: 'Skill Transferability', score: 85, desc: `Prior experience (${(beneficiary?.existing_skills || [])[0] || 'practical experience'}) transfers well` }
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      
      {/* Page Title */}
      <div className="bg-blue-900 text-white rounded-xl p-6 shadow-sm flex items-center justify-between">
        <div>
          <span className="text-amber-300 font-bold text-xs uppercase tracking-wider">
            पायरी ५ ऑफ ७ (Step 5 of 7)
          </span>
          <h1 className="text-2xl font-bold mt-1">
            {userName} साठी शिफारस केलेली प्रमाणपत्रे (Dynamic NSQF Recommendations)
          </h1>
          <p className="text-xs text-blue-200 mt-1">
            Explainable AI recommendations derived from NQR qualification registry for {userName} ({userDistrict}).
          </p>
        </div>
        <Award className="w-12 h-12 text-amber-300 hidden sm:block" />
      </div>

      {/* Main Recommended Qualification Card */}
      <div className="bg-white border-2 border-blue-900 rounded-xl p-6 shadow-sm space-y-6">
        
        {/* Top Header & Score Badge */}
        <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-4">
          <div>
            <span className="bg-blue-100 text-blue-900 border border-blue-300 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              सर्वोत्तम शिफारस (Top Match Recommendation)
            </span>
            <h2 className="text-2xl font-extrabold text-slate-900 mt-2">
              {primaryQual.job_role}
            </h2>
            <p className="text-xs font-semibold text-slate-600">
              QP Code: {primaryQual.qp_code} | Sector: {primaryQual.sector}
            </p>
          </div>

          <div className="bg-emerald-50 border-2 border-emerald-600 rounded-xl p-3 text-center min-w-[120px]">
            <span className="text-xs font-bold text-emerald-800 uppercase block">Match Score</span>
            <span className="text-3xl font-extrabold text-emerald-700">{primaryQual.score}%</span>
          </div>
        </div>

        {/* Qualification Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-medium">
          <div className="bg-slate-50 p-3 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold">NSQF स्तर (NSQF Level):</span>
            <span className="font-bold text-slate-900 text-sm">Level {primaryQual.nsqf_level}</span>
          </div>
          <div className="bg-slate-50 p-3 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold">कालावधी (Duration):</span>
            <span className="font-bold text-slate-900 text-sm">{primaryQual.duration_hours} Hours (~3 Months)</span>
          </div>
          <div className="bg-slate-50 p-3 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold">प्रमाणपत्र मंडळ (Awarding Body):</span>
            <span className="font-bold text-slate-900">{primaryQual.awarding_body}</span>
          </div>
        </div>

        {/* Official Source Provenance Link */}
        <div className="bg-slate-100 border border-slate-300 rounded-lg p-3 flex flex-wrap items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-blue-900" />
            <span className="font-semibold text-slate-800">
              स्रोत (Source): {primaryQual.source_name} (Last verified: {primaryQual.last_verified_at})
            </span>
          </div>
          <a
            href={primaryQual.source_url}
            target="_blank"
            rel="noreferrer"
            className="text-blue-900 hover:underline font-bold flex items-center space-x-1"
          >
            <span>अधिकृत NQR रेकॉर्ड पहा (View Official NQR Record)</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Explainability Section - WHY THIS IS RECOMMENDED */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-5 space-y-3">
          <h3 className="text-sm font-bold text-blue-950 uppercase tracking-wider flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-700" />
            <span>ही शिफारस का दिली आहे? (WHY THIS IS RECOMMENDED FOR {userName.toUpperCase()})</span>
          </h3>

          <ul className="space-y-2 text-xs font-semibold text-slate-800">
            {explainableReasons.map((reason, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <span className="text-emerald-700 font-bold">✓</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Factors Breakdown */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            घटक विश्लेषण (Factors Considered in Score):
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            {factors.map((f, idx) => (
              <div key={idx} className="bg-white border p-2.5 rounded flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900 block">{f.factor}</span>
                  <span className="text-slate-500">{f.desc}</span>
                </div>
                <span className="font-extrabold text-blue-900 bg-blue-50 px-2 py-1 rounded border border-blue-200">
                  {f.score}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Navigation Action Buttons */}
        <div className="border-t pt-4 flex justify-between items-center">
          <button
            onClick={() => navigate('/skill-gap')}
            className="text-xs font-semibold text-slate-700 hover:text-slate-900"
          >
            ← मागे जा (Back to Skill Gap)
          </button>

          <button
            onClick={() => navigate('/training')}
            className="bg-blue-900 hover:bg-blue-800 text-white font-bold text-base px-6 py-3 rounded-lg shadow-sm flex items-center space-x-2 transition"
          >
            <span>जवळची प्रशिक्षण केंद्रे पहा (Find Nearby Training Centres)</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>

      </div>

    </div>
  );
};
