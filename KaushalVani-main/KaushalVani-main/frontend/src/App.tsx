import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { BeneficiaryProvider } from './context/BeneficiaryContext';
import { Header } from './components/Header';
import { Footer } from './components/Footer';

import { LandingPage } from './pages/LandingPage';
import { AssessmentPage } from './pages/AssessmentPage';
import { ProfileConfirmationPage } from './pages/ProfileConfirmationPage';
import { SkillGapPage } from './pages/SkillGapPage';
import { RecommendationsPage } from './pages/RecommendationsPage';
import { TrainingOptionsPage } from './pages/TrainingOptionsPage';
import { OpportunitiesPage } from './pages/OpportunitiesPage';
import { RoadmapPage } from './pages/RoadmapPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { PrivacyPage } from './pages/PrivacyPage';

export const App: React.FC = () => {
  return (
    <LanguageProvider>
      <BeneficiaryProvider>
        <Router>
          <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
            <Header />
            <main className="flex-1">
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/assessment" element={<AssessmentPage />} />
                <Route path="/profile" element={<ProfileConfirmationPage />} />
                <Route path="/skill-gap" element={<SkillGapPage />} />
                <Route path="/recommendations" element={<RecommendationsPage />} />
                <Route path="/training" element={<TrainingOptionsPage />} />
                <Route path="/opportunities" element={<OpportunitiesPage />} />
                <Route path="/roadmap" element={<RoadmapPage />} />
                <Route path="/admin" element={<AdminDashboardPage />} />
                <Route path="/data-sources" element={<DataSourcesPage />} />
                <Route path="/privacy" element={<PrivacyPage />} />
              </Routes>
            </main>
            <Footer />
          </div>
        </Router>
      </BeneficiaryProvider>
    </LanguageProvider>
  );
};

export default App;
