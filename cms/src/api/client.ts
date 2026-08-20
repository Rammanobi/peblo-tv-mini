import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import type { ApiErrorBody } from '../types/api';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000';
const TOKEN_KEY = 'peblo_cms_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export const http = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
});

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Normalized application-level error. UI components branch on `kind` to render
 * loading/empty/error/permission-denied states rather than treating every
 * failure as a generic error blob.
 */
export class ApiError extends Error {
  kind: 'unauthorized' | 'forbidden' | 'not_found' | 'conflict' | 'validation' | 'payload_too_large' | 'server' | 'network';
  status: number | null;
  details: ApiErrorBody['error']['details'];
  requestId: string | null;

  constructor(opts: {
    message: string;
    kind: ApiError['kind'];
    status: number | null;
    details?: ApiErrorBody['error']['details'];
    requestId?: string | null;
  }) {
    super(opts.message);
    this.name = 'ApiError';
    this.kind = opts.kind;
    this.status = opts.status;
    this.details = opts.details ?? [];
    this.requestId = opts.requestId ?? null;
  }
}

function mapError(err: AxiosError<ApiErrorBody>): ApiError {
  if (!err.response) {
    return new ApiError({
      message: 'Could not reach the Peblo API. Check your connection or that the backend is running.',
      kind: 'network',
      status: null,
    });
  }

  const status = err.response.status;
  const body = err.response.data;
  const envelope = body?.error;

  const kindByStatus: Record<number, ApiError['kind']> = {
    401: 'unauthorized',
    403: 'forbidden',
    404: 'not_found',
    409: 'conflict',
    413: 'payload_too_large',
    422: 'validation',
  };

  const kind = kindByStatus[status] ?? (status >= 500 ? 'server' : 'server');

  return new ApiError({
    message: envelope?.message ?? `Request failed with status ${status}.`,
    kind,
    status,
    details: envelope?.details ?? [],
    requestId: envelope?.request_id ?? null,
  });
}

http.interceptors.response.use(
  (res) => res,
  (err: AxiosError<ApiErrorBody>) => Promise.reject(mapError(err))
);

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.get<T>(url, config);
  return res.data;
}

export async function apiPost<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.post<T>(url, data, config);
  return res.data;
}

export async function apiPatch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.patch<T>(url, data, config);
  return res.data;
}

export async function apiDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.delete<T>(url, config);
  return res.data;
}
