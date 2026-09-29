import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBeneficiary } from '../context/BeneficiaryContext';
import { Building2, MapPin, ArrowRight, Filter } from 'lucide-react';

export const TrainingOptionsPage: React.FC = () => {
  const { beneficiary } = useBeneficiary();
  const navigate = useNavigate();

  const userName = beneficiary?.name || 'Beneficiary User';
  const userDistrict = beneficiary?.district || 'Chhatrapati Sambhajinagar';
  const userMobility = beneficiary?.mobility_km || 15;
  const desiredRole = beneficiary?.desired_occupation || 'Vocational & Technical Training';

  const [selectedRadius, setSelectedRadius] = useState<number>(userMobility);

  const trainingCentres = [
    {
      id: 'tc-101',
      provider_name: `PMKVK Government ITI ${userDistrict}`,
      centre_name: `${userDistrict} Skill Training Hub`,
      district: `${userDistrict} District`,
      address: `Industrial Area Sector 2, ${userDistrict} - 431006`,
      contact_phone: '+91 240 2484920',
      contact_email: `iti.${userDistrict.toLowerCase()}@dvet.gov.in`,
      distance_km: 8.4,
      batch_start: '15th October 2026',
      stipend_support: 'Eligible for PM-AJAY GIA Stipend Support'
    },
    {
      id: 'tc-103',
      provider_name: 'MSSDS Vocational Training Institute',
      centre_name: 'Regional Vocational Skill Academy',
      district: `${userDistrict} District`,
      address: `Sector 3 Skill Zone, ${userDistrict}`,
      contact_phone: '+91 240 2554099',
      contact_email: 'info@skillacademy.org.in',
      distance_km: 12.1,
      batch_start: '01st November 2026',
      stipend_support: 'Hostel Accommodation & Tool Kit Support'
    },
    {
      id: 'tc-104',
      provider_name: 'Rural Self Employment Training Institute (RSETI)',
      centre_name: 'Bank RSETI Centre',
      district: 'Jalna',
      address: 'Devalgaon Raja Road, Jalna - 431203',
      contact_phone: '+91 2482 220199',
      contact_email: 'rseti.jalna@mahabank.co.in',
      distance_km: 34.5,
      batch_start: '10th November 2026',
      stipend_support: 'Free Micro-grant Loan Assistance'
    }
  ];

  const filteredCentres = trainingCentres.filter(c => c.distance_km <= selectedRadius);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      
      {/* Title */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="text-blue-900 font-bold text-xs uppercase tracking-wider bg-blue-100 px-2.5 py-0.5 rounded">
            Geospatial Proximity Matching ({userDistrict})
          </span>
          <h1 className="text-2xl font-extrabold text-blue-950 mt-1">
            {userName} साठी मान्यताप्राप्त प्रशिक्षण केंद्रे (Training Centres)
          </h1>
          <p className="text-xs text-slate-600 mt-1">
            Nearest ITI & Skill India centres offering {desiredRole} near {userDistrict}.
          </p>
        </div>

        {/* Distance Radius Filter */}
        <div className="flex items-center space-x-2 bg-slate-50 border border-slate-300 p-2 rounded-lg">
          <Filter className="w-4 h-4 text-slate-600" />
          <span className="text-xs font-bold text-slate-700">प्रवास मर्यादा:</span>
          <select
            value={selectedRadius}
            onChange={(e) => setSelectedRadius(Number(e.target.value))}
            className="bg-white border border-slate-300 rounded text-xs font-bold px-2.5 py-1 focus:ring-2 focus:ring-blue-900"
          >
            <option value={5}>5 km</option>
            <option value={10}>10 km</option>
            <option value={15}>15 km (Preferred)</option>
            <option value={25}>25 km</option>
            <option value={50}>50 km</option>
          </select>
        </div>
      </div>

      {/* List of Training Centres */}
      <div className="space-y-4">
        {filteredCentres.map((tc) => (
          <div key={tc.id} className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm space-y-4 hover:border-blue-900 transition">
            <div className="flex flex-wrap items-start justify-between gap-2 border-b pb-3">
              <div>
                <span className="text-[11px] font-bold text-blue-900 uppercase tracking-wider">
                  {tc.provider_name}
                </span>
                <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                  {tc.centre_name}
                </h3>
              </div>
              <span className="bg-emerald-100 text-emerald-900 border border-emerald-300 font-extrabold text-xs px-3 py-1 rounded-full flex items-center space-x-1">
                <MapPin className="w-3.5 h-3.5" />
                <span>{tc.distance_km} km away</span>
              </span>
            </div>

            <p className="text-xs text-slate-700 font-medium flex items-center space-x-1.5">
              <MapPin className="w-4 h-4 text-slate-500 flex-shrink-0" />
              <span>{tc.address}</span>
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded border">
              <div>
                <span className="text-slate-500 block font-semibold">फोन क्र. (Phone):</span>
                <span className="font-bold text-slate-900">{tc.contact_phone}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-semibold">नवीन बॅच (Next Batch):</span>
                <span className="font-bold text-blue-900">{tc.batch_start}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-semibold">विशेष सवलत (Scholarship):</span>
                <span className="font-bold text-emerald-800">{tc.stipend_support}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Action Button */}
      <div className="border-t pt-4 flex justify-between items-center">
        <button
          onClick={() => navigate('/recommendations')}
          className="text-xs font-semibold text-slate-700 hover:text-slate-900"
        >
          ← मागे जा (Back to Recommendations)
        </button>

        <button
          onClick={() => navigate('/opportunities')}
          className="bg-blue-900 hover:bg-blue-800 text-white font-bold text-base px-6 py-3 rounded-lg shadow-sm flex items-center space-x-2 transition cursor-pointer"
        >
          <span>रोजगार आणि उद्योग मार्ग पहा (View Opportunities & Enterprise)</span>
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>

    </div>
  );
};
