import type { ZodType } from 'zod';
import { logout, getToken } from './session';
import { apiErrorSchema } from './schemas';
export class ApiClientError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}
const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
async function request<T>(path: string, init: RequestInit = {}, schema?: ZodType<T>): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type'))
    headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, { ...init, headers });
  } catch {
    throw new ApiClientError('NETWORK_DOWN', 'Backend unreachable', 0);
  }
  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    const parsed = apiErrorSchema.safeParse(body);
    const err = parsed.success ? parsed.data.error : undefined;
    const code = err?.code || `HTTP_${response.status}`;
    if (response.status === 401) {
      logout();
      window.location.assign('/login');
    }
    if (response.status === 403)
      throw new ApiClientError(
        'FORBIDDEN_ROLE',
        err?.message || "You don't have access to this page.",
        403,
        err?.details,
      );
    throw new ApiClientError(code, err?.message || 'Request failed', response.status, err?.details);
  }
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get('content-type') || '';
  const value: unknown = contentType.includes('application/json')
    ? await response.json()
    : await response.blob();
  if (!schema) return value as T;
  const parsed = schema.safeParse(value);
  if (!parsed.success) {
    console.error(`[Lucen AI] Contract mismatch at ${path}`, parsed.error.flatten());
    throw new ApiClientError(
      'CONTRACT_MISMATCH',
      `Contract mismatch at ${path}`,
      200,
      parsed.error.flatten(),
    );
  }
  return parsed.data;
}
export const api = {
  get: <T>(path: string, schema?: ZodType<T>) => request<T>(path, {}, schema),
  post: <T>(path: string, body?: unknown, schema?: ZodType<T>) =>
    request<T>(
      path,
      { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body ?? {}) },
      schema,
    ),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
