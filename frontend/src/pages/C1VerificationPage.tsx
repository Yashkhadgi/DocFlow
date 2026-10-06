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
} from '../api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/Card';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { StatusBadge } from '../components/StatusBadge';
import { useToast } from '../components/Toast';

interface TestResult {
  name: string;
  passed: boolean;
  message: string;
  details?: any;
}

export const C1VerificationPage: React.FC = () => {
  const toast = useToast();
  const [results, setResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const runAllTests = async () => {
    setIsRunning(true);
    const testLogs: TestResult[] = [];

    const addLog = (name: string, passed: boolean, message: string, details?: any) => {
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
      } catch (err: any) {
        addLog('2. GET /health', false, `Failed: ${err.message || 'Error'}`);
      }

      // Test 3: POST /auth/login
      try {
        const authRes = await login({ email: 'demo@docflow.app', password: 'Demo@1234' });
        const storedToken = getAuthToken();
        addLog(
          '3. POST /auth/login & Token Store',
          !!authRes.access_token && storedToken === authRes.access_token,
          `Access token retrieved and persisted (${authRes.user.email})`
        );
      } catch (err: any) {
        addLog('3. POST /auth/login', false, `Failed: ${err.message || 'Error'}`);
      }

      // Test 4: GET /documents
      try {
        const docs = await getDocuments();
        addLog(
          '4. GET /documents (Section 5.3 Schema)',
          Array.isArray(docs.items) && typeof docs.counts === 'object',
          `Loaded ${docs.items.length} items. Counts: queued=${docs.counts.queued}, needs_review=${docs.counts.needs_review}, approved=${docs.counts.approved}, failed=${docs.counts.failed}, duplicate=${docs.counts.duplicate}`
        );
      } catch (err: any) {
        addLog('4. GET /documents', false, `Failed: ${err.message || 'Error'}`);
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
      } catch (err: any) {
        addLog('5. POST /documents/upload', false, `Failed: ${err.message || 'Error'}`);
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
      } catch (err: any) {
        addLog('6. GET /documents/{id}', false, `Failed: ${err.message || 'Error'}`);
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
      } catch (err: any) {
        addLog('7. PATCH /documents/{id}/fields', false, `Failed: ${err.message || 'Error'}`);
      }

      // Test 8: POST /documents/{id}/approve
      try {
        const approvedDoc = await approveDocument('33333333-3333-3333-3333-333333333333');
        addLog(
          '8. POST /documents/{id}/approve',
          approvedDoc.status === 'approved',
          `Document status transitioned to '${approvedDoc.status}'`
        );
      } catch (err: any) {
        addLog('8. POST /documents/{id}/approve', false, `Failed: ${err.message || 'Error'}`);
      }

      // Test 9: POST /documents/{id}/retry
      try {
        const retriedDoc = await retryDocument('44444444-4444-4444-4444-444444444444');
        addLog(
          '9. POST /documents/{id}/retry (From Failed -> Queued)',
          retriedDoc.status === 'queued',
          `Document status reset from 'failed' to '${retriedDoc.status}'`
        );
      } catch (err: any) {
        addLog('9. POST /documents/{id}/retry', false, `Failed: ${err.message || 'Error'}`);
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
      } catch (err: any) {
        addLog('10. GET /export', false, `Failed: ${err.message || 'Error'}`);
      }

      toast.success('Verification suite executed successfully!');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Design System & Task Verification
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Automated testing suite & shared design system component showcase
          </p>
        </div>
        <Button
          variant="primary"
          size="lg"
          isLoading={isRunning}
          onClick={runAllTests}
        >
          Execute C1 Verification Suite
        </Button>
      </div>

      {/* Design System Showcase */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Design System Showcase</CardTitle>
          <CardDescription>StatusBadges, Buttons, Badges, and Theme Tokens</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-3">
              Status Badge Variants:
            </span>
            <div className="flex flex-wrap gap-2">
              <StatusBadge status="queued" />
              <StatusBadge status="processing" />
              <StatusBadge status="needs_review" />
              <StatusBadge status="approved" />
              <StatusBadge status="failed" />
              <StatusBadge status="duplicate" />
            </div>
          </div>

          <div>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-3">
              Button Component Variants:
            </span>
            <div className="flex flex-wrap gap-3">
              <Button variant="primary">Primary Button</Button>
              <Button variant="secondary">Secondary Button</Button>
              <Button variant="danger">Danger Button</Button>
              <Button variant="outline">Outline Button</Button>
              <Button variant="ghost">Ghost Button</Button>
            </div>
          </div>

          <div>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-3">
              Badge Color Variants:
            </span>
            <div className="flex flex-wrap gap-2">
              <Badge variant="indigo">Indigo</Badge>
              <Badge variant="green" dot>Green Dot</Badge>
              <Badge variant="amber" dot>Amber Dot</Badge>
              <Badge variant="red" dot>Red Dot</Badge>
              <Badge variant="purple" dot>Purple Dot</Badge>
              <Badge variant="blue" dot>Blue Dot</Badge>
              <Badge variant="gray">Gray</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Execution Results */}
      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Verification Execution Log ({results.filter((r) => r.passed).length}/{results.length} Passed)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {results.map((res, i) => (
              <div
                key={i}
                className={`p-3.5 rounded-xl border flex flex-col space-y-1 font-mono text-xs ${
                  res.passed
                    ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900'
                    : 'bg-rose-50/60 border-rose-200 text-rose-900'
                }`}
              >
                <div className="flex items-center justify-between font-bold">
                  <span>{res.name}</span>
                  <Badge variant={res.passed ? 'green' : 'red'}>
                    {res.passed ? 'PASS' : 'FAIL'}
                  </Badge>
                </div>
                <div className="text-[11px] text-slate-600 font-sans">{res.message}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
};
