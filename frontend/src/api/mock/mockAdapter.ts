import type {
  ApproveDocumentRequest,
  AuthResponse,
  DocumentDetail,
  DocumentListItem,
  DocumentStatusCounts,
  DocumentsListResponse,
  ExportParams,
  GetDocumentsParams,
  HealthResponse,
  LoginRequest,
  PatchDocumentFieldsRequest,
  RegisterRequest,
  UploadResponse,
  UploadResultItem,
  User,
} from '../types';
import {
  mockAuthFixture,
  mockDocumentDetailApproved,
  mockDocumentDetailDuplicate,
  mockDocumentDetailFailed,
  mockDocumentDetailNeedsReview,
  mockDocumentsListFixture,
} from './fixtures';

// Helper to delay responses for realistic feel
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Deep clone to avoid mutating fixtures
const clone = <T>(obj: T): T => JSON.parse(JSON.stringify(obj));

class MockDatabase {
  private items: DocumentListItem[];
  private detailsMap: Map<string, DocumentDetail>;

  constructor() {
    this.items = clone(mockDocumentsListFixture.items);
    this.detailsMap = new Map<string, DocumentDetail>([
      [mockDocumentDetailNeedsReview.id, clone(mockDocumentDetailNeedsReview)],
      [mockDocumentDetailApproved.id, clone(mockDocumentDetailApproved)],
      [mockDocumentDetailFailed.id, clone(mockDocumentDetailFailed)],
      [mockDocumentDetailDuplicate.id, clone(mockDocumentDetailDuplicate)],
    ]);

    // Also seed detail entries for scanned_invoice if accessed
    this.detailsMap.set('55555555-5555-5555-5555-555555555555', {
      id: '55555555-5555-5555-5555-555555555555',
      filename: 'scanned_invoice.pdf',
      mime_type: 'application/pdf',
      status: 'processing',
      auto_approved: false,
      duplicate_of_id: null,
      duplicate_reason: null,
      error_message: null,
      file_url: 'https://storage.example.com/presigned/scanned_invoice.pdf',
      fields: [],
      line_items: [],
      validation_issues: [],
      job: {
        status: 'processing',
        attempts: 1,
        max_attempts: 3,
        last_error: null,
      },
      created_at: '2026-10-06T10:12:00Z',
      updated_at: '2026-10-06T10:12:10Z',
    });
  }

  private calculateCounts(): DocumentStatusCounts {
    const counts: DocumentStatusCounts = {
      queued: 0,
      processing: 0,
      needs_review: 0,
      approved: 0,
      failed: 0,
      duplicate: 0,
    };
    for (const item of this.items) {
      if (item.status in counts) {
        counts[item.status]++;
      }
    }
    return counts;
  }

  async getHealth(): Promise<HealthResponse> {
    await delay(100);
    return { status: 'ok' };
  }

  async register(req: RegisterRequest): Promise<User> {
    await delay(200);
    return {
      id: 'usr-' + Math.random().toString(36).substring(2, 9),
      email: req.email,
      full_name: req.full_name || 'New User',
    };
  }

  async login(_req: LoginRequest): Promise<AuthResponse> {
    await delay(250);
    return clone(mockAuthFixture);
  }

