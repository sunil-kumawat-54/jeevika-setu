import React, { useState, useEffect } from 'react';
import { Database, ExternalLink, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import axios from 'axios';

export const DataSourcesPage: React.FC = () => {
  const [sources, setSources] = useState<any[]>([]);

  useEffect(() => {
    axios.get('/api/admin/sources').then(res => {
      if (res.data && res.data.dataSources) {
        setSources(res.data.dataSources);
      }
    }).catch(() => {
      console.log('Error loading sources');
    });
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex items-center justify-between">
        <div>
          <span className="text-blue-900 font-bold text-xs uppercase tracking-wider bg-blue-100 px-2.5 py-0.5 rounded">
            Government Data Quality & Provenance
          </span>
          <h1 className="text-2xl font-extrabold text-blue-950 mt-1">
            शासकीय माहिती स्रोत स्थिती (Data Source Transparency)
          </h1>
          <p className="text-xs text-slate-600 mt-1">
            KaushalVani strictly uses verified government datasets and never invents qualifications or schemes.
          </p>
        </div>
        <Database className="w-12 h-12 text-blue-900 hidden sm:block" />
      </div>

      {/* Sources Grid */}
      <div className="space-y-4">
        {sources.map((src) => (
          <div key={src.id} className="bg-white border-2 border-slate-300 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-2 border-b pb-2">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  {src.publisher}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                  {src.name}
                </h3>
              </div>
              <span className="bg-emerald-100 text-emerald-900 border border-emerald-300 text-xs font-bold px-3 py-1 rounded-full">
                {src.status}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded border">
              <div>
                <span className="text-slate-500 block font-semibold">प्रकार (Type):</span>
                <span className="font-bold text-slate-900">{src.type}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-semibold">शेवटची सिंक वेळ (Last Sync):</span>
                <span className="font-bold text-slate-900">{src.lastSync}</span>
              </div>
              <div>
                <span className="text-slate-500 block font-semibold">अधिकृत वेबसाईट (Official Link):</span>
                <a href={src.sourceUrl} target="_blank" rel="noreferrer" className="text-blue-900 font-bold hover:underline flex items-center space-x-1">
                  <span>{src.sourceUrl}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};
