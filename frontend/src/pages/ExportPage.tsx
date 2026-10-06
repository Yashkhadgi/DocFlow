import React, { useState } from 'react';
import { exportDocuments } from '../api/client';

export const ExportPage: React.FC = () => {
  const [format, setFormat] = useState<'csv' | 'json'>('csv');
  const [isExporting, setIsExporting] = useState(false);

  const handleDownload = async () => {
    setIsExporting(true);
    try {
      const blob = await exportDocuments({ format, status: 'approved' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `docflow_export_${Date.now()}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Export failed: ' + (err?.error?.message || err?.message));
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-white">Export Processed Data</h1>
        <p className="text-sm text-slate-400">
          Download structured extraction data for all approved documents
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div>
          <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
            Select Format
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setFormat('csv')}
              className={`p-4 rounded-xl border text-left transition-all ${
                format === 'csv'
                  ? 'bg-indigo-950/60 border-indigo-500 ring-2 ring-indigo-500/20 text-white'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <div className="font-bold text-sm">CSV Format</div>
              <div className="text-xs text-slate-500 mt-1">One row per line item. Excel compatible.</div>
            </button>

            <button
              onClick={() => setFormat('json')}
              className={`p-4 rounded-xl border text-left transition-all ${
                format === 'json'
                  ? 'bg-indigo-950/60 border-indigo-500 ring-2 ring-indigo-500/20 text-white'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <div className="font-bold text-sm">JSON Format</div>
              <div className="text-xs text-slate-500 mt-1">Structured document objects array.</div>
            </button>
          </div>
        </div>

        <button
          onClick={handleDownload}
          disabled={isExporting}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-xl transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50"
        >
          {isExporting ? 'Generating Download...' : `Download ${format.toUpperCase()} Export`}
        </button>
      </div>
    </div>
  );
};