  async uploadDocuments(files: File[]): Promise<UploadResponse> {
    await delay(400);
    const results: UploadResultItem[] = [];

    for (const file of files) {
      const lowerName = file.name.toLowerCase();

      if (lowerName.endsWith('.exe')) {
        results.push({
          filename: file.name,
          document_id: null,
          status: null,
          duplicate_of_id: null,
          error: {
            code: 'unsupported_type',
            message: 'Only PDF, JPG, PNG allowed',
          },
        });
        continue;
      }

      if (lowerName.includes('copy')) {
        const dupId = 'dup-' + Math.random().toString(36).substring(2, 9);
        const originalId = '22222222-2222-2222-2222-222222222222';

        const dupItem: DocumentListItem = {
          id: dupId,
          filename: file.name,
          status: 'duplicate',
          auto_approved: false,
          vendor_name: 'Acme Traders',
          invoice_number: 'INV-001',
          currency: 'INR',
          total: '11800.00',
          issues_count: 0,
          low_confidence_count: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };

        const dupDetail: DocumentDetail = {
          id: dupId,
          filename: file.name,
          mime_type: file.type || 'application/pdf',
          status: 'duplicate',
          auto_approved: false,
          duplicate_of_id: originalId,
          duplicate_reason: 'same_file',
          error_message: null,
          file_url: null,
          fields: [],
          line_items: [],
          validation_issues: [],
          job: null,
          created_at: dupItem.created_at,
          updated_at: dupItem.updated_at,
        };

        this.items.unshift(dupItem);
        this.detailsMap.set(dupId, dupDetail);

        results.push({
          filename: file.name,
          document_id: dupId,
          status: 'duplicate',
          duplicate_of_id: originalId,
          error: null,
        });
        continue;
      }

      // Normal valid upload -> status: queued
      const docId = 'doc-' + Math.random().toString(36).substring(2, 9);
      const now = new Date().toISOString();

      const newItem: DocumentListItem = {
        id: docId,
        filename: file.name,
        status: 'queued',
        auto_approved: false,
        vendor_name: null,
        invoice_number: null,
        currency: null,
        total: null,
        issues_count: 0,
        low_confidence_count: 0,
        created_at: now,
        updated_at: now,
      };

      const newDetail: DocumentDetail = {
        id: docId,
        filename: file.name,
        mime_type: file.type || 'application/pdf',
        status: 'queued',
        auto_approved: false,
        duplicate_of_id: null,
        duplicate_reason: null,
        error_message: null,
        file_url: `https://storage.example.com/presigned/${file.name}`,
        fields: [],
        line_items: [],
        validation_issues: [],
        job: {
          status: 'queued',
          attempts: 0,
          max_attempts: 3,
          last_error: null,
        },
        created_at: now,
        updated_at: now,
      };

      this.items.unshift(newItem);
      this.detailsMap.set(docId, newDetail);

      results.push({
        filename: file.name,
        document_id: docId,
        status: 'queued',
        duplicate_of_id: null,
        error: null,
      });

      // Schedule simulation: queued -> processing -> needs_review
      this.scheduleDocumentProcessing(docId);
    }

    return { results };
  }

  private scheduleDocumentProcessing(docId: string) {
    // Step 1: queued -> processing (after 1.5s)
    setTimeout(() => {
      const item = this.items.find((d) => d.id === docId);
      const detail = this.detailsMap.get(docId);
      if (item && detail && item.status === 'queued') {
        item.status = 'processing';
        item.updated_at = new Date().toISOString();
        detail.status = 'processing';
        detail.updated_at = item.updated_at;
        if (detail.job) {
          detail.job.status = 'processing';
          detail.job.attempts = 1;
        }

        // Step 2: processing -> needs_review (after 2s)
        setTimeout(() => {
          if (item.status === 'processing') {
            item.status = 'needs_review';
            item.vendor_name = 'Global Logistics Inc';
            item.invoice_number = 'INV-999';
            item.currency = 'INR';
            item.total = '5400.00';
            item.issues_count = 1;
            item.low_confidence_count = 1;
            item.updated_at = new Date().toISOString();

            detail.status = 'needs_review';
            detail.updated_at = item.updated_at;
            if (detail.job) {
              detail.job.status = 'succeeded';
            }
            detail.fields = [
              {
                field_name: 'vendor_name',
                value: 'Global Logistics Inc',
                reviewed_value: null,
                confidence: 0.96,
                needs_review: false,
                bbox: { page: 1, x: 0.1, y: 0.05, w: 0.3, h: 0.04 },
              },
              {
                field_name: 'invoice_number',
                value: 'INV-999',
                reviewed_value: null,
                confidence: 0.98,
                needs_review: false,
                bbox: null,
              },
              {
                field_name: 'invoice_date',
                value: '2026-10-05',
                reviewed_value: null,
                confidence: 0.95,
                needs_review: false,
                bbox: null,
              },
              {
                field_name: 'gstin',
                value: '29AAACG05611Z5',
                reviewed_value: null,
                confidence: 0.72,
                needs_review: true,
                bbox: null,
              },
              {
                field_name: 'subtotal',
                value: '5000.00',
                reviewed_value: null,
                confidence: 0.95,
                needs_review: false,
                bbox: null,
              },
              {
                field_name: 'tax',
                value: '400.00',
                reviewed_value: null,
                confidence: 0.95,
                needs_review: false,
                bbox: null,
              },
              {
                field_name: 'total',
                value: '5400.00',
                reviewed_value: null,
                confidence: 0.96,
                needs_review: false,
                bbox: null,
              },
            ];
            detail.line_items = [
              {
                position: 1,
                description: 'Freight Charges',
                quantity: '1',
                rate: '5000.00',
                amount: '5000.00',
                confidence: 0.95,
              },
            ];
            detail.validation_issues = [
              {
                rule: 'invalid_gstin',
                severity: 'warning',
                field_name: 'gstin',
                message: 'GSTIN confidence is low (0.72). Please verify.',
              },
            ];
          }
        }, 2000);
      }
    }, 1500);
  }

