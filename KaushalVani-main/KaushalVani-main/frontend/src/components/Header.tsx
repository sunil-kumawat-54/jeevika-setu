import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AccessibilityToolbar } from './AccessibilityToolbar';
import { useLanguage } from '../context/LanguageContext';
import { Mic, ShieldCheck, Menu, X } from 'lucide-react';

export const Header: React.FC = () => {
  const { t } = useLanguage();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { path: '/', label: t('home') },
    { path: '/assessment', label: t('voiceAssessment') },
    { path: '/roadmap', label: t('livelihoodRoadmap') },
    { path: '/training', label: t('trainingCentres') },
    { path: '/opportunities', label: t('opportunities') },
    { path: '/admin', label: t('officialDashboard') },
    { path: '/data-sources', label: t('dataSources') },
  ];

  return (
    <header className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-40">
      {/* Top Accessibility Bar */}
      <AccessibilityToolbar />

      {/* Main Banner & Logo */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center justify-between">
        
        <Link to="/" className="flex items-center space-x-2 sm:space-x-3 group">
          {/* Logo Banner */}
          <div className="h-10 sm:h-12 md:h-14 overflow-hidden flex items-center">
            <img
              src="/logo.png"
              alt="KaushalVani Logo"
              className="h-full object-contain hover:opacity-95 transition"
            />
          </div>
          <span className="hidden xl:inline bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-semibold px-2 py-0.5 rounded">
            PM-AJAY GIA AI Portal
          </span>
        </Link>

        {/* Action Buttons & Mobile Toggle */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          
          <Link
            to="/admin"
            className="hidden sm:flex items-center space-x-1.5 text-xs font-semibold text-blue-900 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3 py-1.5 rounded-md transition"
          >
            <ShieldCheck className="w-4 h-4 text-blue-700" />
            <span>{t('forOfficials')}</span>
          </Link>

          <Link
            to="/assessment"
            className="flex items-center space-x-1.5 text-xs sm:text-sm font-bold text-white bg-blue-900 hover:bg-blue-800 px-3 sm:px-4 py-1.5 sm:py-2 rounded-md shadow-sm transition"
          >
            <Mic className="w-4 h-4 text-amber-300 animate-pulse" />
            <span>{t('startVoiceAssessment')}</span>
          </Link>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-slate-700 hover:text-blue-900 rounded-md hover:bg-slate-100 border border-slate-200"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Desktop Navigation Links */}
      <nav className="hidden md:block bg-slate-100 border-t border-slate-200 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex space-x-6 overflow-x-auto text-xs sm:text-sm font-medium py-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`pb-0.5 border-b-2 transition whitespace-nowrap ${
                isActive(item.path) ? 'border-blue-900 text-blue-900 font-bold' : 'border-transparent text-slate-600 hover:text-blue-900'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </nav>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-100 border-t border-slate-200 px-4 py-3 space-y-2 shadow-inner">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setMobileMenuOpen(false)}
              className={`block py-2 px-3 rounded-md text-sm font-semibold transition ${
                isActive(item.path) ? 'bg-blue-900 text-white font-bold' : 'text-slate-800 hover:bg-slate-200'
              }`}
            >
              {item.label}
            </Link>
          ))}
          <div className="pt-2 border-t border-slate-200 flex justify-between">
            <Link
              to="/admin"
              onClick={() => setMobileMenuOpen(false)}
              className="text-xs font-semibold text-blue-900 flex items-center space-x-1"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>{t('forOfficials')}</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
