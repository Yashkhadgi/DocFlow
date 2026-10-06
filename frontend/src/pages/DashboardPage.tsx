import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getDocuments } from '../api/client';
import type { DocumentListItem, DocumentStatus } from '../api/types';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { StatusBadge } from '../components/StatusBadge';
import { Input } from '../components/Input';
import { Skeleton } from '../components/Skeleton';
import { EmptyState } from '../components/EmptyState';

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
      const hasPending = query.state.data?.items.some(
        (item: DocumentListItem) => item.status === 'queued' || item.status === 'processing'
      );
      return hasPending ? 3000 : false;
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
            Document Dashboard
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Manage, review, and monitor document extractions and automation pipeline
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            Refresh
          </Button>
          <Link to="/upload">
            <Button variant="primary" size="md">
              Upload Invoices
            </Button>
          </Link>
        </div>
      </div>

      {/* Counts Cards */}
      {data?.counts && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {(
            [
              ['queued', 'Queued', data.counts.queued, 'text-slate-600'],
              ['processing', 'Processing', data.counts.processing, 'text-blue-600'],
              ['needs_review', 'Needs Review', data.counts.needs_review, 'text-amber-600'],
              ['approved', 'Approved', data.counts.approved, 'text-emerald-600'],
              ['failed', 'Failed', data.counts.failed, 'text-rose-600'],
              ['duplicate', 'Duplicate', data.counts.duplicate, 'text-purple-600'],
            ] as const
          ).map(([key, label, count, colorClass]) => (
            <Card
              key={key}
              hoverable
              onClick={() => setSelectedStatus(key)}
              className={`p-4 ${
                selectedStatus === key
                  ? 'ring-2 ring-indigo-600 border-indigo-600 bg-indigo-50/20'
                  : ''
              }`}
            >
              <div className="text-xs font-semibold text-slate-500">{label}</div>
              <div className={`text-2xl font-black mt-1 ${colorClass}`}>{count}</div>
            </Card>
          ))}
        </div>
      )}

      {/* Search and Filters */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="w-full sm:w-80">
            <Input
              placeholder="Search filename, vendor, or invoice #..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              startIcon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              }
            />
          </div>
          <div className="flex items-center space-x-2 overflow-x-auto w-full sm:w-auto">
            <button
              onClick={() => setSelectedStatus('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                selectedStatus === 'all'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All Documents
            </button>
          </div>
        </div>
      </Card>

      {/* Document Table / List */}
      <Card className="overflow-hidden shadow-xs">
        {isLoading ? (
          <div className="p-6">
            <Skeleton variant="card" count={3} />
          </div>
        ) : isError ? (
          <div className="p-12 text-center text-rose-600 font-medium">
            Error loading documents: {(error as any)?.error?.message || 'Unknown error'}
          </div>
        ) : data?.items.length === 0 ? (
          <EmptyState
            title="No documents found"
            description="No documents match your filter or search query. Upload your first invoice to get started!"
            primaryAction={
              <Link to="/upload">
                <Button variant="primary" size="sm">
                  Upload Invoice Now
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-slate-500 font-semibold text-xs uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4">Filename</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Vendor</th>
                  <th className="px-6 py-4">Invoice #</th>
                  <th className="px-6 py-4">Total</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {data?.items.map((doc: DocumentListItem) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-slate-50/70 transition-colors group"
                  >
                    <td className="px-6 py-4 font-mono font-semibold text-slate-900">
                      {doc.filename}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-800">
                      {doc.vendor_name || '—'}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-600">
                      {doc.invoice_number || '—'}
                    </td>
                    <td className="px-6 py-4 font-bold text-slate-900">
                      {formatMoney(doc.total, doc.currency)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link to={`/documents/${doc.id}`}>
                        <Button variant="secondary" size="sm">
                          View Detail &rarr;
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

const KNOWN_CURRENCIES = new Set(['INR', 'USD', 'EUR', 'GBP', 'AUD', 'CAD', 'SGD', 'AED', 'JPY']);

function formatMoney(amount: string | null, currency: string | null): string {
  if (amount === null || amount === undefined || amount === '') {
    return currency ? `No amount (${currency.toUpperCase()})` : '—';
  }

  const numericAmount = Number(amount);
  const normalizedCurrency = currency?.trim().toUpperCase() || null;
  if (
    normalizedCurrency &&
    KNOWN_CURRENCIES.has(normalizedCurrency) &&
    Number.isFinite(numericAmount)
  ) {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: normalizedCurrency,
      }).format(numericAmount);
    } catch {
      // Fall through to the explicit unknown display below.
    }
  }

  const displayAmount = Number.isFinite(numericAmount) ? numericAmount.toFixed(2) : amount;
  return `Unknown currency · ${displayAmount}`;
}
