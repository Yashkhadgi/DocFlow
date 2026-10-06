import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadDocuments } from '../api/client';
import type { UploadResultItem } from '../api/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/Card';
import { Button } from '../components/Button';
import { StatusBadge } from '../components/StatusBadge';
import { Badge } from '../components/Badge';
import { useToast } from '../components/Toast';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
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
      toast.success(`Successfully submitted batch of ${res.results.length} files`);
    } catch (err: any) {
      toast.error('Upload failed: ' + (err?.error?.message || err?.message));
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
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Upload Invoices</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Bulk upload PDF, JPG, or PNG files (max 10 MB per file, max 20 files per batch)
        </p>
      </div>

      {/* Quick Test Presets */}
      <Card className="p-4 bg-indigo-50/30 border-indigo-100">
        <span className="text-xs font-bold text-indigo-900 uppercase tracking-wider block mb-2">
          Quick Test Presets:
        </span>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => addSimulatedFile('clean_invoice.pdf')}
          >
            + clean_invoice.pdf
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => addSimulatedFile('clean_invoice_copy.pdf')}
            className="text-purple-700 bg-purple-50 hover:bg-purple-100 border-purple-200"
          >
            + clean_invoice_copy.pdf (Duplicate)
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => addSimulatedFile('notes.exe', 'application/x-msdownload')}
            className="text-rose-700 bg-rose-50 hover:bg-rose-100 border-rose-200"
          >
            + notes.exe (Unsupported Type)
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedFiles([])}
          >
            Clear All
          </Button>
        </div>
      </Card>

      {/* Upload Drop Area */}
      <Card className="border-2 border-dashed border-slate-300 hover:border-indigo-500 p-8 text-center transition-colors">
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
          className="cursor-pointer inline-flex flex-col items-center justify-center space-y-3"
        >
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-2xl font-bold shadow-xs border border-indigo-100/60">
            &uarr;
          </div>
          <div>
            <span className="text-sm font-bold text-slate-900 block">
              Click to browse or drag and drop invoice files here
            </span>
            <span className="text-xs text-slate-500">PDF, JPG, PNG (Max 10 MB per file)</span>
          </div>
        </label>
      </Card>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Selected Files ({selectedFiles.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100">
            {selectedFiles.map((f, i) => (
              <div key={i} className="py-2.5 flex justify-between items-center text-xs font-mono">
                <span className="font-semibold text-slate-800">{f.name}</span>
                <span className="text-slate-500">{(f.size / 1024).toFixed(1)} KB</span>
              </div>
            ))}
            <div className="pt-4">
              <Button
                variant="primary"
                size="lg"
                fullWidth
                isLoading={isUploading}
                onClick={handleUpload}
              >
                Submit Batch Upload
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Results Display */}
      {uploadResults && (
        <Card className="border-indigo-200">
          <CardHeader>
            <CardTitle className="text-sm">Batch Upload Outcome</CardTitle>
            <CardDescription>Per-file upload and queueing status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {uploadResults.map((res, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-lg border bg-slate-50 border-slate-200"
              >
                <span className="font-mono text-xs font-bold text-slate-800">
                  {res.filename}
                </span>
                <div>
                  {res.status === 'queued' && <StatusBadge status="queued" />}
                  {res.status === 'duplicate' && <StatusBadge status="duplicate" />}
                  {res.error && (
                    <Badge variant="red">
                      Error: {res.error.message}
                    </Badge>
                  )}
                </div>
              </div>
            ))}

            <div className="pt-2">
              <Button
                variant="secondary"
                size="md"
                fullWidth
                onClick={() => navigate('/')}
              >
                Go to Dashboard to track progress &rarr;
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
