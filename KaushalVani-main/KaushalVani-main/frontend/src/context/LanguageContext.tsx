import React, { createContext, useContext, useState, useEffect } from 'react';

export type SupportedLanguage = 'mr' | 'hi' | 'en';
export type TextSize = 'normal' | 'large' | 'xlarge';

interface Translations {
  [key: string]: {
    [lang in SupportedLanguage]: string;
  };
}

export const dictionary: Translations = {
  brandTitle: {
    mr: 'कौशलवाणी',
    hi: 'कौशलवाणी',
    en: 'KaushalVani'
  },
  tagline: {
    mr: 'तुमचा आवाज. तुमचे कौशल्य. तुमचा उपजीविकेचा मार्ग.',
    hi: 'आपकी आवाज़। आपकी कुशलता। आपका आजीविका पथ।',
    en: 'Your Voice. Your Skills. Your Livelihood Path.'
  },
  subtagline: {
    mr: 'पीएम-अजय (PM-AJAY) योजनेअंतर्गत आपल्या भाषेत बोलून योग्य कौशल्य, प्रशिक्षण आणि स्थानिक रोजगार मिळवा.',
    hi: 'पीएम-अजय (PM-AJAY) योजना के तहत अपनी भाषा में बोलकर सही कौशल, प्रशिक्षण और स्थानीय रोजगार खोजें।',
    en: 'PM-AJAY Livelihood Assistant — Speak naturally to discover suitable NSQF skills, accredited training centres, and local employment around you.'
  },
  startVoiceAssessment: {
    mr: 'ध्वनी मूल्यांकन सुरू करा',
    hi: 'ध्वनि मूल्यांकन शुरू करें',
    en: 'Start Voice Assessment'
  },
  exploreOpportunities: {
    mr: 'रोजगार व उद्योग शोधा',
    hi: 'अवसर और उद्योग खोजें',
    en: 'Explore Opportunities'
  },
  forBeneficiaries: {
    mr: 'लाभार्थ्यांसाठी',
    hi: 'लाभार्थियों के लिए',
    en: 'For Beneficiaries'
  },
  forOfficials: {
    mr: 'शासकीय अधिकाऱ्यांसाठी',
    hi: 'अधिकारियों के लिए',
    en: 'For Officials'
  },
  home: {
    mr: 'गृहपृष्ठ',
    hi: 'मुख्य पृष्ठ',
    en: 'Home'
  },
  voiceAssessment: {
    mr: 'ध्वनी मुलाखत',
    hi: 'ध्वनि साक्षात्कार',
    en: 'Voice Assessment'
  },
  livelihoodRoadmap: {
    mr: 'उपजीविका मार्ग',
    hi: 'आजीविका पथ',
    en: 'Livelihood Roadmap'
  },
  trainingCentres: {
    mr: 'प्रशिक्षण केंद्रे',
    hi: 'प्रशिक्षण केंद्र',
    en: 'Training Centres'
  },
  opportunities: {
    mr: 'रोजगार / उद्योग',
    hi: 'अवसर व उद्योग',
    en: 'Opportunities'
  },
  officialDashboard: {
    mr: 'शासकीय डॅशबोर्ड',
    hi: 'शासकीय डैशबोर्ड',
    en: 'Official Dashboard'
  },
  dataSources: {
    mr: 'डेटा स्रोत',
    hi: 'डेटा स्रोत',
    en: 'Data Sources'
  },
  schemeBanner: {
    mr: 'प्रधानमंत्री अनुसूचित जाति अभ्युदय योजना (PM-AJAY) — अनुदान (Grant-in-Aid) उपजीविका सहाय्यक प्रणाली',
    hi: 'प्रधानमंत्री अनुसूचित जाति अभ्युदय योजना (PM-AJAY) — अनुदान (Grant-in-Aid) आजीविका सहायक प्रणाली',
    en: 'Pradhan Mantri Anusuchit Jaati Abhyuday Yojana (PM-AJAY) — Grant-in-Aid Livelihood Platform'
  },
  multilingualAI: {
    mr: 'बहुभाषी ध्वनी-आधारित सहाय्यक',
    hi: 'बहुभाषी ध्वनि-आधारित सहायक',
    en: 'Multilingual Voice AI Assistant'
  },
  selectLanguage: {
    mr: 'तुमची आवडती भाषा निवडा:',
    hi: 'अपनी पसंदीदा भाषा चुनें:',
    en: 'Select Preferred Language:'
  },
  demoPersonaBtn: {
    mr: 'प्राथमिक प्रात्यक्षिक (डेमो: सीता)',
    hi: 'प्राथमिक प्रदर्शन (डेमो: सीता)',
    en: 'Primary Demonstration (Demo Persona: Sita)'
  },
  noTypingRequired: {
    mr: '* कोणतीही फॉर्म भरण्याची किंवा टाईप करण्याची गरज नाही. फक्त मायक्रोफोन वापरून बोला.',
    hi: '* कोई फ़ॉर्म भरने या टाइप करने की आवश्यकता नहीं है। केवल बोलें।',
    en: '* No long form filling or typing required. Simply speak using your device microphone.'
  },
  publicServiceSys: {
    mr: 'शासकीय उपजीविका सहाय्य प्रणाली',
    hi: 'शासकीय आजीविका सहायता प्रणाली',
    en: 'Public Livelihood Decision-Support System'
  },
  nsqfNqrConnected: {
    mr: 'राष्ट्रीय कौशल्य पात्रता आराखडा (NSQF) आणि राष्ट्रीय पात्रता नोंदणी (NQR) शी थेट जोडलेली सिस्टीम.',
    hi: 'राष्ट्रीय कौशल योग्यता ढांचा (NSQF) और राष्ट्रीय योग्यता रजिस्टर (NQR) से जुड़ी प्रणाली।',
    en: 'Directly integrated with National Qualifications Register (NQR) and NSQF qualification standards.'
  },
  journeyTitle: {
    mr: 'कौशलवाणी उपजीविका प्रवास',
    hi: 'कौशलवाणी आजीविका यात्रा',
    en: 'KaushalVani Beneficiary Livelihood Journey'
  },
  step1Title: {
    mr: '१. बोलून प्रोफाईल नोंदणी',
    hi: '१. बोलकर प्रोफाइल पंजीकरण',
    en: '1. Voice Profile Capture'
  },
  step1Desc: {
    mr: 'आपल्या भाषेत सध्याचे काम, शिक्षण आणि इच्छित क्षेत्राबद्दल नैसर्गिकरीत्या बोला.',
    hi: 'अपनी भाषा में वर्तमान कार्य, शिक्षा और वांछित क्षेत्र के बारे में स्वाभाविक रूप से बोलें।',
    en: 'Speak naturally in your preferred language about current work, education, and skills.'
  },
  step2Title: {
    mr: '२. कौशल्य फरक विश्लेषण',
    hi: '२. कौशल अंतर विश्लेषण',
    en: '2. AI Skill Gap Analysis'
  },
  step2Desc: {
    mr: 'NSQF/NQR राष्ट्रीय मानकांनुसार आवश्यक कौशल्यांचे पारदर्शक मूल्यमापन.',
    hi: 'NSQF/NQR राष्ट्रीय मानकों के अनुसार आवश्यक कौशलों का पारदर्शी मूल्यांकन।',
    en: 'Transparent skill matrix gap evaluation aligned with official NSQF qualification standards.'
  },
  step3Title: {
    mr: '३. जवळची प्रशिक्षण केंद्रे',
    hi: '३. नजदीकी प्रशिक्षण केंद्र',
    en: '3. Nearby Training Centres'
  },
  step3Desc: {
    mr: 'प्रवासाच्या मर्यादेनुसार जवळच्या मान्यताप्राप्त ITI किंवा स्किल सेंटरची निवड.',
    hi: 'यात्रा सीमा के अनुसार नजदीकी मान्यता प्राप्त ITI या स्किल सेंटर का चयन।',
    en: 'Geospatial radius matching for accredited Government ITIs & Skill India Digital centres.'
  },
  step4Title: {
    mr: '४. वैयक्तिकृत उपजीविका मार्ग',
    hi: '४. व्यक्तिगत आजीविका पथ',
    en: '4. Personalized Livelihood Roadmap'
  },
  step4Desc: {
    mr: 'वेतन रोजगार किंवा स्वयंरोजगार मायक्रो-एंटरप्राइजसाठी स्पष्ट मार्गदर्शक नकाशा.',
    hi: 'वेतन रोजगार या स्व-रोजगार माइक्रो-एंटरप्राइज के लिए स्पष्ट मार्गदर्शक नक्शा।',
    en: 'Actionable 7-step roadmap linking training to verified wage placement and enterprise grants.'
  },
  accessibilityOptions: {
    mr: 'प्रवेशक्षमता पर्याय:',
    hi: 'सुलभता विकल्प:',
    en: 'Accessibility Options:'
  },
  highContrast: {
    mr: 'उच्च कॉन्ट्रास्ट',
    hi: 'उच्च कंट्रास्ट',
    en: 'High Contrast'
  },
  highContrastOn: {
    mr: 'उच्च कॉन्ट्रास्ट चालू',
    hi: 'उच्च कंट्रास्ट चालू',
    en: 'High Contrast ON'
  },
  stopAudio: {
    mr: 'आवाज थांबवा',
    hi: 'ऑडियो रोकें',
    en: 'Stop Audio'
  },
  typeInstead: {
    mr: 'टाइप करून उत्तर द्या',
    hi: 'टाइप करके उत्तर दें',
    en: 'Type response instead'
  }
};

