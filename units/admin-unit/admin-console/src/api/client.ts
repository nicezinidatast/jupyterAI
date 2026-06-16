/**
 * Thin fetch wrapper. We deliberately avoid axios so the build stays small.
 * All endpoints route through the SPA's reverse proxy (nginx), so a relative
 * URL is sufficient.
 */
const BASE = '/api/admin';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
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
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type User = {
  user_id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  roles: string[];
  created_at: string;
};

export type Connection = {
  connection_id: string;
  name: string;
  engine: string;
  host: string;
  port: number;
  database: string | null;
  is_active: boolean;
  created_at: string;
  grants: { subject_user_id: string | null; subject_role: string | null; action: string }[];
};

export type PiiPattern = {
  pattern_id: string;
  name: string;
  kind: 'name' | 'rrn' | 'phone' | 'email' | 'custom';
  regex: string;
  is_active: boolean;
};

export type Backup = {
  backup_id: string;
  target: string;
  started_at: string;
  ended_at: string | null;
  state: 'running' | 'success' | 'failed';
  size_bytes: number | null;
  location: string | null;
  error: string | null;
};

export type DashboardStats = {
  users: number;
  active_users: number;
  connections: number;
  pii_patterns: number;
  notebooks: number;
  audit_events_last_24h: number;
  backups_successful: number;
  backups_failed: number;
};

// --- Users -------------------------------------------------------------
export const usersApi = {
  list: () => request<User[]>('/users'),
  create: (body: { email: string; display_name?: string; roles?: string[] }) =>
    request<User>('/users', { method: 'POST', body: JSON.stringify(body) }),
  setRoles: (userId: string, roles: string[]) =>
    request<User>(`/users/${userId}/roles`, {
      method: 'PATCH',
      body: JSON.stringify({ roles }),
    }),
  remove: (userId: string) =>
    request<void>(`/users/${userId}`, { method: 'DELETE' }),
};

export type TestConnectionResult = {
  ok: boolean;
  latency_ms: number | null;
  reason: string | null;
};

// --- Connections -------------------------------------------------------
export const connectionsApi = {
  list: () => request<Connection[]>('/connections'),
  create: (body: { name: string; engine: string; host: string; port: number; database?: string }) =>
    request<Connection>('/connections', { method: 'POST', body: JSON.stringify(body) }),
  remove: (id: string) =>
    request<void>(`/connections/${id}`, { method: 'DELETE' }),
  test: (id: string) =>
    request<TestConnectionResult>(`/connections/${id}/test`, { method: 'POST' }),
};

// --- PII Patterns ------------------------------------------------------
export const piiApi = {
  list: () => request<PiiPattern[]>('/pii-patterns'),
  create: (body: { name: string; kind: string; regex: string }) =>
    request<PiiPattern>('/pii-patterns', { method: 'POST', body: JSON.stringify(body) }),
  toggle: (id: string) =>
    request<PiiPattern>(`/pii-patterns/${id}`, { method: 'PATCH' }),
  remove: (id: string) =>
    request<void>(`/pii-patterns/${id}`, { method: 'DELETE' }),
};

// --- Backups -----------------------------------------------------------
export const backupsApi = {
  list: () => request<Backup[]>('/backups'),
  run: () => request<Backup>('/backups/run', { method: 'POST' }),
};

// --- Stats -------------------------------------------------------------
export const statsApi = {
  dashboard: () => request<DashboardStats>('/stats'),
};
