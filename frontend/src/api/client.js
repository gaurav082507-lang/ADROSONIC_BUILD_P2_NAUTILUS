// Client API wrapper handling §7.2 standard error shape and multipart payloads

export class ApiError extends Error {
  constructor(status, error_code, details = {}, message = "") {
    super(message || error_code);
    this.status = status;
    this.error_code = error_code;
    this.details = details;
  }
}

function getToken() {
  try { return sessionStorage.getItem('lucen_token'); } catch { return null; }
}

export async function fetchClient(endpoint, options = {}) {
  const useMocks = import.meta.env.VITE_USE_MOCKS === "1";

  if (useMocks) {
    const mocks = await import('../mocks/handlers.js');
    return mocks.handleMock(endpoint, options);
  }

  const headers = { ...options.headers };
  // Only set application/json if not sending FormData multipart
  if (!(options.body instanceof FormData)) {
    if (!headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
  }
  // Attach Bearer token if present
  const tok = getToken();
  if (tok && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${tok}`;
  }

  const res = await fetch(`/api/v1${endpoint}`, {
    ...options,
    headers
  });

  if (res.status === 401) {
    // Clear stale session and redirect to login
    try { sessionStorage.clear(); } catch {}
    window.location.href = '/login';
    throw new ApiError(401, 'NOT_AUTHENTICATED', {}, 'Session expired. Please log in again.');
  }

  if (!res.ok) {
    let errBody = {};
    try {
      errBody = await res.json();
    } catch {
      throw new ApiError(res.status, 'UNKNOWN_ERROR', {}, 'Network or server error');
    }
    const errObj = errBody.error || {};
    throw new ApiError(
      res.status,
      errObj.code || 'UNKNOWN_ERROR',
      errObj.details || {},
      errObj.message || 'An error occurred'
    );
  }

  if (res.status === 204) return null;
  return res.json();
}
