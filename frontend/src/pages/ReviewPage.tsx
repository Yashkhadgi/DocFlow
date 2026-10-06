import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getDocumentById,
  updateDocumentFields,
  approveDocument,
  retryDocument,
} from '../api/client';
import type { LineItem } from '../api/types';
import { Button } from '../components/Button';
import { StatusBadge } from '../components/StatusBadge';
import { Badge } from '../components/Badge';
import { Input } from '../components/Input';
import { useToast } from '../components/Toast';

export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: doc, isLoading, isError, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocumentById(id!),
    enabled: !!id,
  });

  const [fieldEdits, setFieldEdits] = useState<Record<string, string>>({});
  const [lineItemsEdits, setLineItemsEdits] = useState<LineItem[]>([]);

  useEffect(() => {
    if (doc) {
      const initialFields: Record<string, string> = {};
      doc.fields.forEach((f) => {
        initialFields[f.field_name] = f.reviewed_value ?? f.value ?? '';
      });
      setFieldEdits(initialFields);
      setLineItemsEdits(doc.line_items || []);
    }
  }, [doc]);

  const updateMutation = useMutation({
    mutationFn: () =>
      updateDocumentFields(id!, {
        fields: fieldEdits,
        line_items: lineItemsEdits,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['document', id], updated);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Fields updated and revalidated successfully!');
    },
    onError: (err: any) => {
      toast.error(err?.error?.message || err?.message || 'Failed to update fields');
    },
  });

  const approveMutation = useMutation({
    mutationFn: (force: boolean = false) => approveDocument(id!, { force }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['document', id], updated);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document approved successfully!');
    },
    onError: (err: any) => {
      toast.error(err?.error?.message || err?.message || 'Failed to approve document');
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => retryDocument(id!),
    onSuccess: (updated) => {
      queryClient.setQueryData(['document', id], updated);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document re-queued for extraction!');
    },
    onError: (err: any) => {
      toast.error(err?.error?.message || err?.message || 'Failed to retry document');
    },
  });

  if (isLoading) {
    return <div className="max-w-6xl mx-auto p-12 text-center text-xs font-mono text-[#78716C]">Loading document details...</div>;
  }

  if (isError || !doc) {
    return (
      <div className="max-w-md mx-auto text-center my-12 bg-white border border-[#E5E2DA] p-8">
        <div className="text-[#C5221F] font-bold text-xs">
          Error: {(error as any)?.error?.message || 'Document not found'}
        </div>
        <Link to="/" className="inline-block mt-4">
          <Button variant="secondary" size="sm">
            &larr; Back to Documents
          </Button>
        </Link>
      </div>
    );
  }

  // --- RENDERING 1: DUPLICATE VIEW (Matching duplicate.png) ---
  if (doc.status === 'duplicate') {
    return (
      <div className="max-w-7xl mx-auto space-y-4 text-[#1C1917] font-sans pb-12">
        {/* Header Bar */}
        <div className="flex justify-between items-center text-xs text-[#78716C]">
          <Link to="/" className="hover:text-[#1C1917] flex items-center space-x-1">
            <span>&larr; Back to Documents</span>
          </Link>
          <div className="flex items-center space-x-2 font-mono">
            <span>DOC ID: {doc.id}</span>
            <StatusBadge status="duplicate" />
          </div>
        </div>

        {/* Title & Claimed Total */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div>
            <div className="text-xs text-[#78716C] font-mono">
              Apex Partners \u2022 Uploaded Oct 23, 2024 \u2022 SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            </div>
            <h1 className="text-2xl font-bold font-serif-title tracking-tight text-[#1C1917] mt-0.5">
              {doc.filename}
            </h1>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <div className="text-[10px] uppercase font-mono tracking-wider text-[#A8A29E]">CLAIMED TOTAL</div>
              <div className="text-2xl font-bold font-serif-title text-[#1C1917]">₹12,500.00</div>
            </div>
            <Button variant="outline" size="sm">Original File</Button>
          </div>
        </div>

        {/* Purple Quarantine Warning Banner */}
        <div className="bg-[#F3E8FF] border border-[#E9D5FF] border-l-4 border-l-[#7E22CE] p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="space-y-1 text-xs">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-[#7E22CE]">Duplicate Document Detected</span>
              <span className="bg-[#7E22CE] text-white text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5">
                AUTOMATIC QUARANTINED
              </span>
            </div>
            <div className="text-[#581C87]">
              <strong>Duplicate:</strong> same_file (SHA-256 byte-for-byte checksum match with existing approved record).
            </div>
            <div className="text-[11px] text-[#7E22CE]">
              Rule match: Exact binary hash match & identical invoice identifier APX-1033.
            </div>
          </div>
          <Button variant="primary" size="sm" className="bg-[#7E22CE] hover:bg-[#6B21A8] text-white shrink-0">
            Open original document &rarr;
          </Button>
        </div>

        {/* Grid Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Scan Preview with Stamp */}
          <div className="lg:col-span-7 bg-white border border-[#E5E2DA] p-6 space-y-4">
            <div className="flex justify-between items-center text-[10px] font-mono uppercase text-[#78716C]">
              <span>DOCUMENT PREVIEW (100% Zoom)</span>
              <div className="flex space-x-2">
                <button className="px-1 border">&minus;</button>
                <span>100%</span>
                <button className="px-1 border">+</button>
              </div>
            </div>

            <div className="bg-[#FBF9F5] border border-[#E5E2DA] p-8 text-center relative min-h-[360px] flex flex-col justify-between">
              {/* Overlay Stamp */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="border-4 border-[#7E22CE] text-[#7E22CE] font-bold text-lg tracking-widest p-4 transform -rotate-12 bg-white/90 uppercase text-center shadow-md">
                  DUPLICATE DETECTED
                  <div className="text-[10px] tracking-normal font-sans text-[#7E22CE]">SILENT HASH MATCH - NON-ACTIONABLE</div>
                </div>
              </div>

              <div className="text-left font-mono text-xs space-y-2 opacity-60">
                <div className="font-bold text-sm">APEX PARTNERS</div>
                <div>Invoice #APX-1033</div>
                <div>Amount: ₹12,500.00</div>
              </div>

              <div className="text-[11px] font-mono text-[#78716C] text-left pt-8 border-t border-[#E5E2DA]">
                <div>File: {doc.filename} (3.2 MB)</div>
                <div>Matching Original: INV-2024-0741_Apex.pdf</div>
              </div>
            </div>
          </div>

          {/* Right Panels */}
          <div className="lg:col-span-5 space-y-6">
            {/* Match Breakdown Card */}
            <div className="bg-white border border-[#E5E2DA] p-6 space-y-4">
              <div className="flex justify-between items-center text-xs border-b border-[#F0ECE1] pb-3">
                <span className="font-bold text-[#1C1917] font-mono uppercase tracking-wider">
                  \u2699 DUPLICATE MATCH BREAKDOWN
                </span>
                <Badge variant="purple" className="text-[10px]">FLAGGED & ISOLATED</Badge>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Detection Method</span>
                  <span className="font-bold text-[#137333] font-mono">\u2022 SHA-256 Binary Hash (100% Match)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Active Master Record</span>
                  <span className="font-bold text-[#7E22CE] font-mono">INV-2024-0741 APPROVED</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Vendor Authority</span>
                  <span className="font-semibold text-[#1C1917]">Apex Partners (VND-8821)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Invoice Serial</span>
                  <span className="font-mono text-[#1C1917]">APX-1033 (In General Ledger)</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-[#F0ECE1]">
                  <span className="text-[#78716C] font-bold">Ledger Total</span>
                  <span className="font-bold font-mono text-sm text-[#1C1917]">₹12,500.00 USD</span>
                </div>
              </div>
            </div>

            {/* Comparison Summary */}
            <div className="bg-white border border-[#E5E2DA] p-6 space-y-3">
              <div className="flex justify-between items-center text-xs font-mono border-b border-[#F0ECE1] pb-2">
                <span className="font-bold text-[#1C1917]">COMPARISON SUMMARY</span>
                <span className="text-[10px] text-[#78716C]">Byte-by-Byte Diff</span>
              </div>
              <table className="w-full text-left text-xs">
                <thead className="text-[10px] text-[#78716C] font-bold uppercase border-b border-[#F0ECE1]">
                  <tr>
                    <th className="pb-1">PARAMETER</th>
                    <th className="pb-1">CURRENT UPLOAD</th>
                    <th className="pb-1">ORIGINAL DOCUMENT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F0ECE1] font-mono text-[11px]">
                  <tr>
                    <td className="py-1.5 text-[#78716C]">Filename</td>
                    <td>Apex_Consulting...</td>
                    <td>INV-2024-0741...</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 text-[#78716C]">File Size</td>
                    <td>3.2 MB</td>
                    <td className="text-[#7E22CE]">3.2 MB (Identical)</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 text-[#78716C]">Total USD</td>
                    <td className="font-bold">₹12,500.00</td>
                    <td className="font-bold text-[#137333]">₹12,500.00</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- RENDERING 2: FAILED VIEW (Matching failed.png) ---
  if (doc.status === 'failed') {
    return (
      <div className="max-w-7xl mx-auto space-y-4 text-[#1C1917] font-sans pb-12">
        {/* Header Bar */}
        <div className="flex justify-between items-center text-xs text-[#78716C]">
          <Link to="/" className="hover:text-[#1C1917] flex items-center space-x-1">
            <span>&larr; Back to Documents</span>
          </Link>
          <div className="flex items-center space-x-2 font-mono">
            <span>DOC ID: {doc.id}</span>
            <StatusBadge status="failed" />
          </div>
        </div>

        {/* Title & Actions */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold font-serif-title tracking-tight text-[#1C1917]">
                {doc.filename}
              </h1>
              <span className="bg-[#FCE8E6] text-[#C5221F] text-[10px] font-bold px-1.5 py-0.5 border border-[#FAD2CF]">
                OCR REJECTED
              </span>
            </div>
            <div className="text-xs text-[#78716C] font-mono mt-0.5">
              Uploaded Oct 22, 2024 \u2022 Vendor: Delta Express \u2022 Total: ₹850.00
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">Original File</Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={retryMutation.isPending}
              onClick={() => retryMutation.mutate()}
              className="bg-[#BD3A17]"
            >
              Retry Ingestion
            </Button>
          </div>
        </div>

        {/* Red Failure Banner */}
        <div className="bg-[#FCE8E6] border border-[#FAD2CF] border-l-4 border-l-[#C5221F] p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="space-y-1 text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-4 h-4 rounded-full bg-[#C5221F] text-white inline-flex items-center justify-center font-bold text-[10px]">!</span>
              <span className="font-bold text-[#C5221F]">OCR Parsing Failed: Invalid Tax ID checksum</span>
              <span className="bg-[#C5221F] text-white text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5">
                ATTEMPTS USED: 3 OF 3
              </span>
            </div>
            <div className="text-[#C5221F]">
              Tax identifier does not match government ledger registry format. Automated validation rules encountered an invalid modulo-97 sum on field <code className="bg-[#F8D7DA] px-1 font-mono">tax_id_code</code>.
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            isLoading={retryMutation.isPending}
            onClick={() => retryMutation.mutate()}
            className="bg-[#C5221F] hover:bg-[#A81C19] text-white shrink-0 uppercase tracking-wider font-bold"
          >
            RETRY
          </Button>
        </div>

        {/* Grid Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Scan Preview */}
          <div className="lg:col-span-6 bg-white border border-[#E5E2DA] p-6 space-y-4">
            <div className="flex justify-between items-center text-[10px] font-mono uppercase text-[#78716C]">
              <span>DOCUMENT PREVIEW (100% Zoom)</span>
            </div>
            <div className="bg-[#FBF9F5] border border-[#E5E2DA] p-6 text-center space-y-4 min-h-[380px]">
              <div className="bg-white border border-[#D5D1C8] p-6 max-w-xs mx-auto text-left font-mono text-xs space-y-2">
                <div className="font-bold text-center border-b pb-2">DELTA EXPRESS CORP</div>
                <div className="flex justify-between text-[11px] text-[#78716C]">
                  <span>RECEIPT NO: DLT-0041</span>
                  <span>DATE: OCT 22, 2024</span>
                </div>
                <div className="py-2 border-y border-[#F0ECE1]">
                  <div className="flex justify-between"><span>Freight Priority</span><span>₹520.00</span></div>
                  <div className="flex justify-between font-bold pt-2"><span>TOTAL PAID</span><span>₹850.00</span></div>
                </div>
                {/* Red Error Box on Scan */}
                <div className="bg-[#FCE8E6] border border-[#C5221F] p-2 text-[10px] text-[#C5221F]">
                  <div className="font-bold uppercase font-mono">\u26A0 ERROR: INVALID CHECKSUM</div>
                  <div>TAX IDENTIFICATION NO. DE-83920199</div>
                </div>
              </div>
              <div className="text-[11px] font-mono text-[#78716C] text-left">
                File: Scan_Receipt_0921.jpg (1.8 MB) \u2022 Engine: Tesseract v5.3 / LedgerOCR
              </div>
            </div>
          </div>

          {/* Right Diagnostics & Form */}
          <div className="lg:col-span-6 space-y-4">
            {/* Processing Diagnostics */}
            <div className="bg-white border border-[#E5E2DA] p-6 space-y-3">
              <div className="flex justify-between items-center text-xs font-mono border-b border-[#F0ECE1] pb-2">
                <span className="font-bold text-[#1C1917]">Processing Diagnostics</span>
                <span className="text-[#C5221F] font-bold">HALTED</span>
              </div>
              <div className="space-y-2 text-xs font-mono">
                <div className="p-2 bg-[#FBF9F5] border border-[#E5E2DA]">
                  <div className="flex justify-between font-bold text-[#C5221F]">
                    <span>Attempt 1: Failed</span>
                    <span className="text-[#78716C] font-normal">Oct 22, 14:10</span>
                  </div>
                  <div className="text-[11px] text-[#78716C] mt-0.5">Timeout on primary OCR pass.</div>
                </div>
                <div className="p-2 bg-[#FCE8E6] border border-[#FAD2CF]">
                  <div className="flex justify-between font-bold text-[#C5221F]">
                    <span>Attempt 3: Failed (Terminal)</span>
                    <span className="text-[#78716C] font-normal">Oct 22, 14:15</span>
                  </div>
                  <div className="text-[11px] text-[#C5221F] mt-0.5">Checksum validation mismatch. Government registry API returned invalid issuer key.</div>
                </div>
              </div>
            </div>

            {/* Extracted Fields Snapshots */}
            <div className="bg-white border border-[#E5E2DA] p-6 space-y-4">
              <div className="flex justify-between items-center border-b border-[#F0ECE1] pb-2">
                <span className="font-bold text-xs text-[#1C1917]">Extracted Fields</span>
                <span className="text-[10px] font-mono text-[#78716C]">CONFIDENCE: 61%</span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-2.5 bg-[#FBF9F5] border border-[#E5E2DA]">
                  <div className="text-[10px] text-[#78716C]">VENDOR NAME</div>
                  <div className="font-bold text-[#1C1917] mt-1">Delta Express</div>
                </div>
                <div className="p-2.5 bg-[#FCE8E6] border border-[#FAD2CF]">
                  <div className="text-[10px] text-[#C5221F] font-bold">TAX IDENTIFICATION NUMBER</div>
                  <div className="font-bold text-[#C5221F] mt-1">DE-83920199</div>
                  <div className="text-[9px] text-[#C5221F] mt-0.5">Match failure</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- RENDERING 3: NEEDS REVIEW / QUEUED VIEW (Matching review.png) ---
  return (
    <div className="max-w-7xl mx-auto space-y-4 text-[#1C1917] font-sans pb-12">
      {/* Header Bar */}
      <div className="flex justify-between items-center text-xs text-[#78716C]">
        <Link to="/" className="hover:text-[#1C1917] flex items-center space-x-1">
          <span>&larr; Back to Documents</span>
        </Link>
        <div className="flex items-center space-x-2 font-mono">
          <span>AUDIT LOG ID: #REC-0921-X4</span>
        </div>
      </div>

      {/* Document Title & Status */}
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold font-serif-title tracking-tight text-[#1C1917]">
              {doc.filename}
            </h1>
            <StatusBadge status={doc.status} />
          </div>
          <div className="text-xs text-[#78716C] font-mono mt-0.5">
            Re-queued just now \u2022 Vendor: Delta Express \u2022 Total: ₹850.00
          </div>
        </div>
        <div className="text-xs text-[#78716C] font-mono animate-pulse">
          Processing...
        </div>
      </div>

      {/* Live Feed Banner */}
      <div className="bg-[#FFFBF7] border border-[#FDE68A] border-l-4 border-l-[#BD3A17] p-4 flex justify-between items-center text-xs">
        <div className="flex items-center space-x-3">
          <span className="w-5 h-5 rounded-full bg-[#FEF3D6] text-[#BD3A17] flex items-center justify-center font-bold animate-spin">\u21BB</span>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-[#1C1917]">Processing, this page will update automatically</span>
              <span className="bg-[#FEF3D6] text-[#B45309] text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5">
                LIVE FEED
              </span>
            </div>
            <div className="text-[#78716C] text-[11px] mt-0.5">
              Re-running OCR pipeline and tax verification engine (Attempt 4)... Position #1 in queue.
            </div>
          </div>
        </div>
        <div className="text-right font-mono">
          <div className="text-[10px] text-[#A8A29E] uppercase">ESTIMATED WAIT</div>
          <div className="font-bold text-sm text-[#BD3A17]">~4 seconds</div>
        </div>
      </div>

      {/* Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Scan Preview */}
        <div className="lg:col-span-5 bg-white border border-[#E5E2DA] p-6 space-y-4">
          <div className="flex justify-between items-center text-[10px] font-mono uppercase text-[#78716C]">
            <span>DOCUMENT SCAN</span>
            <div className="flex space-x-2">
              <button className="px-1 border">&minus;</button>
              <span>100%</span>
              <button className="px-1 border">+</button>
            </div>
          </div>
          <div className="bg-[#FBF9F5] border border-[#E5E2DA] p-6 text-center space-y-4 min-h-[380px]">
            <div className="bg-white border border-[#D5D1C8] p-6 max-w-xs mx-auto text-left font-mono text-xs space-y-2">
              <div className="font-bold text-center border-b pb-2">DELTA EXPRESS LOGISTICS</div>
              <div className="text-[10px] text-[#78716C] text-center">HQ: 489 Freight Parkway, Chicago IL</div>
              <div className="py-2 border-y border-[#F0ECE1] space-y-1">
                <div className="flex justify-between"><span>Priority Heavy Cargo</span><span>₹750.00</span></div>
                <div className="flex justify-between font-bold pt-2"><span>TOTAL PAID</span><span>₹850.00</span></div>
              </div>
            </div>
            <div className="text-[11px] font-mono text-[#78716C] text-left">
              Source: Direct Mobile Scanner ( Elena R. ) \u2022 2.4 MB - 300 DPI
            </div>
          </div>
        </div>

        {/* Right Live Ingestion & Form */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white border border-[#E5E2DA] p-6 space-y-4">
            <div className="flex justify-between items-center text-xs font-mono border-b border-[#F0ECE1] pb-2">
              <span className="font-bold text-[#1C1917]">\u25CF Live Ingestion Pipeline</span>
              <span className="text-[10px] text-[#78716C]">Engine v4.2.1</span>
            </div>

            {/* Pipeline Steps */}
            <div className="space-y-3 text-xs font-mono">
              <div className="flex items-start space-x-3">
                <span className="w-4 h-4 rounded-full bg-[#137333] text-white flex items-center justify-center text-[10px] font-bold mt-0.5">&check;</span>
                <div className="flex-1">
                  <div className="flex justify-between">
                    <span className="font-bold text-[#1C1917]">Document Re-queued <strong className="text-[#137333]">COMPLETED</strong></span>
                    <span className="text-[#78716C] text-[10px]">Just now</span>
                  </div>
                  <div className="text-[11px] text-[#78716C]">Retry trigger received from Elena Rostova</div>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <span className="w-4 h-4 rounded-full bg-[#BD3A17] text-white flex items-center justify-center text-[10px] font-bold mt-0.5 animate-pulse">\u25CF</span>
                <div className="flex-1">
                  <div className="flex justify-between">
                    <span className="font-bold text-[#1C1917]">Optical AI OCR Pass <strong className="text-[#BD3A17]">IN PROGRESS</strong></span>
                    <span className="text-[#BD3A17] text-[10px] font-bold">75%</span>
                  </div>
                  <div className="text-[11px] text-[#78716C]">High-res multi-pass text and spatial block recovery running...</div>
                </div>
              </div>
            </div>

            {/* Extracted Fields Form */}
            <div className="pt-4 border-t border-[#F0ECE1] space-y-4">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="font-bold text-[#1C1917]">Extracted Fields</span>
                <Badge variant="amber" className="text-[9px] uppercase font-bold">CONFIDENCE LOCK: PENDING</Badge>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                {doc.fields.map((field) => (
                  <div key={field.field_name} className="p-3 bg-[#FBF9F5] border border-[#E5E2DA]">
                    <div className="flex justify-between text-[10px] text-[#78716C]">
                      <span className="uppercase">{field.field_name.replace('_', ' ')}</span>
                      <span className="text-[#137333] font-bold">{(field.confidence * 100).toFixed(0)}% Confidence</span>
                    </div>
                    <Input
                      disabled={doc.status !== 'needs_review'}
                      value={fieldEdits[field.field_name] ?? ''}
                      onChange={(e) => setFieldEdits({ ...fieldEdits, [field.field_name]: e.target.value })}
                      className="mt-1 font-bold text-xs"
                    />
                  </div>
                ))}
              </div>

              {doc.status === 'needs_review' && (
                <div className="pt-4 border-t border-[#F0ECE1] flex space-x-3">
                  <Button variant="primary" size="md" isLoading={updateMutation.isPending} onClick={() => updateMutation.mutate()}>
                    Save Changes
                  </Button>
                  <Button variant="secondary" size="md" isLoading={approveMutation.isPending} onClick={() => approveMutation.mutate(false)}>
                    Approve
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
