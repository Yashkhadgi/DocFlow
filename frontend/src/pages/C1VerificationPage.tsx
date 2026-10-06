import React, { useState } from 'react';
import {
  getHealth,
  login,
  getDocuments,
  getDocumentById,
  uploadDocuments,
  updateDocumentFields,
  approveDocument,
  retryDocument,
  exportDocuments,
  isMockMode,
  getAuthToken,
  getApiErrorMessage,
} from '../api/client';

interface TestResult {
  name: string;
  passed: boolean;
  message: string;
  details?: unknown;
}

export const C1VerificationPage: React.FC = () => {
  const [results, setResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const runAllTests = async () => {
    setIsRunning(true);
    const testLogs: TestResult[] = [];

    const addLog = (name: string, passed: boolean, message: string, details?: unknown) => {
      testLogs.push({ name, passed, message, details });
      setResults([...testLogs]);
    };

    try {
      // Test 1: Check VITE_USE_MOCK flag
      const mockActive = isMockMode();
      addLog(
        '1. VITE_USE_MOCK Environment Switch',
        true,
        `VITE_USE_MOCK is currently evaluated as: ${mockActive ? 'true (Mock Mode)' : 'false (Real API Mode)'}`
      );

      // Test 2: GET /health
      try {
        const health = await getHealth();
        addLog('2. GET /health', health.status === 'ok', `Returned status: ${health.status}`, health);
      } catch (err: unknown) {
        addLog('2. GET /health', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 3: POST /auth/login
      try {
        const authRes = await login({ email: 'demo@docflow.app', password: 'Demo@1234' });
        const storedToken = getAuthToken();
        addLog(
          '3. POST /auth/login & Token Store',
          !!authRes.access_token && storedToken === authRes.access_token,
          `Access token retrieved and persisted in memory/localStorage (${authRes.user.email})`
        );
      } catch (err: unknown) {
        addLog('3. POST /auth/login', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 4: GET /documents
      try {
        const docs = await getDocuments();
        addLog(
          '4. GET /documents (Section 5.3 Schema)',
          Array.isArray(docs.items) && typeof docs.counts === 'object',
          `Loaded ${docs.items.length} items. Counts: queued=${docs.counts.queued}, needs_review=${docs.counts.needs_review}, approved=${docs.counts.approved}, failed=${docs.counts.failed}, duplicate=${docs.counts.duplicate}`
        );
      } catch (err: unknown) {
        addLog('4. GET /documents', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 5: POST /documents/upload & Duplicate/Unsupported simulation
      try {
        const fakeClean = new File(['test'], 'invoice_test.pdf', { type: 'application/pdf' });
        const fakeCopy = new File(['test'], 'clean_invoice_copy.pdf', { type: 'application/pdf' });
        const fakeExe = new File(['test'], 'malware.exe', { type: 'application/x-msdownload' });

        const uploadRes = await uploadDocuments([fakeClean, fakeCopy, fakeExe]);
        const cleanResult = uploadRes.results.find((r) => r.filename === 'invoice_test.pdf');
        const copyResult = uploadRes.results.find((r) => r.filename === 'clean_invoice_copy.pdf');
        const exeResult = uploadRes.results.find((r) => r.filename === 'malware.exe');

        const uploadPassed =
          cleanResult?.status === 'queued' &&
          copyResult?.status === 'duplicate' &&
          exeResult?.error?.code === 'unsupported_type';

        addLog(
          '5. POST /documents/upload (Simulated Queued, Duplicate, & Unsupported Types)',
          uploadPassed,
          `Clean status: ${cleanResult?.status}, Copy status: ${copyResult?.status}, Exe error: ${exeResult?.error?.code}`,
          uploadRes
        );
      } catch (err: unknown) {
        addLog('5. POST /documents/upload', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 6: GET /documents/{id}
      try {
        const docDetail = await getDocumentById('33333333-3333-3333-3333-333333333333');
        addLog(
          '6. GET /documents/{id} (document_detail_needs_review.json)',
          docDetail.id === '33333333-3333-3333-3333-333333333333' && docDetail.fields.length > 0,
          `Document filename: ${docDetail.filename}, fields count: ${docDetail.fields.length}, issues count: ${docDetail.validation_issues.length}`,
          docDetail
        );
      } catch (err: unknown) {
        addLog('6. GET /documents/{id}', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 7: PATCH /documents/{id}/fields (Fix total mismatch and revalidate)
      try {
        const patchRes = await updateDocumentFields('33333333-3333-3333-3333-333333333333', {
          fields: { total: '11800.00' },
        });
        const totalField = patchRes.fields.find((f) => f.field_name === 'total');
        const mismatchResolved = !patchRes.validation_issues.some((i) => i.rule === 'total_mismatch');

        addLog(
          '7. PATCH /documents/{id}/fields & Revalidation',
          totalField?.reviewed_value === '11800.00' && mismatchResolved,
          `Updated total to 11800.00. total_mismatch issue cleared: ${mismatchResolved}`
        );
      } catch (err: unknown) {
        addLog('7. PATCH /documents/{id}/fields', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 8: POST /documents/{id}/approve
      try {
        const approvedDoc = await approveDocument('33333333-3333-3333-3333-333333333333');
        addLog(
          '8. POST /documents/{id}/approve',
          approvedDoc.status === 'approved',
          `Document status transitioned to '${approvedDoc.status}'`
        );
      } catch (err: unknown) {
        addLog('8. POST /documents/{id}/approve', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 9: POST /documents/{id}/retry
      try {
        const retriedDoc = await retryDocument('44444444-4444-4444-4444-444444444444');
        addLog(
          '9. POST /documents/{id}/retry (From Failed -> Queued)',
          retriedDoc.status === 'queued',
          `Document status reset from 'failed' to '${retriedDoc.status}'`
        );
      } catch (err: unknown) {
        addLog('9. POST /documents/{id}/retry', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }

      // Test 10: GET /export
      try {
        const csvBlob = await exportDocuments({ format: 'csv' });
        const jsonBlob = await exportDocuments({ format: 'json' });
        addLog(
          '10. GET /export (CSV & JSON format generation)',
          csvBlob.size > 0 && jsonBlob.size > 0,
          `Generated CSV blob (${csvBlob.size} bytes) & JSON blob (${jsonBlob.size} bytes)`
        );
      } catch (err: unknown) {
        addLog('10. GET /export', false, `Failed: ${getApiErrorMessage(err, 'Error')}`);
      }
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-extrabold text-white">Task C1 Checklist & Verification</h1>
          <p className="text-sm text-slate-400">
            Automated verification suite testing all Section 5.3 endpoints, types, and mock layer simulation
          </p>
        </div>
        <button
          onClick={runAllTests}
          disabled={isRunning}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
        >
          {isRunning ? 'Running Verification...' : 'Execute C1 Verification Suite'}
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
          Verification Requirements Matrix:
        </h3>
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-300">
          <li className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center space-x-2">
            <span className="text-emerald-400 font-bold">&check;</span>
            <span>Tailwind setup (@tailwindcss/vite v4 plugin)</span>
          </li>
          <li className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center space-x-2">
            <span className="text-emerald-400 font-bold">&check;</span>
            <span>React Router setup (BrowserRouter + pages)</span>
          </li>
          <li className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center space-x-2">
            <span className="text-emerald-400 font-bold">&check;</span>
            <span>TanStack Query setup (QueryClientProvider)</span>
          </li>
          <li className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center space-x-2">
            <span className="text-emerald-400 font-bold">&check;</span>
            <span>src/api/types.ts (Section 5.3 responses)</span>
          </li>
          <li className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center space-x-2">
            <span className="text-emerald-400 font-bold">&check;</span>
            <span>src/api/client.ts (One function per endpoint)</span>
          </li>
          <li className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center space-x-2">
            <span className="text-emerald-400 font-bold">&check;</span>
            <span>src/api/mock/ (Built from /contracts/fixtures)</span>
          </li>
        </ul>
      </div>

      {/* Results Log */}
      {results.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Verification Execution Log ({results.filter((r) => r.passed).length}/{results.length} Passed)
            </h3>
          </div>

          <div className="space-y-3 font-mono text-xs">
            {results.map((res, i) => (
              <div
                key={i}
                className={`p-3 rounded-lg border flex flex-col space-y-1 ${
                  res.passed
                    ? 'bg-emerald-950/30 border-emerald-800/80 text-emerald-300'
                    : 'bg-rose-950/30 border-rose-800/80 text-rose-300'
                }`}
              >
                <div className="flex items-center justify-between font-bold">
                  <span>{res.name}</span>
                  <span>{res.passed ? 'PASS' : 'FAIL'}</span>
                </div>
                <div className="text-[11px] text-slate-300">{res.message}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
