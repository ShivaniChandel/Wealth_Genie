import { supabase } from '@/lib/supabase';
import type { ErrorResponse } from './types';

/**
 * Base URL for the FastAPI backend, e.g. `http://localhost:8000`.
 * The `/api/v1` prefix (docs/07_API_SPECIFICATION.md) is added by apiFetch,
 * so callers pass paths like `/documents/upload`, not `/api/v1/documents/upload`.
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * Thrown by apiFetch for any non-2xx response. Mirrors the backend's
 * standard error schema (ErrorResponse) so callers can branch on `.status`
 * or display `.detail` directly.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly error: string;
  readonly detail: string;

  constructor(status: number, body: Partial<ErrorResponse>) {
    const detail = body.detail || 'The request failed.';
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.error = body.error || 'Error';
    this.detail = detail;
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, 'body'> {
  /**
   * Plain objects are JSON-serialized automatically (Content-Type set to
   * application/json). Pass a `FormData` instance as-is for multipart
   * requests (e.g. document upload) — it is forwarded untouched so the
   * browser sets its own boundary-aware Content-Type.
   */
  body?: BodyInit | Record<string, unknown> | null;
}

function isJsonSerializableBody(body: unknown): body is Record<string, unknown> {
  return (
    body !== null &&
    typeof body === 'object' &&
    !(body instanceof FormData) &&
    !(body instanceof Blob) &&
    !(body instanceof ArrayBuffer) &&
    !(body instanceof URLSearchParams)
  );
}

async function getAccessToken(): Promise<string> {
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();

  if (error || !session) {
    throw new ApiError(401, {
      error: 'Unauthorized',
      detail: 'No active session. Please sign in again.',
      status_code: 401,
    });
  }

  return session.access_token;
}

/**
 * Typed fetch wrapper for the FastAPI backend (`/api/v1/*`).
 *
 * Every protected endpoint (all of them except register/login, which the
 * frontend never calls — see docs/14_AUTH_FLOW.md) requires a Supabase JWT.
 * This wrapper fetches the current session and attaches it automatically so
 * callers never handle tokens or headers directly.
 *
 * @example
 *   const status = await apiFetch<AnalysisJobStatusResponse>(`/analysis/status/${jobId}`);
 *   const upload = await apiFetch<UploadResponse>('/documents/upload', { method: 'POST', body: formData });
 *   const reply = await apiFetch<ChatResponse>('/chat', { method: 'POST', body: { message, conversation_history } });
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const accessToken = await getAccessToken();
  const { body, headers, ...rest } = options;

  const finalHeaders = new Headers(headers);
  finalHeaders.set('Authorization', `Bearer ${accessToken}`);

  let finalBody: BodyInit | null | undefined;
  if (isJsonSerializableBody(body)) {
    finalHeaders.set('Content-Type', 'application/json');
    finalBody = JSON.stringify(body);
  } else {
    finalBody = body as BodyInit | null | undefined;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...rest,
    headers: finalHeaders,
    body: finalBody,
  });

  // Matches POST /auth/logout, which returns 204 with no body.
  if (response.status === 204) {
    return undefined as T;
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError(response.status, (payload as Partial<ErrorResponse>) ?? {});
  }

  return payload as T;
}