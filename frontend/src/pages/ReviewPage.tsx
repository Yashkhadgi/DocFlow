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
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/Card';
import { Button } from '../components/Button';
import { StatusBadge } from '../components/StatusBadge';
import { Badge } from '../components/Badge';
import { Input } from '../components/Input';
import { Skeleton } from '../components/Skeleton';
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
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <Skeleton variant="card" count={2} />
      </div>
    );
  }

  if (isError || !doc) {
    return (
      <div className="max-w-md mx-auto text-center my-12">
        <Card className="p-8 space-y-4">
          <div className="text-rose-600 font-bold">
            Error: {(error as any)?.error?.message || 'Document not found'}
          </div>
          <Link to="/">
            <Button variant="secondary" size="sm">
              &larr; Back to Dashboard
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const blockingErrors = doc.validation_issues.filter((i) => i.severity === 'error');

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-extrabold text-slate-900 font-mono tracking-tight">
              {doc.filename}
            </h1>
            <StatusBadge status={doc.status} />
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">ID: {doc.id}</p>
        </div>
        <Link to="/">
          <Button variant="secondary" size="sm">
            &larr; Back to Dashboard
          </Button>
        </Link>
      </div>

      {/* Validation Issues Banner */}
      {doc.validation_issues.length > 0 && (
        <Card className="border-amber-200 bg-amber-50/40 p-4 space-y-2">
          <span className="text-xs font-bold text-amber-800 uppercase tracking-wider block">
            Validation Issues ({doc.validation_issues.length})
          </span>
          <ul className="space-y-1.5 text-xs">
            {doc.validation_issues.map((issue, idx) => (
              <li
                key={idx}
                className={`p-2.5 rounded-lg border flex items-center justify-between font-medium ${
                  issue.severity === 'error'
                    ? 'bg-rose-50 border-rose-200 text-rose-800'
                    : 'bg-amber-100/60 border-amber-200 text-amber-800'
                }`}
              >
                <span>
                  <strong>[{issue.rule}]</strong> {issue.message}
                </span>
                <Badge variant={issue.severity === 'error' ? 'red' : 'amber'} size="sm">
                  {issue.severity.toUpperCase()}
                </Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Split screen layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Document Preview */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-6 flex flex-col justify-between min-h-[420px]">
            <div className="space-y-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                Document Preview
              </span>
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center space-y-3">
                <div className="w-16 h-20 mx-auto bg-white border border-slate-300 rounded shadow-xs flex items-center justify-center font-mono text-xs font-bold text-slate-600">
                  PDF
                </div>
                <p className="text-xs font-mono font-semibold text-slate-800">{doc.filename}</p>
                <p className="text-[11px] text-slate-500">
                  MIME: {doc.mime_type} &bull; URL: {doc.file_url ? 'Presigned URL Active' : 'None'}
                </p>
              </div>
            </div>

            {doc.status === 'failed' && (
              <div className="pt-4 border-t border-slate-100 space-y-3">
                <p className="text-xs text-rose-600 font-semibold">
                  Error: {doc.error_message}
                </p>
                <Button
                  variant="danger"
                  size="md"
                  fullWidth
                  isLoading={retryMutation.isPending}
                  onClick={() => retryMutation.mutate()}
                >
                  Retry Processing
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Right Column: Extracted Fields & Line Items Form */}
        <div className="lg:col-span-7 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Extracted Fields & Verification</CardTitle>
              <CardDescription>
                Review extracted values. Yellow highlighted fields require review.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {doc.fields.map((field) => {
                  const isNeedsReview = field.needs_review;
                  const hasIssue = doc.validation_issues.some(
                    (i) => i.field_name === field.field_name
                  );

                  return (
                    <div
                      key={field.field_name}
                      className={`p-3.5 rounded-xl border transition-all ${
                        hasIssue
                          ? 'bg-rose-50/50 border-rose-300 ring-2 ring-rose-500/10'
                          : isNeedsReview
                          ? 'bg-amber-50/50 border-amber-300 ring-2 ring-amber-500/10'
                          : 'bg-white border-slate-200'
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="text-xs font-semibold text-slate-700 capitalize">
                          {field.field_name.replace('_', ' ')}
                        </span>
                        <Badge
                          variant={field.confidence >= 0.85 ? 'green' : 'amber'}
                          size="sm"
                        >
                          {(field.confidence * 100).toFixed(0)}%
                        </Badge>
                      </div>

                      <Input
                        disabled={doc.status !== 'needs_review'}
                        value={fieldEdits[field.field_name] ?? ''}
                        onChange={(e) =>
                          setFieldEdits({
                            ...fieldEdits,
                            [field.field_name]: e.target.value,
                          })
                        }
                      />
                    </div>
                  );
                })}
              </div>

              {/* Action Buttons */}
              {doc.status === 'needs_review' && (
                <div className="pt-4 border-t border-slate-100 flex flex-wrap gap-3">
                  <Button
                    variant="primary"
                    size="md"
                    isLoading={updateMutation.isPending}
                    onClick={() => updateMutation.mutate()}
                  >
                    Save & Revalidate
                  </Button>

                  <Button
                    variant="secondary"
                    size="md"
                    className="text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border-emerald-200"
                    isLoading={approveMutation.isPending}
                    onClick={() => approveMutation.mutate(false)}
                  >
                    Approve
                  </Button>

                  {blockingErrors.length > 0 && (
                    <Button
                      variant="outline"
                      size="md"
                      className="text-amber-700 hover:bg-amber-50 border-amber-300"
                      isLoading={approveMutation.isPending}
                      onClick={() => approveMutation.mutate(true)}
                    >
                      Force Approve
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