interface LanguageContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  textSize: TextSize;
  setTextSize: (size: TextSize) => void;
  highContrast: boolean;
  toggleHighContrast: () => void;
  isSpeaking: boolean;
  speakText: (text: string) => void;
  stopSpeech: () => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<SupportedLanguage>('mr');
  const [textSize, setTextSize] = useState<TextSize>('normal');
  const [highContrast, setHighContrast] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('font-large', 'font-xlarge');
    if (textSize === 'large') root.classList.add('font-large');
    if (textSize === 'xlarge') root.classList.add('font-xlarge');
  }, [textSize]);

  useEffect(() => {
    if (highContrast) {
      document.body.classList.add('high-contrast');
    } else {
      document.body.classList.remove('high-contrast');
    }
  }, [highContrast]);

  const toggleHighContrast = () => setHighContrast(!highContrast);

  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      if (language === 'mr') utterance.lang = 'mr-IN';
      else if (language === 'hi') utterance.lang = 'hi-IN';
      else utterance.lang = 'en-IN';

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    }
  };

  const stopSpeech = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  const t = (key: string): string => {
    if (dictionary[key] && dictionary[key][language]) {
      return dictionary[key][language];
    }
    return key;
  };

  return (
    <LanguageContext.Provider value={{
      language,
      setLanguage,
      textSize,
      setTextSize,
      highContrast,
      toggleHighContrast,
      isSpeaking,
      speakText,
      stopSpeech,
      t
    }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
};
