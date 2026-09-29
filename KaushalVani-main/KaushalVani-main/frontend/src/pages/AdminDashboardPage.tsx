import React, { useState, useEffect } from 'react';
import { ShieldCheck, Filter, Users, Award, Building2, Briefcase, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';
import axios from 'axios';

export const AdminDashboardPage: React.FC = () => {
  const [selectedDistrict, setSelectedDistrict] = useState<string>('All');
  const [selectedGender, setSelectedGender] = useState<string>('All');
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [beneficiaries, setBeneficiaries] = useState<any[]>([]);

  useEffect(() => {
    fetchAnalytics();
  }, [selectedDistrict, selectedGender]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const res = await axios.get('/api/admin/dashboard', {
        params: { district: selectedDistrict, gender: selectedGender }
      });
      if (res.data) {
        setDashboardData(res.data);
      }
      const bRes = await axios.get('/api/beneficiaries');
      if (bRes.data && bRes.data.beneficiaries) {
        setBeneficiaries(bRes.data.beneficiaries);
      }
    } catch (err) {
      console.log('Error fetching dashboard analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (bId: string, newStatus: string) => {
    try {
      await axios.patch(`/api/outcomes/${bId}`, { employment_status: newStatus });
      fetchAnalytics();
    } catch (err) {
      console.log('Error updating outcome');
    }
  };

  const summary = dashboardData?.summary || {
    totalBeneficiaries: 500,
    profiledCount: 500,
    analyzedCount: 412,
    enrolledCount: 320,
    placedCount: 185,
    selfEmployedCount: 94,
    dropoutsCount: 12,
    successRate: 87
  };

  const funnelData = dashboardData?.funnelData || [
    { stage: 'Voice Profiled', count: 500, percentage: 100 },
    { stage: 'Skill Gap Analyzed', count: 412, percentage: 82 },
    { stage: 'Training Enrolled', count: 320, percentage: 64 },
    { stage: 'Wage Placed', count: 185, percentage: 37 },
    { stage: 'Micro-Enterprise Self-Employed', count: 94, percentage: 19 }
  ];

  const sectorDemand = dashboardData?.sectorDemand || [
    { sector: 'Solar Energy & Electrical', beneficiaries: 145 },
    { sector: 'Garment & Apparel Tailoring', beneficiaries: 110 },
    { sector: 'Auto Mechanic & Repair', beneficiaries: 85 },
    { sector: 'Healthcare Assistant (GDA)', beneficiaries: 75 },
    { sector: 'Organic Agriculture & Bio-Inputs', beneficiaries: 55 },
    { sector: 'IT & Data Entry Operations', beneficiaries: 30 }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      
      {/* Top Banner */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-md flex flex-wrap items-center justify-between gap-4 border-b-4 border-amber-500">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-6 h-6 text-amber-400" />
            <span className="text-amber-400 text-xs font-bold uppercase tracking-wider">
              PM-AJAY GIA District Official Portal
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold mt-1">
            शासकीय उपजीविका डॅशबोर्ड (Administrator Dashboard)
          </h1>
          <p className="text-xs text-slate-300 mt-1">
            Monitoring Beneficiary Funnel, Skill Gap Metrics, Training Enrollments, & Placement Outcomes.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 bg-slate-800 p-3 rounded-xl border border-slate-700 text-xs">
          <Filter className="w-4 h-4 text-amber-400" />
          <div>
            <span className="text-slate-400 block font-semibold">जिल्हा (District):</span>
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="bg-slate-900 border border-slate-600 text-white rounded px-2.5 py-1 font-semibold focus:ring-1 focus:ring-amber-400"
            >
              <option value="All">All Districts</option>
              <option value="Aurangabad">Aurangabad (Sambhajinagar)</option>
              <option value="Jalna">Jalna</option>
              <option value="Nanded">Nanded</option>
              <option value="Latur">Latur</option>
            </select>
          </div>

          <div>
            <span className="text-slate-400 block font-semibold">लिंग (Gender):</span>
            <select
              value={selectedGender}
              onChange={(e) => setSelectedGender(e.target.value)}
              className="bg-slate-900 border border-slate-600 text-white rounded px-2.5 py-1 font-semibold focus:ring-1 focus:ring-amber-400"
            >
              <option value="All">All Genders</option>
              <option value="Female">Female</option>
              <option value="Male">Male</option>
            </select>
          </div>
        </div>
      </div>

      {/* Synthetic Data Disclaimer */}
      <div className="bg-amber-50 border border-amber-300 p-3 rounded-lg text-xs font-semibold text-amber-950 flex items-center space-x-2">
        <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0" />
        <span>Note: Dashboard analytics combine live beneficiary records with verified synthetic PM-AJAY beneficiary demo cohort data (500 records).</span>
      </div>

      {/* Metric Cards (KPI Summary) */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        
        <div className="bg-white border-2 border-slate-300 rounded-xl p-4 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase block">Total Profiled</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-blue-950 mt-1 block">{summary.totalBeneficiaries}</span>
          <span className="text-[10px] text-emerald-700 font-semibold">100% Voice Interviewed</span>
        </div>

        <div className="bg-white border-2 border-slate-300 rounded-xl p-4 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase block">Analyzed</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-blue-900 mt-1 block">{summary.analyzedCount}</span>
          <span className="text-[10px] text-slate-600 font-semibold">NSQF Mapped</span>
        </div>

        <div className="bg-white border-2 border-slate-300 rounded-xl p-4 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase block">Enrolled</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-amber-600 mt-1 block">{summary.enrolledCount}</span>
          <span className="text-[10px] text-amber-800 font-semibold">In Accredited ITIs</span>
        </div>

        <div className="bg-white border-2 border-slate-300 rounded-xl p-4 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase block">Wage Placed</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-emerald-700 mt-1 block">{summary.placedCount}</span>
          <span className="text-[10px] text-emerald-800 font-semibold">Verified NCS Jobs</span>
        </div>

        <div className="bg-white border-2 border-slate-300 rounded-xl p-4 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase block">Self-Employed</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-purple-700 mt-1 block">{summary.selfEmployedCount}</span>
          <span className="text-[10px] text-purple-800 font-semibold">PM-AJAY GIA Grants</span>
        </div>

        <div className="bg-white border-2 border-slate-300 rounded-xl p-4 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase block">Success Rate</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-emerald-700 mt-1 block">{summary.successRate}%</span>
          <span className="text-[10px] text-slate-500 font-semibold">Placement / Enterprise</span>
        </div>

      </div>

      {/* Visual Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Chart 1: Beneficiary Funnel Progress */}
        <div className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">
            १. लाभार्थी प्रगती फनेल (Beneficiary Progression Funnel)
          </h3>

          <div className="space-y-3">
            {funnelData.map((f: any, idx: number) => (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between text-xs font-bold text-slate-800">
                  <span>{f.stage}</span>
                  <span>{f.count} ({f.percentage}%)</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-4 overflow-hidden border">
                  <div
                    className="bg-blue-900 h-full rounded-full transition-all duration-500"
                    style={{ width: `${f.percentage}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Chart 2: Sector Demand Distribution */}
        <div className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider border-b pb-2">
            २. क्षेत्रनिहाय मागणी (Sector Aspiration Demand)
          </h3>

          <div className="space-y-2.5">
            {sectorDemand.map((sec: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between bg-slate-50 p-2.5 rounded border text-xs">
                <span className="font-bold text-slate-900">{sec.sector}</span>
                <span className="bg-blue-100 text-blue-900 border border-blue-300 font-extrabold px-2.5 py-0.5 rounded">
                  {sec.beneficiaries} Beneficiaries
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Beneficiary Outcome Tracking Table */}
      <div className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b pb-3">
          <h3 className="text-base font-bold text-slate-900">
            लाभार्थी यादी आणि उपजीविका स्थिती (Beneficiary Cohort & Outcome Management)
          </h3>
          <span className="text-xs text-slate-500 font-medium">Showing top 10 recent records</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100 border-b border-slate-300 text-slate-700 font-bold uppercase">
                <th className="p-3">ID / Name</th>
                <th className="p-3">District</th>
                <th className="p-3">Education</th>
                <th className="p-3">Desired Skill</th>
                <th className="p-3">Status</th>
                <th className="p-3 text-right">Officer Action</th>
              </tr>
            </thead>
            <tbody className="divide-y border-b">
              {beneficiaries.slice(0, 8).map((b: any) => (
                <tr key={b.id} className="hover:bg-slate-50">
                  <td className="p-3 font-bold text-slate-900">
                    {b.name} ({b.age}y, {b.gender})
                  </td>
                  <td className="p-3">{b.district}</td>
                  <td className="p-3">{b.education}</td>
                  <td className="p-3 font-bold text-blue-900">{b.desired_occupation}</td>
                  <td className="p-3">
                    <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold border ${
                      b.status === 'placed' ? 'bg-emerald-100 text-emerald-900 border-emerald-300' :
                      (b.status === 'enrolled' ? 'bg-amber-100 text-amber-900 border-amber-300' : 'bg-blue-100 text-blue-900 border-blue-300')
                    }`}>
                      {b.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => handleStatusUpdate(b.id, 'Wage Employed')}
                      className="bg-blue-900 hover:bg-blue-800 text-white font-bold text-[11px] px-3 py-1 rounded"
                    >
                      Update Placed
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
