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

export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: doc, isLoading, isError, error } = useQuery({
    queryKey: ['document', id],
    queryFn: () => getDocumentById(id!),
    enabled: !!id,
  });

  const [fieldEdits, setFieldEdits] = useState<Record<string, string>>({});
  const [lineItemsEdits, setLineItemsEdits] = useState<LineItem[]>([]);
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

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
      setActionMsg({ type: 'success', msg: 'Fields updated and revalidated!' });
    },
    onError: (err: any) => {
      setActionMsg({
        type: 'error',
        msg: err?.error?.message || err?.message || 'Failed to update fields',
      });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (force: boolean = false) => approveDocument(id!, { force }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['document', id], updated);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setActionMsg({ type: 'success', msg: 'Document approved successfully!' });
    },
    onError: (err: any) => {
      setActionMsg({
        type: 'error',
        msg: err?.error?.message || err?.message || 'Failed to approve document',
      });
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => retryDocument(id!),
    onSuccess: (updated) => {
      queryClient.setQueryData(['document', id], updated);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setActionMsg({ type: 'success', msg: 'Document re-queued for extraction!' });
    },
    onError: (err: any) => {
      setActionMsg({
        type: 'error',
        msg: err?.error?.message || err?.message || 'Failed to retry document',
      });
    },
  });

  if (isLoading) return <div className="p-12 text-center text-slate-400">Loading document...</div>;
  if (isError || !doc) {
    return (
      <div className="p-12 text-center text-rose-400 space-y-4">
        <div>Error: {(error as any)?.error?.message || 'Document not found'}</div>
        <Link to="/" className="text-xs text-indigo-400 underline">Back to Dashboard</Link>
      </div>
    );
  }

  const blockingErrors = doc.validation_issues.filter((i) => i.severity === 'error');

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-extrabold text-white font-mono">{doc.filename}</h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-950 text-amber-400 border border-amber-800">
              {doc.status}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">ID: {doc.id}</p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            to="/"
            className="px-3 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
          >
            &larr; Back to Dashboard
          </Link>
        </div>
      </div>

      {actionMsg && (
        <div
          className={`p-3 rounded-lg border text-xs ${
            actionMsg.type === 'success'
              ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
              : 'bg-rose-950/80 border-rose-800 text-rose-300'
          }`}
        >
          {actionMsg.msg}
        </div>
      )}

      {/* Validation Issues Banner */}
      {doc.validation_issues.length > 0 && (
        <div className="bg-slate-900 border border-amber-800/80 rounded-xl p-4 space-y-2">
          <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">
            Validation Issues ({doc.validation_issues.length})
          </span>
          <ul className="space-y-1 text-xs">
            {doc.validation_issues.map((issue, idx) => (
              <li
                key={idx}
                className={`p-2 rounded border flex items-center justify-between ${
                  issue.severity === 'error'
                    ? 'bg-rose-950/50 border-rose-800/80 text-rose-300'
                    : 'bg-amber-950/50 border-amber-800/80 text-amber-300'
                }`}
              >
                <span>
                  <strong>[{issue.rule}]</strong> {issue.message}
                </span>
                <span className="text-[10px] uppercase px-1.5 py-0.5 rounded font-bold border border-current">
                  {issue.severity}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Split screen simulation layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left column: Document Preview */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-between min-h-[400px]">
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Document Preview</h3>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-8 text-center space-y-3">
              <div className="w-16 h-20 mx-auto bg-slate-800 border border-slate-700 rounded flex items-center justify-center font-mono text-xs text-slate-400">
                PDF
              </div>
              <p className="text-xs font-mono text-slate-300">{doc.filename}</p>
              <p className="text-[11px] text-slate-500">
                MIME: {doc.mime_type} &bull; URL: {doc.file_url ? 'Presigned active' : 'None'}
              </p>
            </div>
          </div>
          {doc.status === 'failed' && (
            <div className="pt-4 border-t border-slate-800 space-y-2">
              <p className="text-xs text-rose-400">Failure message: {doc.error_message}</p>
              <button
                onClick={() => retryMutation.mutate()}
                disabled={retryMutation.isPending}
                className="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-lg transition-all"
              >
                {retryMutation.isPending ? 'Re-queueing...' : 'Retry Processing'}
              </button>
            </div>
          )}
        </div>

        {/* Right column: Extracted Fields & Line Items Form */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Extracted Fields & Verification
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {doc.fields.map((field) => {
                const isNeedsReview = field.needs_review;
                const hasIssue = doc.validation_issues.some((i) => i.field_name === field.field_name);

                return (
                  <div
                    key={field.field_name}
                    className={`p-3 rounded-lg border transition-all ${
                      hasIssue
                        ? 'bg-rose-950/20 border-rose-600/60'
                        : isNeedsReview
                        ? 'bg-amber-950/20 border-amber-500/60'
                        : 'bg-slate-950 border-slate-800'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1 text-xs">
                      <label className="font-semibold text-slate-300 capitalize">
                        {field.field_name.replace('_', ' ')}
                      </label>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          field.confidence >= 0.85
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-amber-950 text-amber-400 border border-amber-800 font-bold'
                        }`}
                      >
                        {(field.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>

                    <input
                      type="text"
                      disabled={doc.status !== 'needs_review'}
                      value={fieldEdits[field.field_name] ?? ''}
                      onChange={(e) =>
                        setFieldEdits({
                          ...fieldEdits,
                          [field.field_name]: e.target.value,
                        })
                      }
                      className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono disabled:opacity-60"
                    />
                  </div>
                );
              })}
            </div>

            {/* Action Buttons */}
            {doc.status === 'needs_review' && (
              <div className="pt-4 border-t border-slate-800 flex flex-wrap gap-3">
                <button
                  onClick={() => updateMutation.mutate()}
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-lg transition-all"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save & Revalidate'}
                </button>

                <button
                  onClick={() => approveMutation.mutate(false)}
                  disabled={approveMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-lg transition-all"
                >
                  {approveMutation.isPending ? 'Approving...' : 'Approve'}
                </button>

                {blockingErrors.length > 0 && (
                  <button
                    onClick={() => approveMutation.mutate(true)}
                    disabled={approveMutation.isPending}
                    className="px-3 py-2 bg-slate-800 hover:bg-amber-900/60 text-amber-300 font-semibold text-xs rounded-lg transition-all border border-amber-800/80"
                  >
                    Force Approve
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