  async getDocuments(
    params: GetDocumentsParams = {}
  ): Promise<DocumentsListResponse> {
    await delay(150);
    const { status, page = 1, page_size = 20, q } = params;

    let filtered = [...this.items];

    if (status) {
      filtered = filtered.filter((doc) => doc.status === status);
    }

    if (q) {
      const lowerQ = q.toLowerCase();
      filtered = filtered.filter(
        (doc) =>
          doc.filename.toLowerCase().includes(lowerQ) ||
          doc.vendor_name?.toLowerCase().includes(lowerQ) ||
          doc.invoice_number?.toLowerCase().includes(lowerQ)
      );
    }

    const total = filtered.length;
    const startIndex = (page - 1) * page_size;
    const paginatedItems = filtered.slice(startIndex, startIndex + page_size);

    return {
      items: paginatedItems,
      page,
      page_size,
      total,
      counts: this.calculateCounts(),
    };
  }

  async getDocumentById(id: string): Promise<DocumentDetail> {
    await delay(150);
    const detail = this.detailsMap.get(id);
    if (!detail) {
      throw {
        status: 404,
        error: { code: 'not_found', message: `Document with ID ${id} not found` },
      };
    }
    return clone(detail);
  }

  async updateDocumentFields(
    id: string,
    req: PatchDocumentFieldsRequest
  ): Promise<DocumentDetail> {
    await delay(250);
    const detail = this.detailsMap.get(id);
    if (!detail) {
      throw {
        status: 404,
        error: { code: 'not_found', message: `Document with ID ${id} not found` },
      };
    }

    if (detail.status !== 'needs_review') {
      throw {
        status: 409,
        error: {
          code: 'conflict',
          message: `Cannot update fields when status is '${detail.status}'`,
        },
      };
    }

    // Update fields
    if (req.fields) {
      for (const [key, val] of Object.entries(req.fields)) {
        const field = detail.fields.find((f) => f.field_name === key);
        if (field) {
          field.reviewed_value = val;
          field.needs_review = false;
        } else {
          detail.fields.push({
            field_name: key,
            value: val,
            reviewed_value: val,
            confidence: 1.0,
            needs_review: false,
            bbox: null,
          });
        }
      }
    }

    // Update line items
    if (req.line_items) {
      detail.line_items = req.line_items;
    }

    // Re-evaluate validation issues for total mismatch
    const getEffectiveValue = (fieldName: string) => {
      const f = detail.fields.find((x) => x.field_name === fieldName);
      return f ? f.reviewed_value ?? f.value : null;
    };

    const subtotalStr = getEffectiveValue('subtotal');
    const taxStr = getEffectiveValue('tax');
    const totalStr = getEffectiveValue('total');

    if (subtotalStr && taxStr && totalStr) {
      const subtotal = parseFloat(subtotalStr);
      const tax = parseFloat(taxStr);
      const total = parseFloat(totalStr);

      if (Math.abs(subtotal + tax - total) < 0.01) {
        detail.validation_issues = detail.validation_issues.filter(
          (issue) => issue.rule !== 'total_mismatch'
        );
      }
    }

    detail.updated_at = new Date().toISOString();

    // Sync back to item list
    const item = this.items.find((i) => i.id === id);
    if (item) {
      item.total = totalStr;
      item.vendor_name = getEffectiveValue('vendor_name');
      item.invoice_number = getEffectiveValue('invoice_number');
      item.currency = getEffectiveValue('currency');
      item.issues_count = detail.validation_issues.length;
      item.low_confidence_count = detail.fields.filter(
        (f) => f.needs_review
      ).length;
      item.updated_at = detail.updated_at;
    }

    return clone(detail);
  }

