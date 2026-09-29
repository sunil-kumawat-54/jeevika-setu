import React from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-slate-900 text-slate-300 border-t-4 border-amber-500 text-xs mt-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          
          {/* Brand Info with Official Logo */}
          <div className="space-y-3 md:col-span-1">
            <div className="h-10 overflow-hidden bg-white/10 p-1.5 rounded inline-block">
              <img src="/logo.png" alt="कौशलवाणी KaushalVani Logo" className="h-full object-contain" />
            </div>
            <p className="text-slate-400 text-xs leading-relaxed">
              PM-AJAY Grant-in-Aid (GIA) component aligned AI Multilingual Voice Livelihood Decision-Support Platform.
            </p>
            <p className="text-amber-400 text-[11px] font-semibold">
              "Your Voice. Your Skills. Your Livelihood Path."
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-3">
              महत्वाच्या लिंक्स (Important Links)
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/" className="hover:text-white transition">गृहपृष्ठ (Home)</Link>
              </li>
              <li>
                <Link to="/assessment" className="hover:text-white transition">ध्वनी मूल्यांकन (Voice Assessment)</Link>
              </li>
              <li>
                <Link to="/roadmap" className="hover:text-white transition">उपजीविका रोडमॅप (Livelihood Roadmap)</Link>
              </li>
              <li>
                <Link to="/training" className="hover:text-white transition">प्रशिक्षण केंद्रे (Training Centres)</Link>
              </li>
            </ul>
          </div>

          {/* Official References */}
          <div>
            <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-3">
              अधिकृत स्रोत (Official Sources)
            </h4>
            <ul className="space-y-2 text-slate-400">
              <li className="flex items-center space-x-1 hover:text-white transition">
                <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
                <a href="https://pmajay.gov.in" target="_blank" rel="noreferrer">PM-AJAY Scheme Portal</a>
              </li>
              <li className="flex items-center space-x-1 hover:text-white transition">
                <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
                <a href="https://nqr.gov.in" target="_blank" rel="noreferrer">National Qualification Register (NQR)</a>
              </li>
              <li className="flex items-center space-x-1 hover:text-white transition">
                <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
                <a href="https://skillindia.gov.in" target="_blank" rel="noreferrer">Skill India Digital</a>
              </li>
              <li className="flex items-center space-x-1 hover:text-white transition">
                <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
                <a href="https://ncs.gov.in" target="_blank" rel="noreferrer">National Career Service (NCS)</a>
              </li>
              <li className="flex items-center space-x-1 hover:text-white transition">
                <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
                <a href="https://bhashini.gov.in" target="_blank" rel="noreferrer">BHASHINI AI Speech Engine</a>
              </li>
            </ul>
          </div>

          {/* Compliance & Accessibility */}
          <div>
            <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-3">
              गुपिते व प्रवेशक्षमता (Privacy & Standards)
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/privacy" className="hover:text-white transition">गोपनीयता आणि संमती (Privacy & Consent)</Link>
              </li>
              <li>
                <Link to="/data-sources" className="hover:text-white transition">पारदर्शक डेटा स्रोत (Data Sources Quality)</Link>
              </li>
              <li className="text-slate-400 pt-1">
                UX4G & GIGW Accessibility Compliant. Screen Reader Ready.
              </li>
            </ul>
          </div>

        </div>

        <div className="mt-8 pt-4 border-t border-slate-800 text-center text-slate-500 text-[11px] flex flex-wrap justify-between items-center">
          <p>© 2026 KaushalVani. Smart India Hackathon / PM-AJAY AI Livelihood MVP.</p>
          <p>Designed for low-literacy, voice-first regional beneficiary empowerment.</p>
        </div>
      </div>
    </footer>
  );
};
