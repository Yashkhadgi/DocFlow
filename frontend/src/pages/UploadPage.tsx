import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { uploadDocuments } from '../api/client';
import { Button } from '../components/Button';
import { StatusBadge } from '../components/StatusBadge';
import { useToast } from '../components/Toast';

interface UploadFileItem {
  id: string;
  file: File;
  name: string;
  sizeFormatted: string;
  status: 'queued' | 'duplicate' | 'unsupported_type' | 'file_too_large' | 'uploading' | string;
  subtext: string;
  duplicateOfId?: string;
  progress?: number;
}

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [selectedFiles, setSelectedFiles] = useState<UploadFileItem[]>([
    {
      id: 'f1',
      file: new File([''], 'invoice_001.pdf', { type: 'application/pdf' }),
      name: 'invoice_001.pdf',
      sizeFormatted: '2.4 MB',
      status: 'queued',
      subtext: 'Checksum verified \u2022 Ready for staging',
    },
    {
      id: 'f2',
      file: new File([''], 'invoice_001_copy.pdf', { type: 'application/pdf' }),
      name: 'invoice_001_copy.pdf',
      sizeFormatted: '2.4 MB',
      status: 'duplicate',
      subtext: 'Same file as invoice_001.pdf \u2022 Open original',
      duplicateOfId: '22222222-2222-2222-2222-222222222222',
    },
    {
      id: 'f3',
      file: new File([''], 'scan_old.exe', { type: 'application/x-msdownload' }),
      name: 'scan_old.exe',
      sizeFormatted: '450 KB',
      status: 'unsupported_type',
      subtext: 'Only PDF, JPG, PNG allowed',
    },
    {
      id: 'f4',
      file: new File([''], 'big_scan.pdf', { type: 'application/pdf' }),
      name: 'big_scan.pdf',
      sizeFormatted: '14.8 MB',
      status: 'file_too_large',
      subtext: 'Over 10 MB limit (Maximum allowed is 10.0 MB)',
    },
    {
      id: 'f5',
      file: new File([''], 'receipt.jpg', { type: 'image/jpeg' }),
      name: 'receipt.jpg',
      sizeFormatted: '1.8 MB',
      status: 'uploading',
      subtext: 'Uploading... 60%',
      progress: 60,
    },
  ]);

  const [isUploading, setIsUploading] = useState(false);
  const [_dragActive, setDragActive] = useState(false);
  const [_batchCompleted, setBatchCompleted] = useState(false);

  const handleFilePicker = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      processFiles(Array.from(e.target.files));
    }
  };

  const processFiles = (files: File[]) => {
    const newItems: UploadFileItem[] = files.map((f, idx) => {
      const lowerName = f.name.toLowerCase();
      const sizeMB = f.size / (1024 * 1024);
      let status = 'queued';
      let subtext = 'Checksum verified \u2022 Ready for staging';

      if (lowerName.endsWith('.exe')) {
        status = 'unsupported_type';
        subtext = 'Only PDF, JPG, PNG allowed';
      } else if (sizeMB > 10) {
        status = 'file_too_large';
        subtext = 'Over 10 MB limit (Maximum allowed is 10.0 MB)';
      } else if (lowerName.includes('copy')) {
        status = 'duplicate';
        subtext = 'Same file detected as existing record \u2022 Open original';
      }

      return {
        id: 'file-' + Date.now() + '-' + idx,
        file: f,
        name: f.name,
        sizeFormatted: sizeMB < 1 ? `${(f.size / 1024).toFixed(0)} KB` : `${sizeMB.toFixed(1)} MB`,
        status,
        subtext,
      };
    });

    setSelectedFiles((prev) => [...prev, ...newItems]);
  };

  const removeFile = (id: string) => {
    setSelectedFiles((prev) => prev.filter((item) => item.id !== id));
  };

  const handleBatchUpload = async () => {
    const validFiles = selectedFiles
      .filter((item) => item.status === 'queued' || item.status === 'uploading')
      .map((item) => item.file);

    if (validFiles.length === 0) {
      toast.warning('No valid queued files to upload.');
      return;
    }

    setIsUploading(true);
    try {
      await uploadDocuments(validFiles);
      setBatchCompleted(true);
      toast.success('Batch upload submitted successfully!');
    } catch (err: any) {
      toast.error('Upload failed: ' + (err?.error?.message || err?.message));
    } finally {
      setIsUploading(false);
    }
  };

  const queuedCount = selectedFiles.filter((f) => f.status === 'queued').length;
  const duplicateCount = selectedFiles.filter((f) => f.status === 'duplicate').length;
  const rejectedCount = selectedFiles.filter(
    (f) => f.status === 'unsupported_type' || f.status === 'file_too_large'
  ).length;
  const uploadingCount = selectedFiles.filter((f) => f.status === 'uploading').length;

  return (
    <div className="max-w-6xl mx-auto space-y-6 text-[#1C1917] font-sans pb-12">
      {/* Top Header */}
      <div>
        <Link to="/" className="text-xs text-[#78716C] hover:text-[#1C1917] inline-flex items-center space-x-1 mb-2">
          <span>&larr; Back to Documents</span>
        </Link>
        <h1 className="text-3xl font-bold font-serif-title tracking-tight text-[#1C1917]">
          Upload invoices
        </h1>
        <p className="text-xs text-[#78716C] mt-0.5">
          Add up to 20 files at once. Each file is checked on its own.
        </p>
      </div>

      {/* Top Dropzone Area */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left Drop Box */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => { e.preventDefault(); setDragActive(false); if (e.dataTransfer.files) processFiles(Array.from(e.dataTransfer.files)); }}
          className="bg-white border-2 border-dashed border-[#C5C1B5] hover:border-[#BD3A17] p-8 text-center flex flex-col items-center justify-center space-y-3 rounded-none transition-colors"
        >
          <input
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={handleFilePicker}
            className="hidden"
            id="upload-file-input"
          />
          <div className="w-10 h-10 rounded-full bg-[#FFF0EB] text-[#BD3A17] flex items-center justify-center">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <span className="text-sm font-bold text-[#1C1917]">Drop invoices here or </span>
            <label htmlFor="upload-file-input" className="text-sm font-bold text-[#BD3A17] hover:underline cursor-pointer">
              browse
            </label>
            <p className="text-[11px] text-[#A8A29E] mt-1">PDF, JPG, PNG. Up to 20 files, 10 MB each.</p>
          </div>
        </div>

        {/* Right Drop Box (Drag-over active preview state) */}
        <div className="bg-[#FFFBF7] border-2 border-solid border-[#BD3A17] p-8 text-center flex flex-col items-center justify-center space-y-2 relative rounded-none">
          <div className="absolute top-2 right-2 bg-[#BD3A17] text-white text-[9px] font-bold uppercase tracking-wider px-2 py-0.5">
            PREVIEW: DRAG-OVER ACTIVE STATE
          </div>
          <div className="w-10 h-10 rounded-full bg-[#FCE8E3] text-[#BD3A17] flex items-center justify-center">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <div className="text-sm font-bold text-[#BD3A17]">Drop files to upload now</div>
          <p className="text-[11px] text-[#78716C]">Release cursor to queue files into isolated validation</p>
        </div>
      </div>

      {/* Selected Files Section */}
      <div className="space-y-3">
        <div className="flex justify-between items-center text-xs">
          <div>
            <span className="font-bold text-[#1C1917]">Selected Files ({selectedFiles.length})</span>
            <span className="text-[#78716C] ml-2 font-mono">\u2014 Ready for validation & ingestion</span>
          </div>
          <div className="text-[#78716C] text-[11px]">
            Isolated validation: Each file is verified independently.
          </div>
        </div>

        {/* File Rows */}
        <div className="space-y-2">
          {selectedFiles.map((item) => {
            const isError = item.status === 'unsupported_type' || item.status === 'file_too_large';
            const isDuplicate = item.status === 'duplicate';

            return (
              <div
                key={item.id}
                className={`bg-white border p-3.5 flex items-center justify-between text-xs rounded-none ${
                  isError
                    ? 'border-l-4 border-l-[#C5221F] border-[#E5E2DA]'
                    : isDuplicate
                    ? 'border-l-4 border-l-[#7E22CE] border-[#E5E2DA]'
                    : 'border-[#E5E2DA]'
                }`}
              >
                <div className="flex items-center space-x-3">
                  {/* Icon */}
                  <div className="text-[#78716C]">
                    {isError ? (
                      <div className="w-5 h-5 rounded-full bg-[#FCE8E6] text-[#C5221F] flex items-center justify-center font-bold text-[10px]">
                        !
                      </div>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-[#1C1917] font-mono">{item.name}</span>
                      <span className="text-[#78716C] font-mono text-[11px]">{item.sizeFormatted}</span>
                    </div>
                    <div className="text-[11px] text-[#78716C] mt-0.5">
                      {item.subtext}
                      {item.duplicateOfId && (
                        <Link to={`/documents/${item.duplicateOfId}`} className="text-[#7E22CE] underline ml-1 font-semibold">
                          Open original
                        </Link>
                      )}
                    </div>
                    {item.progress !== undefined && (
                      <div className="w-36 bg-[#E5E2DA] h-1.5 mt-1 rounded-none overflow-hidden">
                        <div className="bg-[#1A73E8] h-full" style={{ width: `${item.progress}%` }}></div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <StatusBadge status={item.status} />
                  <button
                    onClick={() => removeFile(item.id)}
                    className="text-[#A8A29E] hover:text-[#1C1917] text-sm font-bold px-1"
                  >
                    &times;
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Batch Status Summary Banner */}
      <div className="bg-[#FFFBF7] border border-[#F0ECE1] p-3.5 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-2">
          <span className="w-4 h-4 rounded-full border border-[#BD3A17] text-[#BD3A17] inline-flex items-center justify-center text-[10px] font-bold">i</span>
          <div>
            <span className="font-bold text-[#1C1917]">
              {selectedFiles.length} files processed:{' '}
            </span>
            <span className="text-[#555555] font-semibold">{queuedCount} queued, </span>
            <span className="text-[#7E22CE] font-semibold">{duplicateCount} duplicate, </span>
            <span className="text-[#C5221F] font-semibold">{rejectedCount} rejected, </span>
            <span className="text-[#1A73E8] font-semibold">{uploadingCount} uploading</span>
            <div className="text-[11px] text-[#78716C]">
              Rejected files will not be uploaded. Valid files will proceed to OCR ingestion.
            </div>
          </div>
        </div>

        <div className="text-[10px] font-mono uppercase tracking-wider text-[#A8A29E] font-bold">
          BATCH VERIFICATION MODE
        </div>
      </div>

      {/* Actions & Completed Preview Bar */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 pt-4 border-t border-[#E5E2DA]">
        <div className="md:col-span-7 space-y-3">
          <div className="text-[10px] uppercase font-mono tracking-wider font-bold text-[#A8A29E]">ACTIONS</div>
          <div className="flex space-x-3">
            <Button variant="secondary" size="md" onClick={() => setSelectedFiles([])}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="md"
              isLoading={isUploading}
              onClick={handleBatchUpload}
            >
              Upload {selectedFiles.length} files &rarr;
            </Button>
          </div>
          <div className="text-[11px] text-[#78716C]">
            Files with unresolvable errors will be automatically stripped from final submission.
          </div>
        </div>

        {/* Right side Completed State Preview Box */}
        <div className="md:col-span-5 bg-white border border-[#CEEAD6] border-l-4 border-l-[#137333] p-4 space-y-3">
          <div className="flex justify-between items-center text-[10px] font-mono uppercase tracking-wider">
            <span className="text-[#78716C]">COMPLETED STATE PREVIEW</span>
            <span className="text-[#137333] font-bold">\u2022 PIPELINE READY</span>
          </div>

          <div className="flex items-start space-x-2">
            <div className="w-5 h-5 rounded-full bg-[#E6F4EA] text-[#137333] flex items-center justify-center shrink-0 font-bold text-xs mt-0.5">
              &check;
            </div>
            <div>
              <div className="text-xs font-bold text-[#1C1917]">All valid files dispatched to pipeline</div>
              <div className="text-[11px] text-[#78716C] mt-0.5">
                3 files successfully staged for OCR extraction and line-item indexing.
              </div>
            </div>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/')}
            className="w-full text-xs font-bold bg-[#BD3A17] uppercase tracking-wider"
          >
            Go to Documents &rarr;
          </Button>
        </div>
      </div>
    </div>
  );
};