  async approveDocument(
    id: string,
    options: ApproveDocumentRequest = {}
  ): Promise<DocumentDetail> {
    await delay(250);
    const detail = this.detailsMap.get(id);
    if (!detail) {
      throw {
        status: 404,
        error: { code: 'not_found', message: `Document with ID ${id} not found` },
      };
    }

    if (detail.status !== 'needs_review') {
      throw {
        status: 409,
        error: {
          code: 'conflict',
          message: `Cannot approve document with status '${detail.status}'`,
        },
      };
    }

    const blockingErrors = detail.validation_issues.filter(
      (i) => i.severity === 'error'
    );
    if (blockingErrors.length > 0 && !options.force) {
      throw {
        status: 409,
        error: {
          code: 'conflict',
          message: `Cannot approve document with blocking validation issues: ${blockingErrors
            .map((e) => e.message)
            .join('; ')}`,
        },
      };
    }

    detail.status = 'approved';
    detail.auto_approved = false;
    detail.updated_at = new Date().toISOString();

    const item = this.items.find((i) => i.id === id);
    if (item) {
      item.status = 'approved';
      item.updated_at = detail.updated_at;
    }

    return clone(detail);
  }

  async retryDocument(id: string): Promise<DocumentDetail> {
    await delay(250);
    const detail = this.detailsMap.get(id);
    if (!detail) {
      throw {
        status: 404,
        error: { code: 'not_found', message: `Document with ID ${id} not found` },
      };
    }

    if (detail.status !== 'failed') {
      throw {
        status: 409,
        error: {
          code: 'conflict',
          message: `Retry allowed only from 'failed' status`,
        },
      };
    }

    detail.status = 'queued';
    detail.error_message = null;
    detail.job = {
      status: 'queued',
      attempts: 0,
      max_attempts: 3,
      last_error: null,
    };
    detail.updated_at = new Date().toISOString();

    const item = this.items.find((i) => i.id === id);
    if (item) {
      item.status = 'queued';
      item.updated_at = detail.updated_at;
    }

    this.scheduleDocumentProcessing(id);
    return clone(detail);
  }

  async exportDocuments(params: ExportParams): Promise<Blob> {
    await delay(300);
    const approvedIds = this.items
      .filter((i) => i.status === (params.status || 'approved'))
      .map((i) => i.id);

    const targetIds = params.ids
      ? params.ids.split(',')
      : approvedIds;

    const exportData = targetIds
      .map((id) => this.detailsMap.get(id))
      .filter((d): d is DocumentDetail => d !== undefined);

    if (params.format === 'csv') {
      const header =
        'document_id,filename,vendor_name,invoice_number,invoice_date,gstin,currency,subtotal,tax,total,item_position,item_description,item_quantity,item_rate,item_amount\n';

      let rows = '';
      for (const doc of exportData) {
        const getVal = (name: string) => {
          const f = doc.fields.find((field) => field.field_name === name);
          return f ? f.reviewed_value ?? f.value ?? '' : '';
        };

        const docFields = [
          doc.id,
          doc.filename,
          getVal('vendor_name'),
          getVal('invoice_number'),
          getVal('invoice_date'),
          getVal('gstin'),
          getVal('currency'),
          getVal('subtotal'),
          getVal('tax'),
          getVal('total'),
        ];

        if (doc.line_items.length === 0) {
          rows += [...docFields, '', '', '', '', ''].map((v) => `"${v}"`).join(',') + '\n';
        } else {
          for (const item of doc.line_items) {
            rows +=
              [
                ...docFields,
                item.position,
                item.description || '',
                item.quantity || '',
                item.rate || '',
                item.amount || '',
              ]
                .map((v) => `"${v}"`)
                .join(',') + '\n';
          }
        }
      }
      return new Blob([header + rows], { type: 'text/csv' });
    } else {
      const jsonObj = exportData.map((doc) => {
        const fieldsObj: Record<string, string | null> = {};
        for (const f of doc.fields) {
          fieldsObj[f.field_name] = f.reviewed_value ?? f.value;
        }
        return {
          document_id: doc.id,
          filename: doc.filename,
          fields: fieldsObj,
          line_items: doc.line_items,
        };
      });
      return new Blob([JSON.stringify(jsonObj, null, 2)], {
        type: 'application/json',
      });
    }
  }
}

export const mockDatabase = new MockDatabase();
