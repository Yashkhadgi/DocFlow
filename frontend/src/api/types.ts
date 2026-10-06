/**
 * REST API Types as defined in V1_BUILD_PLAN.md Section 5.3
 */

export type DocumentStatus =
  | 'queued'
  | 'processing'
  | 'needs_review'
  | 'approved'
  | 'failed'
  | 'duplicate';

export interface ApiErrorDetail {
  code:
    | 'unauthorized'
    | 'not_found'
    | 'validation_error'
    | 'file_too_large'
    | 'unsupported_type'
    | 'conflict'
    | 'internal_error'
    | string;
  message: string;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface HealthResponse {
  status: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface UploadResultItem {
  filename: string;
  document_id: string | null;
  status: DocumentStatus | null;
  duplicate_of_id: string | null;
  error: ApiErrorDetail | null;
}

export interface UploadResponse {
  results: UploadResultItem[];
}

export interface DocumentListItem {
  id: string;
  filename: string;
  status: DocumentStatus;
  auto_approved: boolean;
  vendor_name: string | null;
  invoice_number: string | null;
  currency: string | null;
  total: string | null;
  issues_count: number;
  low_confidence_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentStatusCounts {
  queued: number;
  processing: number;
  needs_review: number;
  approved: number;
  failed: number;
  duplicate: number;
}

export interface DocumentsListResponse {
  items: DocumentListItem[];
  page: number;
  page_size: number;
  total: number;
  counts: DocumentStatusCounts;
}

export interface GetDocumentsParams {
  status?: DocumentStatus;
  page?: number;
  page_size?: number;
  q?: string;
}

export interface BoundingBox {
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ExtractedField {
  field_name: string;
  value: string | null;
  reviewed_value: string | null;
  confidence: number;
  needs_review: boolean;
  bbox: BoundingBox | null;
}

export interface LineItem {
  position: number;
  description: string | null;
  quantity: string | null;
  rate: string | null;
  amount: string | null;
  confidence?: number | null;
}

export type ValidationRule =
  | 'total_mismatch'
  | 'line_items_mismatch'
  | 'invalid_gstin'
  | 'invalid_date'
  | 'missing_required'
  | string;

export interface ValidationIssue {
  rule: ValidationRule;
  severity: 'error' | 'warning';
  field_name: string | null;
  message: string;
}

export interface DocumentJob {
  status: 'queued' | 'processing' | 'succeeded' | 'failed';
  attempts: number;
  max_attempts: number;
  last_error: string | null;
}

export interface DocumentDetail {
  id: string;
  filename: string;
  mime_type: string;
  status: DocumentStatus;
  auto_approved: boolean;
  duplicate_of_id: string | null;
  duplicate_reason: 'same_file' | 'same_invoice' | string | null;
  error_message: string | null;
  file_url: string | null;
  fields: ExtractedField[];
  line_items: LineItem[];
  validation_issues: ValidationIssue[];
  job: DocumentJob | null;
  created_at: string;
  updated_at: string;
}

export interface PatchDocumentFieldsRequest {
  fields?: Record<string, string | null>;
  line_items?: LineItem[];
}

export interface ApproveDocumentRequest {
  force?: boolean;
}

export interface ExportParams {
  format: 'csv' | 'json';
  status?: DocumentStatus;
  ids?: string;
}
