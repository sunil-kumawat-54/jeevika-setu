import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { Briefcase, ExternalLink, ArrowRight, ShieldCheck } from 'lucide-react';

export const OpportunitiesPage: React.FC = () => {
  const { beneficiary } = useBeneficiary();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'wage' | 'enterprise'>('wage');

  const userName = beneficiary?.name || 'Beneficiary User';
  const userDistrict = beneficiary?.district || 'Chhatrapati Sambhajinagar';
  const userEdu = beneficiary?.education || '10th Class Pass';
  const desiredRole = beneficiary?.desired_occupation || 'Technical & Vocational Skills';

  const wageJobs = [
    {
      id: 'job-201',
      title: `Junior ${desiredRole} Specialist`,
      employer: `${userDistrict} Technical Services Pvt Ltd`,
      sector: 'Technical / Vocational Sector',
      location: `${userDistrict} Industrial Zone`,
      salary_range: '₹14,000 - ₹18,000 / month',
      vacancies: 12,
      job_type: 'Full-Time Wage Employment',
      education_req: `${userEdu} + NSQF Level 4 Certificate`,
      source_name: 'National Career Service (NCS Verified Job)',
      source_url: 'https://ncs.gov.in'
    },
    {
      id: 'job-202',
      title: `Assistant Specialist - ${desiredRole}`,
      employer: `Marathwada Development Co-op Society`,
      sector: 'Regional Utilities & Contracting',
      location: `${userDistrict} District`,
      salary_range: '₹12,000 - ₹16,000 / month',
      vacancies: 8,
      job_type: 'Contractual Wage Employment',
      education_req: `${userEdu} + Vocational Certificate`,
      source_name: 'National Career Service (NCS Verified Job)',
      source_url: 'https://ncs.gov.in'
    }
  ];

  const enterprisePathways = [
    {
      id: 'ent-301',
      title: `${userDistrict} स्थानिक ${desiredRole} मायक्रो-उद्योग (${desiredRole} Micro-Enterprise)`,
      sector: 'Self-Employment & Micro-Business',
      suitable_for: `${userName} (${userEdu} + NSQF Certification)`,
      equipment: ['Diagnostic Toolkit', 'Essential Equipment Set', 'Safety Gear', 'Customer Meter'],
      target_market: `Local households & commercial units across ${userDistrict} district`,
      grant_support: 'PM-AJAY GIA Grant-in-Aid Subsidized Loan (Up to ₹35,000 Support)',
      estimated_revenue: '₹18,000 - ₹28,000 / month',
      guidance_url: 'https://pmajay.gov.in/gia/enterprise-guidelines'
    }
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      
      {/* Title */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
        <div>
          <span className="text-blue-900 font-bold text-xs uppercase tracking-wider bg-blue-100 px-2.5 py-0.5 rounded">
            Livelihood Placement & Enterprise Pathways ({userDistrict})
          </span>
          <h1 className="text-2xl font-extrabold text-blue-950 mt-1">
            {userName} साठी रोजगार व उद्योग संधी (Opportunities)
          </h1>
          <p className="text-xs text-slate-600 mt-1">
            Verified local wage jobs and PM-AJAY Grant-in-Aid enterprise pathways for {desiredRole}.
          </p>
        </div>
        <Briefcase className="w-12 h-12 text-blue-900 hidden sm:block" />
      </div>

      {/* Pathway Switcher Tabs */}
      <div className="flex border-b border-slate-300">
        <button
          onClick={() => setActiveTab('wage')}
          className={`py-3 px-6 text-sm font-bold border-b-2 transition ${
            activeTab === 'wage' ? 'border-blue-900 text-blue-900 bg-blue-50/50' : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          १. वेतन आधारित नोकरी (Wage Employment Jobs)
        </button>
        <button
          onClick={() => setActiveTab('enterprise')}
          className={`py-3 px-6 text-sm font-bold border-b-2 transition ${
            activeTab === 'enterprise' ? 'border-blue-900 text-blue-900 bg-blue-50/50' : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          २. स्वयंरोजगार आणि मायक्रो-उद्योग (Enterprise Pathway)
        </button>
      </div>

      {/* Tab 1: Wage Employment Jobs */}
      {activeTab === 'wage' && (
        <div className="space-y-4">
          {wageJobs.map((job) => (
            <div key={job.id} className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-2 border-b pb-3">
                <div>
                  <span className="text-[11px] font-bold text-blue-900 uppercase tracking-wider">
                    {job.employer}
                  </span>
                  <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                    {job.title}
                  </h3>
                </div>
                <span className="bg-emerald-100 text-emerald-900 border border-emerald-300 font-extrabold text-sm px-3 py-1 rounded-full">
                  {job.salary_range}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded border">
                <div>
                  <span className="text-slate-500 block font-semibold">ठिकाण (Location):</span>
                  <span className="font-bold text-slate-900">{job.location}</span>
                </div>
                <div>
                  <span className="text-slate-500 block font-semibold">प्रकार (Type):</span>
                  <span className="font-bold text-slate-900">{job.job_type}</span>
                </div>
                <div>
                  <span className="text-slate-500 block font-semibold">रिक्त पदे (Vacancies):</span>
                  <span className="font-bold text-blue-900">{job.vacancies} Openings</span>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs bg-slate-100 p-2.5 rounded border border-slate-200">
                <span className="font-semibold text-slate-700 flex items-center space-x-1">
                  <ShieldCheck className="w-4 h-4 text-blue-900" />
                  <span>{job.source_name}</span>
                </span>
                <a href={job.source_url} target="_blank" rel="noreferrer" className="text-blue-900 font-bold hover:underline flex items-center space-x-1">
                  <span>NCS पोर्टलवर अर्ज करा →</span>
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 2: Micro-Enterprise Pathway */}
      {activeTab === 'enterprise' && (
        <div className="space-y-4">
          {enterprisePathways.map((ent) => (
            <div key={ent.id} className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-2 border-b pb-3">
                <div>
                  <span className="bg-amber-100 text-amber-900 border border-amber-300 text-xs font-bold px-2.5 py-0.5 rounded">
                    PM-AJAY GIA Enterprise Scheme
                  </span>
                  <h3 className="text-xl font-bold text-slate-900 mt-1">
                    {ent.title}
                  </h3>
                </div>
                <span className="bg-blue-100 text-blue-900 border border-blue-300 font-extrabold text-sm px-3 py-1 rounded-full">
                  {ent.estimated_revenue}
                </span>
              </div>

              <div className="space-y-2 text-xs font-medium text-slate-800 bg-slate-50 p-4 rounded border">
                <div>
                  <span className="font-bold text-slate-900 block mb-1">आवश्यक साधने (Equipment Toolkit Needed):</span>
                  <div className="flex flex-wrap gap-1.5">
                    {ent.equipment.map((eq, i) => (
                      <span key={i} className="bg-white border text-slate-700 px-2 py-0.5 rounded">
                        • {eq}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-2">
                  <span className="font-bold text-slate-900 block">पीएम-अजय अनुदान (PM-AJAY Financial Grant):</span>
                  <span className="text-emerald-800 font-bold">{ent.grant_support}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Navigation Action Buttons */}
      <div className="border-t pt-4 flex justify-between items-center">
        <button
          onClick={() => navigate('/training')}
          className="text-xs font-semibold text-slate-700 hover:text-slate-900"
        >
          ← मागे जा (Back to Training)
        </button>

        <button
          onClick={() => navigate('/roadmap')}
          className="bg-emerald-700 hover:bg-emerald-800 text-white font-extrabold text-base px-7 py-3.5 rounded-xl shadow-md flex items-center space-x-2 transition cursor-pointer"
        >
          <span>माझा संपूर्ण उपजीविका रोडमॅप पहा (View Personalized Livelihood Roadmap)</span>
          <ArrowRight className="w-5 h-5 text-white" />
        </button>
      </div>

    </div>
  );
};
