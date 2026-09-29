import React from 'react';
import { useLanguage, SupportedLanguage } from '../context/LanguageContext';
import { VolumeX, Eye, Languages } from 'lucide-react';

export const AccessibilityToolbar: React.FC = () => {
  const {
    language,
    setLanguage,
    textSize,
    setTextSize,
    highContrast,
    toggleHighContrast,
    isSpeaking,
    stopSpeech
  } = useLanguage();

  return (
    <div className="bg-slate-800 text-white text-xs py-1.5 px-3 sm:px-4 shadow-inner flex flex-wrap items-center justify-between gap-2 border-b border-slate-700">
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <span className="font-semibold text-slate-300 hidden lg:inline">Accessibility Options:</span>
        
        {/* Text Sizing */}
        <div className="flex items-center bg-slate-700 rounded px-1 py-0.5 space-x-1" role="group" aria-label="Text Size Controls">
          <button
            onClick={() => setTextSize('normal')}
            className={`px-2 py-0.5 rounded text-xs font-bold transition ${textSize === 'normal' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:text-white'}`}
            title="Standard Text Size"
          >
            A
          </button>
          <button
            onClick={() => setTextSize('large')}
            className={`px-2 py-0.5 rounded text-xs font-bold transition ${textSize === 'large' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:text-white'}`}
            title="Large Text Size"
          >
            A+
          </button>
          <button
            onClick={() => setTextSize('xlarge')}
            className={`px-2 py-0.5 rounded text-xs font-bold transition ${textSize === 'xlarge' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:text-white'}`}
            title="Extra Large Text Size"
          >
            A++
          </button>
        </div>

        {/* High Contrast */}
        <button
          onClick={toggleHighContrast}
          className={`flex items-center space-x-1 px-2.5 py-0.5 rounded font-medium border transition ${
            highContrast ? 'bg-yellow-400 text-black border-yellow-400' : 'bg-slate-700 text-slate-200 border-slate-600 hover:bg-slate-600'
          }`}
          title="Toggle High Contrast Theme"
        >
          <Eye className="w-3.5 h-3.5" />
          <span className="text-[11px] sm:text-xs">{highContrast ? 'Contrast ON' : 'High Contrast'}</span>
        </button>

        {/* Stop Speech */}
        {isSpeaking && (
          <button
            onClick={stopSpeech}
            className="flex items-center space-x-1 bg-red-600 text-white px-2 py-0.5 rounded hover:bg-red-700 text-xs"
            title="Stop Audio Reading"
          >
            <VolumeX className="w-3.5 h-3.5" />
            <span>Stop Audio</span>
          </button>
        )}
      </div>

      {/* Language Selector */}
      <div className="flex items-center space-x-1.5 ml-auto sm:ml-0">
        <Languages className="w-3.5 h-3.5 text-blue-300" />
        <span className="text-slate-300 font-medium hidden md:inline text-xs">Language:</span>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
          className="bg-slate-900 border border-slate-600 text-white text-xs rounded px-2 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-400 font-semibold"
          aria-label="Select Preferred Language"
        >
          <option value="mr">मराठी (Marathi)</option>
          <option value="hi">हिंदी (Hindi)</option>
          <option value="en">English</option>
        </select>
      </div>
    </div>
  );
};
