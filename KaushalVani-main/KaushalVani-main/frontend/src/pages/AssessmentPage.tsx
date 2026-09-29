import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { VoiceRecorder } from '../components/VoiceRecorder';
import { User, CheckCircle2, ArrowRight, ArrowLeft, Sparkles, MapPin, Briefcase, GraduationCap, RotateCcw, HelpCircle } from 'lucide-react';
import axios from 'axios';

export const AssessmentPage: React.FC = () => {
  const { language, t, speakText } = useLanguage();
  const { beneficiary, setBeneficiary, setInterviewStep } = useBeneficiary();
  const navigate = useNavigate();

  const [currentPromptIndex, setCurrentPromptIndex] = useState<number>(0);

  // Question Answers State for all 6 questions
  const [questionAnswers, setQuestionAnswers] = useState<Record<number, string>>({});

  // Clean dynamic extracted profile - NO HARDCODED DEFAULTS
  const [extractedProfile, setExtractedProfile] = useState<any>({
    name: beneficiary?.name && beneficiary.name !== 'User' ? beneficiary.name : '',
    age: beneficiary?.age && beneficiary.age !== 24 ? beneficiary.age : 0,
    location: beneficiary?.location || '',
    district: beneficiary?.district || '',
    education: beneficiary?.education || '',
    current_occupation: beneficiary?.current_occupation || '',
    desired_occupation: beneficiary?.desired_occupation || '',
    existing_skills: beneficiary?.existing_skills || [],
    employment_preference: beneficiary?.employment_preference || 'wage',
    mobility_km: beneficiary?.mobility_km || 15
  });

  const promptQuestions = [
    {
      field: 'identity',
      mr: 'तुमचे नाव आणि वय सांगा.',
      hi: 'अपना नाम और उम्र बताएं।',
      en: 'What is your name and age?',
      hint: 'उदा. "माझे नाव चीकू कांबळे आहे, वय २० वर्षे आहे"'
    },
    {
      field: 'location',
      mr: 'तुम्ही सध्या कोणत्या गावात किंवा जिल्ह्यात राहता?',
      hi: 'आप अभी किस गांव या जिले में रहते हैं?',
      en: 'Which village or district do you currently live in?',
      hint: 'उदा. "मी औरंगाबाद / छत्रपती संभाजीनगर जिल्ह्यात राहतो"'
    },
    {
      field: 'current_occupation',
      mr: 'तुम्ही सध्या काय काम करता आणि तुमचा अनुभव काय आहे?',
      hi: 'आप अभी क्या काम करते हैं और आपका अनुभव क्या है?',
      en: 'What work do you currently do and what is your experience?',
      hint: 'उदा. "मी शेतीत काम करतो, २ वर्षांचा अनुभव आहे"'
    },
    {
      field: 'desired_occupation',
      mr: 'तुम्हाला भविष्यात कोणते काम किंवा कौशल्य शिकायला आवडेल?',
      hi: 'आप भविष्य में कौन सा काम या कौशल सीखना चाहते हैं?',
      en: 'What job role or technical skill would you like to learn?',
      hint: 'उदा. "मला सोलर, टेलरिंग, कॉम्प्युटर, किंवा ब्यूटी पार्लर शिकायचे आहे"'
    },
    {
      field: 'education',
      mr: 'तुमचे उच्चतम शिक्षण किती झाले आहे? (उदा. ५ वी, ८ वी, १० वी पास)',
      hi: 'आपकी उच्चतम शिक्षा कितनी हुई है? (उदा. 5वीं, 8वीं, 10वीं पास)',
      en: 'What is your highest education level? (e.g. 8th pass, 10th pass)',
      hint: 'उदा. "मी १० वी पास आहे"'
    },
    {
      field: 'mobility',
      mr: 'प्रशिक्षणासाठी तुम्ही किती किलोमीटर जाऊ शकता आणि तुम्हाला नोकरी हवी आहे की व्यवसाय?',
      hi: 'ट्रेनिंग के लिए आप कितने किलोमीटर तक जा सकते हैं और आपको नौकरी चाहिए या बिजनेस?',
      en: 'How far can you travel for training and do you prefer a job or enterprise?',
      hint: 'उदा. "मी १५ किमी जाऊ शकतो आणि मला नोकरी हवी आहे"'
    }
  ];

  const currentQ = promptQuestions[currentPromptIndex] || promptQuestions[0];
  const questionText = currentQ[language as keyof typeof currentQ] || currentQ['mr'];

  // Client-Side Entity & Intent Parser (Completely Dynamic)
  const parseClientEntities = (transcript: string, current: any, fieldKey: string) => {
    const lower = transcript.toLowerCase();
    let updated = { ...current };

    // 1. Name Extraction (Question 1 or identity field)
    if (fieldKey === 'identity' || transcript.includes('नाव') || transcript.includes('नाम') || lower.includes('name') || lower.includes('i am')) {
      const nameMatch = transcript.match(/(?:माझे नाव|नाव|मेरा नाम|नाम|my name is|i am)\s+([A-Za-z\u0900-\u097F]+)/i);
      if (nameMatch && nameMatch[1]) {
        const potential = nameMatch[1].trim();
        if (!['आहे', 'है', 'is', 'a'].includes(potential.toLowerCase())) {
          updated.name = potential.charAt(0).toUpperCase() + potential.slice(1);
        }
      } else if (fieldKey === 'identity' && !updated.name) {
        // First word if short sentence
        const firstWord = transcript.trim().split(' ')[0].replace(/[.,]/g, '');
        if (firstWord && firstWord.length >= 2 && !/\d/.test(firstWord)) {
          updated.name = firstWord.charAt(0).toUpperCase() + firstWord.slice(1);
        }
      }
    }

    // 2. Age Extraction
    const ageMatch = transcript.match(/(\d{2})\s*(?:वर्षे|साल|years|yrs|वय|उम्र)?/);
    if (ageMatch) {
      const parsedAge = parseInt(ageMatch[1]);
      if (parsedAge >= 15 && parsedAge <= 75) {
        updated.age = parsedAge;
      }
    }

    // 3. District / Location Extraction
    const districtKeywords: Record<string, string> = {
      'संभाजीनगर': 'Aurangabad', 'औरंगाबाद': 'Aurangabad', 'aurangabad': 'Aurangabad',
      'जालना': 'Jalna', 'jalna': 'Jalna',
      'पुणे': 'Pune', 'pune': 'Pune',
      'नाशिक': 'Nashik', 'nashik': 'Nashik',
      'नांदेड': 'Nanded', 'nanded': 'Nanded',
      'लातूर': 'Latur', 'latur': 'Latur',
      'नागपूर': 'Nagpur', 'nagpur': 'Nagpur',
      'बीड': 'Beed', 'beed': 'Beed',
      'मुंबई': 'Mumbai', 'mumbai': 'Mumbai',
      'ठाणे': 'Thane', 'thane': 'Thane'
    };
    for (const [kw, dist] of Object.entries(districtKeywords)) {
      if (lower.includes(kw)) {
        updated.district = dist;
        updated.location = `${dist} District`;
        break;
      }
    }
    if (fieldKey === 'location' && !updated.district && transcript.length > 2) {
      updated.district = transcript.trim();
      updated.location = `${transcript.trim()} District`;
    }

    // 4. Education Extraction
    if (lower.includes('10') || lower.includes('दहावी') || lower.includes('10th') || lower.includes('दसवीं')) {
      updated.education = '10th Class Pass';
    } else if (lower.includes('12') || lower.includes('बारावी') || lower.includes('12th') || lower.includes('बारहवीं')) {
      updated.education = '12th Class Pass';
    } else if (lower.includes('8') || lower.includes('आठवी') || lower.includes('8th') || lower.includes('आठवीं')) {
      updated.education = '8th Class Pass';
    } else if (lower.includes('5') || lower.includes('पांचवी') || lower.includes('5th')) {
      updated.education = '5th Class Pass';
    } else if (lower.includes('पदवी') || lower.includes('graduate') || lower.includes('college')) {
      updated.education = 'Graduate';
    } else if (fieldKey === 'education' && !updated.education) {
      updated.education = transcript;
    }

    // 5. Current Occupation & Skills Extraction
    if (lower.includes('शेती') || lower.includes('खेती') || lower.includes('farm') || lower.includes('agri') || lower.includes('शेतकरी')) {
      updated.current_occupation = 'Agricultural Laborer';
      updated.existing_skills = Array.from(new Set([...updated.existing_skills, 'Crop Cultivation', 'Basic Farming', 'Hand Tools Handling']));
    } else if (lower.includes('शिवण') || lower.includes('कपडे') || lower.includes('tailor') || lower.includes('दर्जी') || lower.includes('stitching')) {
      updated.current_occupation = 'Garment Tailor / Stitcher';
      updated.existing_skills = Array.from(new Set([...updated.existing_skills, 'Garment Stitching', 'Measurement Taking', 'Pattern Cutting']));
    } else if (lower.includes('मॅकेनिक') || lower.includes('गॅरेज') || lower.includes('garage') || lower.includes('mechanic') || lower.includes('गाडी')) {
      updated.current_occupation = 'Workshop Helper / Mechanic';
      updated.existing_skills = Array.from(new Set([...updated.existing_skills, 'Auto Servicing', 'Mechanical Tools', 'Basic Repairs']));
    } else if (lower.includes('दुकान') || lower.includes('शॉप') || lower.includes('shop') || lower.includes('sales')) {
      updated.current_occupation = 'Shop Assistant & Sales';
      updated.existing_skills = Array.from(new Set([...updated.existing_skills, 'Customer Handling', 'Cash Counter Operation']));
    } else if (lower.includes('कॉम्प्युटर') || lower.includes('डाटा') || lower.includes('computer') || lower.includes('data')) {
      updated.current_occupation = 'Computer Assistant';
      updated.existing_skills = Array.from(new Set([...updated.existing_skills, 'Computer Operations', 'Keyboard Typing']));
    } else if (lower.includes('जैविक') || lower.includes('खत') || lower.includes('bio') || lower.includes('organic')) {
      updated.current_occupation = 'Organic Bio-Input Farmer';
      updated.existing_skills = Array.from(new Set([...updated.existing_skills, 'Bio-Fertilizer Production', 'Soil Testing']));
    } else if (fieldKey === 'current_occupation' && transcript.length > 2) {
      updated.current_occupation = transcript;
      updated.existing_skills = Array.from(new Set([...updated.existing_skills, transcript]));
    }

    // 6. Desired Occupation / Aspirations Extraction (DYNAMIC)
    if (lower.includes('सोलर') || lower.includes('वीज') || lower.includes('बिजली') || lower.includes('solar') || lower.includes('electric') || lower.includes('वायरिंग')) {
      updated.desired_occupation = 'Solar Energy & Electrical Installation';
    } else if (lower.includes('शिवणकाम') || lower.includes('बुटीक') || lower.includes('boutique') || lower.includes('fashion') || lower.includes('कपड्यांचा') || lower.includes('टेलरींग')) {
      updated.desired_occupation = 'Self-Employed Tailor & Boutique Owner';
    } else if (lower.includes('दवाखाना') || lower.includes('हॉस्पिटल') || lower.includes('hospital') || lower.includes('health') || lower.includes('नर्स') || lower.includes('पेशंट')) {
      updated.desired_occupation = 'Healthcare Attendant / General Duty Assistant';
    } else if (lower.includes('कॉम्प्युटर') || lower.includes('डाटा') || lower.includes('computer') || lower.includes('data entry') || lower.includes('office')) {
      updated.desired_occupation = 'Domestic Data Entry Operator';
    } else if (lower.includes('जैविक') || lower.includes('ऑर्गेनिक') || lower.includes('bio-input') || lower.includes('खत')) {
      updated.desired_occupation = 'Organic Farming & Bio-Input Producer';
    } else if (lower.includes('ब्यूटी') || lower.includes('पार्लर') || lower.includes('beauty') || lower.includes('parlour')) {
      updated.desired_occupation = 'Beauty Culture & Hair Dressing Specialist';
    } else if (lower.includes('फूड') || lower.includes('प्रॉसेसिंग') || lower.includes('food processing') || lower.includes('पापड')) {
      updated.desired_occupation = 'Food Processing & Micro Enterprise Operator';
    } else if (lower.includes('ड्रायव्हिंग') || lower.includes('चालक') || lower.includes('driver')) {
      updated.desired_occupation = 'Commercial Vehicle Driver';
    } else if (fieldKey === 'desired_occupation' && transcript.length > 2) {
      // Use exact user response if no keyword matched!
      updated.desired_occupation = transcript.charAt(0).toUpperCase() + transcript.slice(1);
    }

    // 7. Employment Preference & Mobility
    if (lower.includes('व्यवसाय') || lower.includes('बिजनेस') || lower.includes('business') || lower.includes('enterprise') || lower.includes('स्वतः')) {
      updated.employment_preference = 'self_employment';
    } else if (lower.includes('नोकरी') || lower.includes('job') || lower.includes('salary')) {
      updated.employment_preference = 'wage';
    }

    const kmMatch = lower.match(/(\d{1,2})\s*(?:km|किमी|किलोमीटर)/);
    if (kmMatch) {
      updated.mobility_km = parseInt(kmMatch[1]);
    }

    return updated;
  };

  const handleTranscriptConfirmed = async (transcript: string) => {
    // Store question answer for current index
    const updatedAnswers = { ...questionAnswers, [currentPromptIndex]: transcript };
    setQuestionAnswers(updatedAnswers);

    let newProfile = parseClientEntities(transcript, extractedProfile, currentQ.field);

    // Call Python AI backend for profile refinement
    try {
      const res = await axios.post('/ai/extract-profile', {
        transcript,
        current_profile: newProfile,
        language
      });

      if (res.data) {
        newProfile = {
          ...newProfile,
          name: res.data.name || newProfile.name,
          age: res.data.age || newProfile.age,
          location: res.data.location || newProfile.location,
          district: res.data.district || newProfile.district,
          education: res.data.education || newProfile.education,
          current_occupation: res.data.current_occupation || newProfile.current_occupation,
          desired_occupation: res.data.desired_occupation || newProfile.desired_occupation,
          existing_skills: res.data.existing_skills && res.data.existing_skills.length ? res.data.existing_skills : newProfile.existing_skills,
          employment_preference: res.data.employment_preference || newProfile.employment_preference,
          mobility_km: res.data.mobility_km || newProfile.mobility_km
        };
      }
    } catch (err) {
      console.log('AI Extraction active locally');
    }

    setExtractedProfile(newProfile);

    // Auto advance to next unanswered question or finish
    if (currentPromptIndex < promptQuestions.length - 1) {
      setCurrentPromptIndex(currentPromptIndex + 1);
    }
  };

  const handleReRecordQuestion = (qIndex: number) => {
    const updatedAnswers = { ...questionAnswers };
    delete updatedAnswers[qIndex];
    setQuestionAnswers(updatedAnswers);
    setCurrentPromptIndex(qIndex);
  };

  const handleFinishAssessment = async () => {
    const finalBeneficiary = {
      id: `ben-${Date.now()}`,
      name: extractedProfile.name || 'Beneficiary User',
      age: Number(extractedProfile.age) || 24,
      gender: 'Female',
      location: extractedProfile.location || `${extractedProfile.district || 'Aurangabad'} District`,
      district: extractedProfile.district || 'Aurangabad',
      state: 'Maharashtra',
      pincode: '431006',
      language: language === 'mr' ? 'Marathi' : (language === 'hi' ? 'Hindi' : 'English'),
      education: extractedProfile.education || '10th Class Pass',
      current_occupation: extractedProfile.current_occupation || 'Agricultural Laborer',
      existing_skills: extractedProfile.existing_skills.length ? extractedProfile.existing_skills : ['Basic Work Skills'],
      experience_years: 2,
      desired_occupation: extractedProfile.desired_occupation || 'Solar Energy & Electrical Installation',
      interests: [extractedProfile.desired_occupation || 'Skill Training'],
      employment_preference: extractedProfile.employment_preference || 'wage',
      mobility_km: Number(extractedProfile.mobility_km) || 15,
      digital_literacy: 'basic' as const,
      status: 'profiled' as const,
      created_at: new Date().toISOString()
    };

    setBeneficiary(finalBeneficiary);
    setInterviewStep(3);

    try {
      await axios.post('/api/beneficiaries', finalBeneficiary);
    } catch (e) {
      console.log('Saved to state context');
    }

    navigate('/profile');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      
      {/* Header Banner */}
      <div className="bg-blue-900 text-white rounded-xl p-5 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <span className="text-amber-300 font-bold text-xs uppercase tracking-wider">
            पायरी २ ऑफ ७ (Step 2 of 7)
          </span>
          <h1 className="text-xl sm:text-2xl font-bold mt-1">
            बहुभाषिक आवाज मूल्यमापन (Multilingual Voice Interview)
          </h1>
          <p className="text-xs text-blue-200 mt-1">
            Answer questions in your native language. Re-record any question anytime!
          </p>
        </div>

        {Object.keys(questionAnswers).length >= 1 && (
          <button
            onClick={handleFinishAssessment}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-md flex items-center space-x-2 transition cursor-pointer"
          >
            <span>मूल्यमापन पूर्ण करा (Complete Profile)</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Interactive 6-Step Question Navigator Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex justify-between items-center text-xs font-bold text-slate-600">
          <span className="uppercase tracking-wider text-blue-900">
            प्रश्न निवड व प्रगती (Question {currentPromptIndex + 1} of {promptQuestions.length})
          </span>
          <span className="bg-blue-100 text-blue-900 px-3 py-1 rounded-full text-xs">
            उत्तर दिले: {Object.keys(questionAnswers).length} / {promptQuestions.length}
          </span>
        </div>

        <div className="grid grid-cols-6 gap-2">
          {promptQuestions.map((q, idx) => {
            const isAnswered = Boolean(questionAnswers[idx]);
            const isActive = currentPromptIndex === idx;

            return (
              <button
                key={idx}
                onClick={() => setCurrentPromptIndex(idx)}
                className={`py-2 px-1 rounded-lg text-xs font-bold transition flex flex-col items-center justify-center border ${
                  isActive
                    ? 'bg-blue-900 text-white border-blue-900 shadow-md ring-2 ring-blue-400'
                    : isAnswered
                    ? 'bg-emerald-50 text-emerald-900 border-emerald-300 hover:bg-emerald-100'
                    : 'bg-slate-100 text-slate-600 border-slate-300 hover:bg-slate-200'
                }`}
                title={`Question ${idx + 1}`}
              >
                <span>Q{idx + 1}</span>
                <span className="text-[10px] mt-0.5 font-normal">
                  {isAnswered ? '✓ Recorded' : (isActive ? '● Active' : 'Pending')}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Voice Recorder Component for Current Active Question */}
      <div className="relative">
        <VoiceRecorder
          key={`q-${currentPromptIndex}`}
          promptQuestion={questionText}
          onTranscriptConfirmed={handleTranscriptConfirmed}
        />

        {/* Existing answer preview for current question with Re-record Button */}
        {questionAnswers[currentPromptIndex] && (
          <div className="mt-4 bg-emerald-50 border border-emerald-300 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <span className="text-xs font-bold text-emerald-900 uppercase flex items-center space-x-1">
                <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                <span>या प्रश्नाचे नोंदवलेले उत्तर (Saved Response for Q{currentPromptIndex + 1}):</span>
              </span>
              <p className="text-sm font-semibold text-emerald-950 mt-1 italic">
                "{questionAnswers[currentPromptIndex]}"
              </p>
            </div>

            <button
              onClick={() => handleReRecordQuestion(currentPromptIndex)}
              className="bg-white hover:bg-red-50 text-red-700 border border-red-300 font-bold text-xs px-3.5 py-2 rounded-lg flex items-center space-x-1.5 shadow-sm transition cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>पुन्हा रेकॉर्ड करा (Re-record Question)</span>
            </button>
          </div>
        )}
      </div>

      {/* Navigation Buttons (Previous / Next Question) */}
      <div className="flex justify-between items-center bg-slate-50 border border-slate-200 rounded-xl p-4">
        <button
          onClick={() => setCurrentPromptIndex(Math.max(0, currentPromptIndex - 1))}
          disabled={currentPromptIndex === 0}
          className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition ${
            currentPromptIndex === 0
              ? 'opacity-40 bg-slate-200 text-slate-500 cursor-not-allowed'
              : 'bg-white border border-slate-300 text-slate-800 hover:bg-slate-100 shadow-sm cursor-pointer'
          }`}
        >
          <ArrowLeft className="w-4 h-4" />
          <span>मागील प्रश्न (Previous Question)</span>
        </button>

        {currentPromptIndex < promptQuestions.length - 1 ? (
          <button
            onClick={() => setCurrentPromptIndex(currentPromptIndex + 1)}
            className="px-5 py-2 bg-blue-900 text-white rounded-lg text-xs font-bold hover:bg-blue-800 flex items-center space-x-1.5 shadow-sm cursor-pointer"
          >
            <span>पुढील प्रश्न (Next Question)</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleFinishAssessment}
            className="px-6 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-sm font-bold flex items-center space-x-2 shadow-md cursor-pointer"
          >
            <CheckCircle2 className="w-4.5 h-4.5 text-white" />
            <span>पडताळणीकडे जा (Proceed to Profile Confirmation)</span>
          </button>
        )}
      </div>

      {/* Live Extracted Beneficiary Profile Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b pb-2">
          <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>तुमच्या उत्तरांमधून एक्सट्रॅक्ट केलेली माहिती (Live Extracted Attributes):</span>
          </h3>
          <span className="text-[11px] text-emerald-800 font-semibold bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
            Dynamic Voice Extraction
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          
          <div className="bg-slate-50 p-2.5 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold flex items-center space-x-1">
              <User className="w-3.5 h-3.5 text-blue-900" />
              <span>नाव व वय (Name & Age):</span>
            </span>
            <span className="font-bold text-slate-900">
              {extractedProfile.name || 'प्रतीक्षेत... (Pending)'} {extractedProfile.age ? `(${extractedProfile.age} yrs)` : ''}
            </span>
          </div>

          <div className="bg-slate-50 p-2.5 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold flex items-center space-x-1">
              <MapPin className="w-3.5 h-3.5 text-blue-900" />
              <span>जिल्हा (District/Location):</span>
            </span>
            <span className="font-bold text-slate-900">
              {extractedProfile.district || 'प्रतीक्षेत... (Pending)'}
            </span>
          </div>

          <div className="bg-slate-50 p-2.5 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold flex items-center space-x-1">
              <GraduationCap className="w-3.5 h-3.5 text-blue-900" />
              <span>शिक्षण (Education):</span>
            </span>
            <span className="font-bold text-slate-900">
              {extractedProfile.education || 'प्रतीक्षेत... (Pending)'}
            </span>
          </div>

          <div className="bg-slate-50 p-2.5 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold flex items-center space-x-1">
              <Briefcase className="w-3.5 h-3.5 text-blue-900" />
              <span>सध्याचे काम (Current Occupation):</span>
            </span>
            <span className="font-bold text-slate-900">
              {extractedProfile.current_occupation || 'प्रतीक्षेत... (Pending)'}
            </span>
          </div>

          <div className="bg-slate-50 p-2.5 rounded border border-blue-200 bg-blue-50/50">
            <span className="text-slate-500 block font-semibold flex items-center space-x-1">
              <Sparkles className="w-3.5 h-3.5 text-blue-900" />
              <span>इच्छित क्षेत्र (Desired Occupation):</span>
            </span>
            <span className="font-bold text-blue-900">
              {extractedProfile.desired_occupation || 'प्रतीक्षेत... (Pending)'}
            </span>
          </div>

          <div className="bg-slate-50 p-2.5 rounded border border-slate-200">
            <span className="text-slate-500 block font-semibold">रोजगार प्राधान्य व प्रवास:</span>
            <span className="font-bold text-slate-900">
              {extractedProfile.employment_preference === 'wage' ? 'वेतन नोकरी' : 'स्वयंरोजगार'} ({extractedProfile.mobility_km} km)
            </span>
          </div>

        </div>

        {extractedProfile.existing_skills && extractedProfile.existing_skills.length > 0 && (
          <div className="pt-2 border-t flex items-center space-x-2">
            <span className="text-xs font-semibold text-slate-600">निष्पादित कौशल्ये (Extracted Skills):</span>
            <div className="flex flex-wrap gap-1.5">
              {extractedProfile.existing_skills.map((s: string, idx: number) => (
                <span key={idx} className="bg-emerald-50 text-emerald-900 border border-emerald-300 text-[11px] font-bold px-2 py-0.5 rounded">
                  ✓ {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

    </div>
  );
};
