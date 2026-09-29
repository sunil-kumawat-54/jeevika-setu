import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { Mic, ArrowRight, Compass, Award, Building2, UserCheck, ShieldCheck, HeartHandshake, Sparkles } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { t, setLanguage, language } = useLanguage();
  const { setBeneficiary, setInterviewStep } = useBeneficiary();
  const navigate = useNavigate();

  // 6 Diverse Evaluation Personas
  const demoPersonas = [
    {
      id: 'persona-sita',
      name: 'Sita (Solar Electrical)',
      desc: '24 yrs, 10th Pass, Agriculture → Solar Energy Installation',
      data: {
        id: 'ben-sita-001',
        name: 'Sita',
        age: 24,
        gender: 'Female',
        location: 'Chhatrapati Sambhajinagar',
        district: 'Aurangabad',
        state: 'Maharashtra',
        pincode: '431006',
        language: 'Marathi',
        education: '10th Class Pass',
        current_occupation: 'Agricultural Laborer',
        existing_skills: ['Basic Farming', 'Pumphouse Operations', 'Hand Tools Handling'],
        experience_years: 3,
        desired_occupation: 'Solar Energy & Electrical Installation',
        interests: ['Solar Energy', 'Electrical Wiring'],
        employment_preference: 'wage',
        mobility_km: 15,
        digital_literacy: 'basic' as const,
        status: 'analyzed' as const,
        created_at: new Date().toISOString()
      }
    },
    {
      id: 'persona-anita',
      name: 'Anita Shinde (Tailoring Enterprise)',
      desc: '32 yrs, 8th Pass, Home Stitching → Garment Boutique Enterprise',
      data: {
        id: 'ben-anita-002',
        name: 'Anita Shinde',
        age: 32,
        gender: 'Female',
        location: 'Jalna District Village',
        district: 'Jalna',
        state: 'Maharashtra',
        pincode: '431203',
        language: 'Marathi',
        education: '8th Class Pass',
        current_occupation: 'Home Stitching / Tailoring',
        existing_skills: ['Garment Stitching', 'Hand Stitching', 'Basic Alterations'],
        experience_years: 4,
        desired_occupation: 'Self-Employed Tailor & Boutique Owner',
        interests: ['Garment Design', 'Apparel Business'],
        employment_preference: 'self_employment',
        mobility_km: 10,
        digital_literacy: 'none' as const,
        status: 'analyzed' as const,
        created_at: new Date().toISOString()
      }
    },
    {
      id: 'persona-ramesh',
      name: 'Ramesh Pawar (Healthcare Assistant)',
      desc: '28 yrs, 10th Pass, Unemployed Youth → Healthcare General Duty Assistant',
      data: {
        id: 'ben-ramesh-003',
        name: 'Ramesh Pawar',
        age: 28,
        gender: 'Male',
        location: 'Nanded Town',
        district: 'Nanded',
        state: 'Maharashtra',
        pincode: '431601',
        language: 'Hindi',
        education: '10th Class Pass',
        current_occupation: 'Unemployed Youth',
        existing_skills: ['Patient Care Assistance', 'First Aid'],
        experience_years: 1,
        desired_occupation: 'Healthcare Attendant / General Duty Assistant',
        interests: ['Healthcare Support', 'Patient Nursing'],
        employment_preference: 'wage',
        mobility_km: 20,
        digital_literacy: 'basic' as const,
        status: 'analyzed' as const,
        created_at: new Date().toISOString()
      }
    },
    {
      id: 'persona-rahul',
      name: 'Rahul Gaikwad (Auto Service Mechanic)',
      desc: '21 yrs, 8th Pass, Workshop Helper → Auto Service Technician',
      data: {
        id: 'ben-rahul-004',
        name: 'Rahul Gaikwad',
        age: 21,
        gender: 'Male',
        location: 'Nashik MIDC Area',
        district: 'Nashik',
        state: 'Maharashtra',
        pincode: '422001',
        language: 'Marathi',
        education: '8th Class Pass',
        current_occupation: 'Workshop Helper',
        existing_skills: ['Oil Changing', 'Basic Mechanical Repair'],
        experience_years: 2,
        desired_occupation: 'Auto Service Technician',
        interests: ['Automotive Repair', 'Engine Diagnostics'],
        employment_preference: 'wage',
        mobility_km: 15,
        digital_literacy: 'basic' as const,
        status: 'analyzed' as const,
        created_at: new Date().toISOString()
      }
    },
    {
      id: 'persona-priya',
      name: 'Priya Kulkarni (IT Data Entry Operator)',
      desc: '20 yrs, 12th Pass, Shop Assistant → Domestic Data Entry Operator',
      data: {
        id: 'ben-priya-005',
        name: 'Priya Kulkarni',
        age: 20,
        gender: 'Female',
        location: 'Pune Suburbs',
        district: 'Pune',
        state: 'Maharashtra',
        pincode: '411001',
        language: 'English',
        education: '12th Class Pass',
        current_occupation: 'Shop Counter Assistant',
        existing_skills: ['Computer Literacy', 'Keyboard Typing', 'MS Office'],
        experience_years: 1,
        desired_occupation: 'Domestic Data Entry Operator',
        interests: ['IT Services', 'Office Administration'],
        employment_preference: 'wage',
        mobility_km: 25,
        digital_literacy: 'intermediate' as const,
        status: 'analyzed' as const,
        created_at: new Date().toISOString()
      }
    },
    {
      id: 'persona-dnyaneshwar',
      name: 'Dnyaneshwar Patil (Organic Bio-Input Enterprise)',
      desc: '42 yrs, 5th Pass, Traditional Farmer → Organic Bio-Fertilizer Enterprise',
      data: {
        id: 'ben-dnyaneshwar-006',
        name: 'Dnyaneshwar Patil',
        age: 42,
        gender: 'Male',
        location: 'Latur Rural Village',
        district: 'Latur',
        state: 'Maharashtra',
        pincode: '413512',
        language: 'Marathi',
        education: '5th Class Pass',
        current_occupation: 'Smallholder Farmer',
        existing_skills: ['Traditional Composting', 'Soil Health'],
        experience_years: 15,
        desired_occupation: 'Organic Bio-Input & Vermicompost Production',
        interests: ['Organic Bio-Inputs', 'Agri Enterprise'],
        employment_preference: 'self_employment',
        mobility_km: 10,
        digital_literacy: 'none' as const,
        status: 'analyzed' as const,
        created_at: new Date().toISOString()
      }
    }
  ];

  const handleSelectPersona = (pData: any) => {
    setBeneficiary(pData);
    setInterviewStep(3);
    navigate('/profile');
  };

  return (
    <div className="space-y-10 pb-12">
      
      {/* Official PM-AJAY Scheme Banner */}
      <div className="bg-amber-50 border-b border-amber-200 py-2.5 px-4 text-center">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-center space-x-2 text-xs font-semibold text-amber-900">
          <ShieldCheck className="w-4 h-4 text-amber-700" />
          <span>{t('schemeBanner')}</span>
        </div>
      </div>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-10 shadow-sm grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center space-x-2 bg-blue-50 border border-blue-200 text-blue-900 text-xs font-bold px-3 py-1.5 rounded-full">
              <Mic className="w-4 h-4 text-blue-800" />
              <span>{t('multilingualAI')}</span>
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-blue-950 font-sans leading-tight">
              {t('brandTitle')}
            </h1>

            <p className="text-xl sm:text-2xl font-bold text-amber-900">
              "{t('tagline')}"
            </p>

            <p className="text-base sm:text-lg text-slate-700 leading-relaxed">
              {t('subtagline')}
            </p>

            {/* Language Selection */}
            <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-2">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                {t('selectLanguage')}
              </span>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setLanguage('mr')}
                  className={`px-4 py-2 rounded-lg text-sm font-bold border transition ${
                    language === 'mr' ? 'bg-blue-900 text-white border-blue-900 shadow-sm' : 'bg-white text-slate-800 border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  मराठी (Marathi)
                </button>
                <button
                  onClick={() => setLanguage('hi')}
                  className={`px-4 py-2 rounded-lg text-sm font-bold border transition ${
                    language === 'hi' ? 'bg-blue-900 text-white border-blue-900 shadow-sm' : 'bg-white text-slate-800 border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  हिंदी (Hindi)
                </button>
                <button
                  onClick={() => setLanguage('en')}
                  className={`px-4 py-2 rounded-lg text-sm font-bold border transition ${
                    language === 'en' ? 'bg-blue-900 text-white border-blue-900 shadow-sm' : 'bg-white text-slate-800 border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  English
                </button>
              </div>
            </div>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                to="/assessment"
                className="bg-blue-900 hover:bg-blue-800 text-white font-bold text-base sm:text-lg px-7 py-3.5 rounded-xl shadow-md flex items-center space-x-3 transition transform active:scale-95"
              >
                <Mic className="w-6 h-6 text-amber-300 animate-pulse" />
                <span>{t('startVoiceAssessment')}</span>
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>

            <p className="text-xs text-slate-500 font-medium">
              {t('noTypingRequired')}
            </p>
          </div>

          {/* Public Service Right Card */}
          <div className="lg:col-span-5 bg-gradient-to-br from-blue-50 to-amber-50 rounded-xl p-6 border border-slate-200 text-center space-y-4">
            <div className="w-20 h-20 bg-blue-900 text-amber-300 rounded-full flex items-center justify-center mx-auto shadow-md">
              <HeartHandshake className="w-10 h-10" />
            </div>
            <h3 className="text-xl font-bold text-blue-950">
              {t('publicServiceSys')}
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              {t('nsqfNqrConnected')}
            </p>

            <div className="space-y-2 text-left bg-white p-4 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-emerald-600 rounded-full"></span>
                <span>{t('step1Title')}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-emerald-600 rounded-full"></span>
                <span>{t('step2Title')}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-emerald-600 rounded-full"></span>
                <span>{t('step3Title')}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-emerald-600 rounded-full"></span>
                <span>{t('step4Title')}</span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* 6 Diverse Evaluation Personas Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        <div className="flex items-center justify-between border-b pb-2">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-amber-600" />
            <h2 className="text-lg sm:text-xl font-extrabold text-blue-950">
              मूल्यांकन चाचणी डेमोंस्ट्रेशन (Test System Against Diverse Evaluation Personas)
            </h2>
          </div>
          <span className="text-xs font-semibold bg-amber-100 text-amber-900 px-2.5 py-1 rounded">
            6 Diverse Test Profiles
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {demoPersonas.map((p) => (
            <div key={p.id} className="bg-white border-2 border-slate-300 hover:border-blue-900 rounded-xl p-4 shadow-sm space-y-3 transition flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b pb-2">
                  <h3 className="font-bold text-slate-900 text-sm flex items-center space-x-1.5">
                    <UserCheck className="w-4 h-4 text-blue-900" />
                    <span>{p.name}</span>
                  </h3>
                  <span className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-bold">
                    {p.data.district}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-2 font-medium">
                  {p.desc}
                </p>
              </div>

              <button
                onClick={() => handleSelectPersona(p.data)}
                className="w-full bg-blue-900 hover:bg-blue-800 text-white font-bold text-xs py-2 px-3 rounded-lg shadow-sm flex items-center justify-center space-x-1.5 transition cursor-pointer"
              >
                <span>हा प्रोफाईल टेस्ट करा (Test This Profile)</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Workflow Step Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-xl sm:text-2xl font-bold text-blue-950 mb-6 text-center">
          {t('journeyTitle')}
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2 relative">
            <span className="bg-blue-900 text-white font-bold text-xs px-2.5 py-1 rounded">
              {language === 'mr' ? 'पायरी १' : (language === 'hi' ? 'चरण १' : 'Step 1')}
            </span>
            <Mic className="w-8 h-8 text-blue-900 mt-2" />
            <h3 className="text-base font-bold text-slate-900">{t('step1Title')}</h3>
            <p className="text-xs text-slate-600">
              {t('step1Desc')}
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2 relative">
            <span className="bg-blue-900 text-white font-bold text-xs px-2.5 py-1 rounded">
              {language === 'mr' ? 'पायरी २' : (language === 'hi' ? 'चरण २' : 'Step 2')}
            </span>
            <Compass className="w-8 h-8 text-blue-900 mt-2" />
            <h3 className="text-base font-bold text-slate-900">{t('step2Title')}</h3>
            <p className="text-xs text-slate-600">
              {t('step2Desc')}
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2 relative">
            <span className="bg-blue-900 text-white font-bold text-xs px-2.5 py-1 rounded">
              {language === 'mr' ? 'पायरी ३' : (language === 'hi' ? 'चरण ३' : 'Step 3')}
            </span>
            <Building2 className="w-8 h-8 text-blue-900 mt-2" />
            <h3 className="text-base font-bold text-slate-900">{t('step3Title')}</h3>
            <p className="text-xs text-slate-600">
              {t('step3Desc')}
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2 relative">
            <span className="bg-blue-900 text-white font-bold text-xs px-2.5 py-1 rounded">
              {language === 'mr' ? 'पायरी ४' : (language === 'hi' ? 'चरण ४' : 'Step 4')}
            </span>
            <Award className="w-8 h-8 text-blue-900 mt-2" />
            <h3 className="text-base font-bold text-slate-900">{t('step4Title')}</h3>
            <p className="text-xs text-slate-600">
              {t('step4Desc')}
            </p>
          </div>
        </div>
      </section>

    </div>
  );
};
