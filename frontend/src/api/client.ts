import { mockDatabase } from './mock/mockAdapter';
import type {
  ApproveDocumentRequest,
  AuthResponse,
  DocumentDetail,
  DocumentsListResponse,
  ExportParams,
  GetDocumentsParams,
  HealthResponse,
  LoginRequest,
  PatchDocumentFieldsRequest,
  RegisterRequest,
  UploadResponse,
  User,
} from './types';

// Helper to determine if mock mode is active
export function isMockMode(): boolean {
  const envMock = import.meta.env.VITE_USE_MOCK;
  if (envMock === undefined || envMock === null || envMock === '') {
    return true; // Default to mock mode for early frontend dev if not set
  }
  return String(envMock).toLowerCase() === 'true';
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const TOKEN_KEY = 'docflow_access_token';

// In-memory token store backed by localStorage
let memoryToken: string | null = localStorage.getItem(TOKEN_KEY);

export function getAuthToken(): string | null {
  return memoryToken;
}

export function setAuthToken(token: string | null): void {
  memoryToken = token;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function logout(): void {
  setAuthToken(null);
  window.location.href = '/login';
}

/**
 * Standard HTTP Fetch wrapper for real backend API calls
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const token = getAuthToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    logout();
    throw {
      status: 401,
      error: { code: 'unauthorized', message: 'Session expired or invalid token' },
    };
  }

  if (!response.ok) {
    let errData;
    try {
      errData = await response.json();
    } catch {
      errData = {
        error: {
          code: 'internal_error',
          message: `HTTP ${response.status}: ${response.statusText}`,
        },
      };
    }
    throw { status: response.status, ...errData };
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response as unknown as T;
}

/**
 * Endpoint 1: GET /health
 */
export async function getHealth(): Promise<HealthResponse> {
  if (isMockMode()) {
    return mockDatabase.getHealth();
  }
  return apiFetch<HealthResponse>('/health');
}

/**
 * Endpoint 2: POST /auth/register
 */
export async function register(req: RegisterRequest): Promise<User> {
  if (isMockMode()) {
    return mockDatabase.register(req);
  }
  return apiFetch<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

/**
 * Endpoint 3: POST /auth/login
 */
export async function login(req: LoginRequest): Promise<AuthResponse> {
  let authData: AuthResponse;
  if (isMockMode()) {
    authData = await mockDatabase.login(req);
  } else {
    authData = await apiFetch<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  }
  setAuthToken(authData.access_token);
  return authData;
}

/**
 * Endpoint 4: POST /documents/upload
 */
export async function uploadDocuments(files: File[]): Promise<UploadResponse> {
  if (isMockMode()) {
    return mockDatabase.uploadDocuments(files);
  }
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  return apiFetch<UploadResponse>('/documents/upload', {
    method: 'POST',
    body: formData,
  });
}

/**
 * Endpoint 5: GET /documents
 */
export async function getDocuments(
  params: GetDocumentsParams = {}
): Promise<DocumentsListResponse> {
  if (isMockMode()) {
    return mockDatabase.getDocuments(params);
  }
  const queryParams = new URLSearchParams();
  if (params.status) queryParams.set('status', params.status);
  if (params.page) queryParams.set('page', params.page.toString());
  if (params.page_size) queryParams.set('page_size', params.page_size.toString());
  if (params.q) queryParams.set('q', params.q);

  const queryString = queryParams.toString();
  const endpoint = `/documents${queryString ? `?${queryString}` : ''}`;
  return apiFetch<DocumentsListResponse>(endpoint);
}

/**
 * Endpoint 6: GET /documents/{id}
 */
export async function getDocumentById(id: string): Promise<DocumentDetail> {
  if (isMockMode()) {
    return mockDatabase.getDocumentById(id);
  }
  return apiFetch<DocumentDetail>(`/documents/${id}`);
}

/**
 * Endpoint 7: PATCH /documents/{id}/fields
 */
export async function updateDocumentFields(
  id: string,
  req: PatchDocumentFieldsRequest
): Promise<DocumentDetail> {
  if (isMockMode()) {
    return mockDatabase.updateDocumentFields(id, req);
  }
  return apiFetch<DocumentDetail>(`/documents/${id}/fields`, {
    method: 'PATCH',
    body: JSON.stringify(req),
  });
}

/**
 * Endpoint 8: POST /documents/{id}/approve
 */
export async function approveDocument(
  id: string,
  req: ApproveDocumentRequest = {}
): Promise<DocumentDetail> {
  if (isMockMode()) {
    return mockDatabase.approveDocument(id, req);
  }
  return apiFetch<DocumentDetail>(`/documents/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

/**
 * Endpoint 9: POST /documents/{id}/retry
 */
export async function retryDocument(id: string): Promise<DocumentDetail> {
  if (isMockMode()) {
    return mockDatabase.retryDocument(id);
  }
  return apiFetch<DocumentDetail>(`/documents/${id}/retry`, {
    method: 'POST',
  });
}

/**
 * Endpoint 10: GET /export
 */
export async function exportDocuments(params: ExportParams): Promise<Blob> {
  if (isMockMode()) {
    return mockDatabase.exportDocuments(params);
  }
  const queryParams = new URLSearchParams();
  queryParams.set('format', params.format);
  if (params.status) queryParams.set('status', params.status);
  if (params.ids) queryParams.set('ids', params.ids);

  const token = getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_BASE_URL}/export?${queryParams.toString()}`,
    { headers }
  );

  if (!response.ok) {
    throw {
      status: response.status,
      error: { code: 'export_failed', message: 'Failed to download export' },
    };
  }

  return response.blob();
}
