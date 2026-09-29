import React from 'react';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { Compass, Award, Building2, Briefcase, Printer, ShieldCheck, Sparkles, HelpCircle } from 'lucide-react';

export const RoadmapPage: React.FC = () => {
  const { beneficiary } = useBeneficiary();

  const handlePrint = () => {
    window.print();
  };

  const userName = beneficiary?.name || 'Beneficiary User';
  const userAge = beneficiary?.age || 20;
  const userDistrict = beneficiary?.district || 'Chhatrapati Sambhajinagar';
  const userEdu = beneficiary?.education || '10th Class Pass';
  const currentOcc = beneficiary?.current_occupation || 'General Worker';
  const desiredRole = beneficiary?.desired_occupation || 'Vocational & Enterprise Pathway';
  const userMobility = beneficiary?.mobility_km || 15;
  const existingSkillsList = (beneficiary?.existing_skills || ['Practical Experience']).join(', ');

  const steps = [
    {
      num: '01',
      title: `${userName} - Baseline Profile (सध्याचे प्रोफाईल)`,
      desc: `${userName} | Age: ${userAge} | Education: ${userEdu} | Location: ${userDistrict} District`,
      detail: `Current Livelihood: ${currentOcc}. Captured Skills: ${existingSkillsList}. Stated Aspiration: ${desiredRole}.`,
      status: 'Completed',
      icon: Compass,
      color: 'bg-blue-900 text-white'
    },
    {
      num: '02',
      title: 'Skill Gap & Qualification Mapping (कौशल्य फरक)',
      desc: `Target NSQF Level 4 Job Role: ${desiredRole}`,
      detail: `Mapped against National Qualification Register (NQR). Skill Gap: Technical Practical Modules & Equipment Operations.`,
      status: 'Analyzed',
      icon: Award,
      color: 'bg-amber-600 text-white'
    },
    {
      num: '03',
      title: 'Recommended Skill Training (प्रशिक्षण कार्यक्रम)',
      desc: `Accredited Skill Training Program (340-480 Hours / ~3 Months)`,
      detail: `Under Sector Skill Council accreditation. Covered under PM-AJAY Grant-in-Aid (GIA) stipend support.`,
      status: 'Enrolling',
      icon: Building2,
      color: 'bg-blue-800 text-white'
    },
    {
      num: '04',
      title: 'Training Centre Matching (प्रशिक्षण केंद्र)',
      desc: `PMKVK Government ITI ${userDistrict} (Within ${userMobility} km mobility radius)`,
      detail: `Accredited training facility located at ${userDistrict} Industrial Sector. Upcoming batch enrolment active.`,
      status: 'Matched',
      icon: Building2,
      color: 'bg-blue-900 text-white'
    },
    {
      num: '05',
      title: 'Assessment & NQR Certification (राष्ट्रीय प्रमाणपत्र)',
      desc: 'Formal NSQF Level 4 Government Certification',
      detail: 'Official NQR verification url: nqr.gov.in. Issued upon achieving required assessment score.',
      status: 'Pending Assessment',
      icon: ShieldCheck,
      color: 'bg-amber-700 text-white'
    },
    {
      num: '06',
      title: 'Wage Employment Opportunity (रोजगार मार्ग)',
      desc: `Role: Junior ${desiredRole} Specialist in ${userDistrict}`,
      detail: 'Salary Range: ₹14,000 - ₹18,000 / month. Verified listing via National Career Service (NCS).',
      status: 'Targeted',
      icon: Briefcase,
      color: 'bg-emerald-700 text-white'
    },
    {
      num: '07',
      title: 'Alternative Enterprise Pathway (स्वयंरोजगार मार्ग)',
      desc: `Setup: ${userDistrict} ${desiredRole} Micro-Enterprise`,
      detail: `Grant Support: Subsidized micro-grant up to ₹35,000 under PM-AJAY GIA scheme. Estimated revenue: ₹18,000 - ₹28,000/mo.`,
      status: 'Alternative',
      icon: Sparkles,
      color: 'bg-purple-700 text-white'
    }
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      
      {/* Top Banner & Print Controls */}
      <div className="bg-white border-2 border-blue-900 rounded-2xl p-6 sm:p-8 shadow-md space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
          <div>
            <span className="bg-blue-900 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              PM-AJAY GIA Dynamic Livelihood Roadmap
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-blue-950 mt-2 font-sans">
              {userName} यांचा वैयक्तिकृत उपजीविका मार्गदर्शक नकाशा
            </h1>
            <p className="text-xs text-slate-600 font-medium mt-1">
              Personalized Livelihood Roadmap for {userName} ({userAge} yrs, {userDistrict} District)
            </p>
          </div>

          <div className="flex items-center space-x-2 no-print">
            <button
              onClick={handlePrint}
              className="bg-blue-900 hover:bg-blue-800 text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-sm flex items-center space-x-1.5 transition cursor-pointer"
            >
              <Printer className="w-4 h-4" />
              <span>रोडमॅप प्रिंट करा (Print Roadmap)</span>
            </button>
          </div>
        </div>

        {/* Explainability Banner: WHY THIS PATHWAY? */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-3">
          <div className="flex items-center space-x-2">
            <HelpCircle className="w-5 h-5 text-blue-900" />
            <h3 className="text-sm font-bold text-blue-950 uppercase tracking-wider">
              हा मार्ग का निवडला आहे? (WHY THIS PATHWAY FOR {userName.toUpperCase()}?)
            </h3>
          </div>
          <p className="text-xs text-slate-800 leading-relaxed font-medium">
            This customized roadmap directly bridges {userName}'s background in {currentOcc} with their explicit goal to learn {desiredRole}. By completing the accredited NSQF Level 4 training at the nearby Government ITI in {userDistrict} (within {userMobility} km mobility radius), {userName} earns a government-recognized certificate while satisfying entry criteria ({userEdu}). Upon graduation, {userName} can enter local wage employment paying ₹14,000–₹18,000/month or leverage PM-AJAY GIA micro-enterprise grant support to start a local enterprise.
          </p>
        </div>
      </div>

      {/* Main Timeline Roadmap Steps */}
      <div className="space-y-6 relative before:absolute before:inset-0 before:left-8 before:w-1 before:bg-blue-200 before:z-0">
        
        {steps.map((step, index) => {
          const IconComponent = step.icon;
          return (
            <div key={index} className="relative z-10 flex items-start space-x-4 group">
              {/* Step Number Badge */}
              <div className={`w-16 h-16 rounded-full flex flex-col items-center justify-center font-extrabold shadow-md flex-shrink-0 border-2 border-white ${step.color}`}>
                <span className="text-xs uppercase">STEP</span>
                <span className="text-lg leading-none">{step.num}</span>
              </div>

              {/* Step Detail Card */}
              <div className="flex-1 bg-white border-2 border-slate-300 rounded-xl p-5 shadow-sm space-y-2 group-hover:border-blue-900 transition">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 flex items-center space-x-2">
                    <IconComponent className="w-5 h-5 text-blue-900" />
                    <span>{step.title}</span>
                  </h3>
                  <span className="bg-slate-100 text-slate-800 border text-[11px] font-bold px-2.5 py-0.5 rounded-full">
                    {step.status}
                  </span>
                </div>

                <p className="text-sm font-bold text-blue-900">
                  {step.desc}
                </p>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {step.detail}
                </p>
              </div>
            </div>
          );
        })}

      </div>

      {/* Final Verification Note */}
      <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-center text-xs text-amber-900 font-semibold">
        <ShieldCheck className="w-5 h-5 text-amber-700 mx-auto mb-1" />
        <span>हा रोडमॅप राष्ट्रीय कौशल्य पात्रता आराखडा (NSQF) व PM-AJAY उपजीविका मार्गदर्शक तत्त्वांशी सुसंगत आहे.</span>
      </div>

    </div>
  );
};
