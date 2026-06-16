/**
 * Thin fetch wrapper for the auth endpoints. Cookie-based session: every
 * request sends `credentials: 'include'` so the httpOnly session cookie set by
 * /signup and /login rides along. All endpoints live under the same origin
 * (the portal proxies /api/* to the backend), so a rooted relative URL works.
 *
 * On error we surface the backend's `detail` string (e.g. "invalid_credentials")
 * via an ApiError so callers can branch on it without re-parsing the response.
 */
const BASE = '/api/auth';

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`${status} ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type AuthUser = {
  email: string; // holds the username
  display_name: string | null;
  roles?: string[];
};

export const authApi = {
  // Free signup: id (username) + password. Active immediately + auto-logged-in
  // (the backend sets the session cookie), so callers just redirect on success.
  signup: (body: { username: string; password: string }) =>
    request<{ user: AuthUser }>('/signup', { body: JSON.stringify(body) }),

  login: (body: { username: string; password: string }) =>
    request<{ user: AuthUser }>('/login', { body: JSON.stringify(body) }),

  // GET — no body. Used on mount to skip the form for already-authenticated users.
  me: () => request<{ user: AuthUser }>('/me', { method: 'GET' }),
};

/** Where we send the browser once a session cookie exists. */
export const ANALYST_URL = '/analyst/';

export function goToAnalyst() {
  window.location.assign(ANALYST_URL);
}
