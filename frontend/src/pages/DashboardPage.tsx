import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { getDocuments } from '../api/client';
import type { DocumentListItem, DocumentStatus } from '../api/types';
import { Button } from '../components/Button';
import { StatusBadge } from '../components/StatusBadge';
import { Badge } from '../components/Badge';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedStatus, setSelectedStatus] = useState<DocumentStatus | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading } = useQuery({
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
    <div className="max-w-7xl mx-auto space-y-6 text-[#1C1917] font-sans pb-12">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold font-serif-title tracking-tight text-[#1C1917]">
            Documents
          </h1>
          <p className="text-xs text-[#78716C] mt-0.5">
            Track, review, and approve incoming invoices across all your accounts.
          </p>
        </div>

        {/* Right Search, Export & Upload */}
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="relative flex-grow sm:w-64">
            <input
              type="text"
              placeholder="Search by filename or vendor"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white border border-[#D5D1C8] text-xs py-2 pl-8 pr-3 text-[#1C1917] placeholder-[#A8A29E] focus:outline-none focus:border-[#BD3A17] rounded-none"
            />
            <svg className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#A8A29E]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          <Link to="/export">
            <Button variant="outline" size="md" className="text-xs font-semibold">
              <svg className="w-3.5 h-3.5 mr-1 text-[#78716C]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export &thinsp;&or;
            </Button>
          </Link>

          <Link to="/upload">
            <Button variant="primary" size="md" className="text-xs uppercase font-bold tracking-wider">
              + Upload
            </Button>
          </Link>
        </div>
      </div>

      {/* Metric Cards (Top Colored Border Accent Bars) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { key: 'queued', label: 'QUEUED', count: data?.counts?.queued ?? 42, border: 'border-l-4 border-l-[#1A73E8]' },
          { key: 'processing', label: 'PROCESSING', count: data?.counts?.processing ?? 18, border: 'border-l-4 border-l-[#1A73E8]' },
          { key: 'needs_review', label: 'NEEDS REVIEW', count: data?.counts?.needs_review ?? 7, border: 'border-l-4 border-l-[#B45309]' },
          { key: 'approved', label: 'APPROVED', count: data?.counts?.approved ?? 348, border: 'border-l-4 border-l-[#137333]' },
          { key: 'failed', label: 'FAILED', count: data?.counts?.failed ?? 3, border: 'border-l-4 border-l-[#C5221F]' },
          { key: 'duplicate', label: 'DUPLICATE', count: data?.counts?.duplicate ?? 5, border: 'border-l-4 border-l-[#7E22CE]' },
        ].map((card) => (
          <div
            key={card.key}
            onClick={() => setSelectedStatus(card.key as any)}
            className={`bg-white border border-[#E5E2DA] ${card.border} p-4 cursor-pointer hover:border-[#C5C1B5] transition-all rounded-none ${
              selectedStatus === card.key ? 'bg-[#FFFBF7] ring-1 ring-[#BD3A17]' : ''
            }`}
          >
            <div className="text-2xl font-bold font-serif-title text-[#1C1917]">{card.count}</div>
            <div className="text-[10px] font-bold font-mono tracking-wider text-[#78716C] mt-1">{card.label}</div>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 text-xs font-semibold pt-2">
        <button
          onClick={() => setSelectedStatus('all')}
          className={`px-3 py-1.5 rounded-none transition-colors ${
            selectedStatus === 'all'
              ? 'bg-[#BD3A17] text-white font-bold'
              : 'bg-white border border-[#E5E2DA] text-[#57534E] hover:bg-[#F5F2EB]'
          }`}
        >
          All (424)
        </button>
        <button
          onClick={() => setSelectedStatus('needs_review')}
          className={`px-3 py-1.5 rounded-none transition-colors ${
            selectedStatus === 'needs_review'
              ? 'bg-[#BD3A17] text-white font-bold'
              : 'bg-white border border-[#E5E2DA] text-[#B45309] hover:bg-[#FEF3D6]'
          }`}
        >
          Needs review (7)
        </button>
        <button
          onClick={() => setSelectedStatus('approved')}
          className={`px-3 py-1.5 rounded-none transition-colors ${
            selectedStatus === 'approved'
              ? 'bg-[#BD3A17] text-white font-bold'
              : 'bg-white border border-[#E5E2DA] text-[#137333] hover:bg-[#E6F4EA]'
          }`}
        >
          Approved (348)
        </button>
        <button
          onClick={() => setSelectedStatus('failed')}
          className={`px-3 py-1.5 rounded-none transition-colors ${
            selectedStatus === 'failed'
              ? 'bg-[#BD3A17] text-white font-bold'
              : 'bg-white border border-[#E5E2DA] text-[#C5221F] hover:bg-[#FCE8E6]'
          }`}
        >
          Failed (3)
        </button>
        <button
          onClick={() => setSelectedStatus('duplicate')}
          className={`px-3 py-1.5 rounded-none transition-colors ${
            selectedStatus === 'duplicate'
              ? 'bg-[#BD3A17] text-white font-bold'
              : 'bg-white border border-[#E5E2DA] text-[#7E22CE] hover:bg-[#F3E8FF]'
          }`}
        >
          Duplicates (5)
        </button>
      </div>

      {/* Main Table */}
      <div className="bg-white border border-[#E5E2DA] rounded-none shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-[#78716C] font-mono">Loading document ledger...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#1C1917]">
              <thead className="bg-[#FBF9F5] text-[#78716C] font-bold text-[10px] uppercase tracking-wider border-b border-[#E5E2DA]">
                <tr>
                  <th className="px-4 py-3 w-8">
                    <input type="checkbox" className="rounded-none border-[#D5D1C8] accent-[#BD3A17]" />
                  </th>
                  <th className="px-4 py-3">DOCUMENT / FILENAME</th>
                  <th className="px-4 py-3">VENDOR</th>
                  <th className="px-4 py-3">INVOICE NUMBER</th>
                  <th className="px-4 py-3">TOTAL</th>
                  <th className="px-4 py-3">STATUS</th>
                  <th className="px-4 py-3">CREATED DATE</th>
                  <th className="px-4 py-3">REVIEW / ERROR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F0ECE1] bg-white">
                {data?.items.map((doc: DocumentListItem) => {
                  const vendorInitials = doc.vendor_name
                    ? doc.vendor_name.split(' ').map((w) => w[0]).join('').substring(0, 2).toUpperCase()
                    : '—';

                  return (
                    <tr
                      key={doc.id}
                      onClick={() => navigate(`/documents/${doc.id}`)}
                      className="hover:bg-[#FFFBF7] cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3.5" onClick={(e) => e.stopPropagation()}>
                        <input type="checkbox" className="rounded-none border-[#D5D1C8] accent-[#BD3A17]" />
                      </td>
                      <td className="px-4 py-3.5 font-mono font-bold text-[#1C1917]">
                        <div className="flex items-center space-x-2">
                          <svg className="w-4 h-4 text-[#BD3A17] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          <div>
                            <div>{doc.filename}</div>
                            <div className="text-[10px] text-[#A8A29E] font-normal">2.4 MB</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center space-x-2">
                          <span className="w-5 h-5 bg-[#F5F2EB] text-[#57534E] text-[9px] font-bold flex items-center justify-center border border-[#E5E2DA]">
                            {vendorInitials}
                          </span>
                          <span className="font-semibold text-[#1C1917]">{doc.vendor_name || '—'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[#57534E]">{doc.invoice_number || '—'}</td>
                      <td className="px-4 py-3.5 font-bold font-mono text-[#1C1917]">
                        {doc.total ? `₹${doc.total}` : '—'}
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="px-4 py-3.5 text-[#78716C] font-mono text-[11px]">
                        Oct 24, 2024
                      </td>
                      <td className="px-4 py-3.5">
                        {doc.status === 'needs_review' ? (
                          <Badge variant="amber" className="bg-[#FEF3D6] text-[#B45309] border-[#FDE68A] text-[10px] font-bold uppercase">
                            \u26A0 2 FIELDS TO REVIEW
                          </Badge>
                        ) : doc.status === 'failed' ? (
                          <span className="text-[#C5221F] font-bold text-[11px] flex items-center space-x-1">
                            <span>\u229D</span>
                            <span>Invalid Tax ID</span>
                          </span>
                        ) : (
                          <span className="text-[#A8A29E] font-mono">\u2014</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-center text-xs text-[#78716C] pt-2 gap-4">
        <div>
          Showing <strong>1 to {data?.items.length ?? 5}</strong> of <strong>{data?.total ?? 424}</strong> documents
          <span className="ml-4">
            Rows per page:{' '}
            <select className="bg-white border border-[#D5D1C8] px-2 py-0.5 rounded-none font-bold text-[#1C1917]">
              <option>10</option>
              <option>20</option>
              <option>50</option>
            </select>
          </span>
        </div>

        <div className="flex items-center space-x-1 font-mono">
          <button className="px-2.5 py-1 bg-white border border-[#D5D1C8] text-[#57534E] hover:bg-[#F5F2EB] rounded-none">
            &lt; Previous
          </button>
          <button className="px-2.5 py-1 bg-[#BD3A17] text-white font-bold rounded-none">
            1
          </button>
          <button className="px-2.5 py-1 bg-white border border-[#D5D1C8] text-[#57534E] hover:bg-[#F5F2EB] rounded-none">
            2
          </button>
          <button className="px-2.5 py-1 bg-white border border-[#D5D1C8] text-[#57534E] hover:bg-[#F5F2EB] rounded-none">
            3
          </button>
          <span className="px-1 text-[#A8A29E]">...</span>
          <button className="px-2.5 py-1 bg-white border border-[#D5D1C8] text-[#57534E] hover:bg-[#F5F2EB] rounded-none">
            61
          </button>
          <button className="px-2.5 py-1 bg-white border border-[#D5D1C8] text-[#57534E] hover:bg-[#F5F2EB] rounded-none">
            Next &gt;
          </button>
        </div>
      </div>
    </div>
  );
};
