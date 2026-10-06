import React, { useState } from 'react';
import { exportDocuments } from '../api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/Card';
import { Button } from '../components/Button';
import { useToast } from '../components/Toast';

export const ExportPage: React.FC = () => {
  const toast = useToast();
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
      toast.success(`Downloaded ${format.toUpperCase()} export file!`);
    } catch (err: any) {
      toast.error('Export failed: ' + (err?.error?.message || err?.message));
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Export Processed Data</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Download structured extraction data for all approved documents
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Choose Export Format</CardTitle>
          <CardDescription>Select between CSV spreadsheet format or structured JSON array</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setFormat('csv')}
              className={`p-4 rounded-xl border text-left transition-all ${
                format === 'csv'
                  ? 'bg-indigo-50/60 border-indigo-600 ring-2 ring-indigo-600/20 text-indigo-950 font-bold'
                  : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
              }`}
            >
              <div className="text-sm font-bold">CSV Format</div>
              <div className="text-xs text-slate-500 mt-1 font-normal">
                One row per line item. Opens in Excel/Sheets.
              </div>
            </button>

            <button
              type="button"
              onClick={() => setFormat('json')}
              className={`p-4 rounded-xl border text-left transition-all ${
                format === 'json'
                  ? 'bg-indigo-50/60 border-indigo-600 ring-2 ring-indigo-600/20 text-indigo-950 font-bold'
                  : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
              }`}
            >
              <div className="text-sm font-bold">JSON Format</div>
              <div className="text-xs text-slate-500 mt-1 font-normal">
                Structured array of document objects.
              </div>
            </button>
          </div>

          <Button
            variant="primary"
            size="lg"
            fullWidth
            isLoading={isExporting}
            onClick={handleDownload}
          >
            Download {format.toUpperCase()} Export
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
