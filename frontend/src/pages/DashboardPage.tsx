import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getDocuments, getApiErrorMessage } from '../api/client';
import type { DocumentListItem, DocumentStatus } from '../api/types';

export const DashboardPage: React.FC = () => {
  const [selectedStatus, setSelectedStatus] = useState<DocumentStatus | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['documents', selectedStatus, searchTerm],
    queryFn: () =>
      getDocuments({
        status: selectedStatus === 'all' ? undefined : selectedStatus,
        q: searchTerm || undefined,
      }),
    refetchInterval: (query) => {
      // Auto-poll every 3s if any document is queued or processing
      const hasPending = query.state.data?.items.some(
        (item: DocumentListItem) => item.status === 'queued' || item.status === 'processing'
      );
      return hasPending ? 3000 : false;
    },
  });

  const getStatusBadge = (status: DocumentStatus) => {
    const styles: Record<DocumentStatus, string> = {
      queued: 'bg-slate-800 text-slate-300 border-slate-700',
      processing: 'bg-blue-950/80 text-blue-400 border-blue-800/80 animate-pulse',
      needs_review: 'bg-amber-950/80 text-amber-400 border-amber-800/80',
      approved: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/80',
      failed: 'bg-rose-950/80 text-rose-400 border-rose-800/80',
      duplicate: 'bg-purple-950/80 text-purple-400 border-purple-800/80',
    };
    return (
      <span
        className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
          styles[status] || styles.queued
        }`}
      >
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white">Document Dashboard</h1>
          <p className="text-slate-400 text-sm">
            Manage, review, and monitor your document extractions
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => refetch()}
            className="px-3 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            Refresh
          </button>
          <Link
            to="/upload"
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all"
          >
            Upload Invoices
          </Link>
        </div>
      </div>

      {/* Counts Cards */}
      {data?.counts && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {(
            [
              ['queued', 'Queued', data.counts.queued, 'text-slate-400'],
              ['processing', 'Processing', data.counts.processing, 'text-blue-400'],
              ['needs_review', 'Needs Review', data.counts.needs_review, 'text-amber-400'],
              ['approved', 'Approved', data.counts.approved, 'text-emerald-400'],
              ['failed', 'Failed', data.counts.failed, 'text-rose-400'],
              ['duplicate', 'Duplicate', data.counts.duplicate, 'text-purple-400'],
            ] as const
          ).map(([key, label, count, colorClass]) => (
            <button
              key={key}
              onClick={() => setSelectedStatus(key)}
              className={`p-4 rounded-xl border text-left transition-all ${
                selectedStatus === key
                  ? 'bg-slate-900 border-indigo-500 ring-2 ring-indigo-500/20'
                  : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="text-xs font-medium text-slate-400">{label}</div>
              <div className={`text-2xl font-black mt-1 ${colorClass}`}>{count}</div>
            </button>
          ))}
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-slate-900/70 p-4 rounded-xl border border-slate-800">
        <div className="w-full sm:w-80">
          <input
            type="text"
            placeholder="Search filename, vendor, or invoice #..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex items-center space-x-2 overflow-x-auto w-full sm:w-auto">
          <button
            onClick={() => setSelectedStatus('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
              selectedStatus === 'all'
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            All
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900/80 rounded-xl border border-slate-800 overflow-hidden shadow-xl">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400">Loading documents...</div>
        ) : isError ? (
          <div className="p-12 text-center text-rose-400">
            Error loading documents: {getApiErrorMessage(error, 'Unknown error')}
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center text-slate-500">No documents found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950 text-slate-400 font-medium text-xs uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4">Filename</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Vendor</th>
                  <th className="px-6 py-4">Invoice #</th>
                  <th className="px-6 py-4">Total</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data?.items.map((doc: DocumentListItem) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-slate-800/40 transition-colors group"
                  >
                    <td className="px-6 py-4 font-mono font-medium text-white flex items-center space-x-2">
                      <span>{doc.filename}</span>
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(doc.status)}</td>
                    <td className="px-6 py-4">{doc.vendor_name || '—'}</td>
                    <td className="px-6 py-4 font-mono text-xs">{doc.invoice_number || '—'}</td>
                    <td className="px-6 py-4 font-semibold text-slate-100">
                      {doc.total ? `₹${doc.total}` : '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/documents/${doc.id}`}
                        className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-950/50 border border-indigo-800/50 px-3 py-1.5 rounded-md transition-colors"
                      >
                        View Detail &rarr;
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
