import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadDocuments } from '../api/client';
import type { UploadResultItem } from '../api/types';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<UploadResultItem[] | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    setIsUploading(true);
    setUploadResults(null);
    try {
      const res = await uploadDocuments(selectedFiles);
      setUploadResults(res.results);
    } catch (err: any) {
      alert('Upload failed: ' + (err?.error?.message || err?.message));
    } finally {
      setIsUploading(false);
    }
  };

  const addSimulatedFile = (name: string, type: string = 'application/pdf') => {
    const fakeFile = new File(['mock content'], name, { type });
    setSelectedFiles((prev) => [...prev, fakeFile]);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-white">Upload Invoices</h1>
        <p className="text-sm text-slate-400">
          Bulk upload your invoices (PDF, JPG, PNG up to 10 MB per file, max 20 files)
        </p>
      </div>

      {/* Quick Test Presets */}
      <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Quick Test Batch Presets:
        </span>
        <div className="flex flex-wrap gap-2 pt-1">
          <button
            onClick={() => addSimulatedFile('clean_invoice.pdf')}
            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded border border-slate-700"
          >
            + clean_invoice.pdf
          </button>
          <button
            onClick={() => addSimulatedFile('clean_invoice_copy.pdf')}
            className="px-3 py-1 bg-purple-950/70 hover:bg-purple-900/70 text-purple-300 text-xs font-mono rounded border border-purple-800/80"
          >
            + clean_invoice_copy.pdf (Duplicate Test)
          </button>
          <button
            onClick={() => addSimulatedFile('notes.exe', 'application/x-msdownload')}
            className="px-3 py-1 bg-rose-950/70 hover:bg-rose-900/70 text-rose-300 text-xs font-mono rounded border border-rose-800/80"
          >
            + notes.exe (Unsupported Type Test)
          </button>
          <button
            onClick={() => setSelectedFiles([])}
            className="px-3 py-1 bg-slate-950 text-slate-400 text-xs rounded border border-slate-800"
          >
            Clear Selected
          </button>
        </div>
      </div>

      {/* Upload Box */}
      <div className="bg-slate-900/80 border-2 border-dashed border-slate-700 hover:border-indigo-500/50 rounded-2xl p-8 text-center space-y-4 transition-colors">
        <input
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileChange}
          className="hidden"
          id="file-upload-input"
        />
        <label
          htmlFor="file-upload-input"
          className="cursor-pointer inline-flex flex-col items-center justify-center space-y-2"
        >
          <div className="w-12 h-12 rounded-xl bg-indigo-950/60 text-indigo-400 flex items-center justify-center text-xl font-bold border border-indigo-800/50">
            &uarr;
          </div>
          <span className="text-sm font-semibold text-slate-200">
            Click to browse or drag and drop invoice files here
          </span>
          <span className="text-xs text-slate-500">PDF, JPG, PNG (Max 10 MB each)</span>
        </label>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex justify-between items-center text-xs text-slate-400 font-semibold">
            <span>Selected Files ({selectedFiles.length})</span>
          </div>
          <ul className="divide-y divide-slate-800">
            {selectedFiles.map((f, i) => (
              <li key={i} className="py-2 flex justify-between items-center font-mono text-xs text-slate-300">
                <span>{f.name}</span>
                <span className="text-slate-500">{(f.size / 1024).toFixed(1)} KB</span>
              </li>
            ))}
          </ul>
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-lg transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50"
          >
            {isUploading ? 'Uploading & Enqueuing...' : 'Submit Batch Upload'}
          </button>
        </div>
      )}

      {/* Upload Results Display */}
      {uploadResults && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Batch Upload Outcome
          </h3>
          <div className="space-y-2">
            {uploadResults.map((res, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-lg border bg-slate-950 border-slate-800"
              >
                <span className="font-mono text-sm text-slate-200">{res.filename}</span>
                <div>
                  {res.status === 'queued' && (
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                      Queued
                    </span>
                  )}
                  {res.status === 'duplicate' && (
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-950 text-purple-300 border border-purple-800">
                      Duplicate
                    </span>
                  )}
                  {res.error && (
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-950 text-rose-300 border border-rose-800">
                      Error: {res.error.message}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="pt-2">
            <button
              onClick={() => navigate('/')}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg"
            >
              Go to Dashboard to track progress &rarr;
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
