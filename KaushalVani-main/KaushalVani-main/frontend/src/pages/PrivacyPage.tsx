import React from 'react';
import { ShieldCheck, Lock, HeartHandshake } from 'lucide-react';

export const PrivacyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h1 className="text-2xl font-extrabold text-blue-950 flex items-center space-x-2">
          <ShieldCheck className="w-7 h-7 text-blue-900" />
          <span>गोपनीयता आणि संमती धोरण (Privacy & Voice Consent Policy)</span>
        </h1>
        <p className="text-xs text-slate-600 mt-2">
          KaushalVani collects only minimal information necessary for livelihood decision support under PM-AJAY.
        </p>

        <div className="mt-6 space-y-4 text-xs text-slate-700 leading-relaxed border-t pt-4">
          <h3 className="text-sm font-bold text-slate-900">१. ध्वनी प्रक्रिया संमती (Voice Recording Consent)</h3>
          <p>
            "Your voice is processed solely to understand your skills, education, and livelihood preferences. Audio is transcribed using BHASHINI AI engine."
          </p>

          <h3 className="text-sm font-bold text-slate-900">२. ओळख आणि डेटा सुरक्षा (Identity & Sensitive Data)</h3>
          <p>
            We DO NOT collect sensitive identity documents, bank details, or Aadhaar numbers in this prototype.
          </p>
        </div>
      </div>
    </div>
  );
};
