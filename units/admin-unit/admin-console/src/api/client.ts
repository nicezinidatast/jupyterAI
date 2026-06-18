/**
 * 관리자 콘솔 API 클라이언트 (얇은 fetch 래퍼)
 *
 * axios 대신 브라우저 내장 fetch를 직접 사용한다. 이유:
 *   1) 번들 크기를 최소화한다 (axios는 약 15 KB gzip).
 *   2) 모든 요청은 SPA와 같은 오리진의 nginx 리버스 프록시를 거치므로
 *      절대 URL 없이 상대 경로('/api/admin')만으로 충분하다.
 *   3) credentials: 'include'로 쿠키 기반 세션을 유지한다.
 *      nginx가 /api/ 요청을 FastAPI 백엔드로 프록시하므로,
 *      브라우저 쿠키가 자동으로 전달된다.
 *
 * 에러 처리 전략:
 *   - HTTP 상태가 2xx가 아니면 무조건 Error를 던진다.
 *   - 응답 body가 JSON이면 FastAPI의 detail 필드를 에러 메시지로 쓴다.
 *   - 204 No Content는 body 파싱 없이 undefined를 반환한다(DELETE 응답에 해당).
 *
 * react-query와 연동 시 이 클라이언트 함수들을 queryFn/mutationFn에 직접 전달한다.
 */
const BASE = '/api/admin';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    // FastAPI는 실패 시 { detail: "..." } 형태의 JSON을 반환한다.
    // JSON 파싱에 실패하면(예: 게이트웨이 에러) statusText로 폴백한다.
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  // DELETE 성공 등 204 응답은 body가 없으므로 파싱을 건너뛴다.
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// 타입 정의 — 백엔드 Pydantic 스키마와 1:1 대응한다.
// 필드가 추가·변경될 때 여기도 함께 갱신해야 클라이언트 타입 안전성이 유지된다.
// ---------------------------------------------------------------------------

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
  /** grants: 이 커넥션에 접근 가능한 역할·사용자와 허용 액션의 목록 */
  grants: { subject_user_id: string | null; subject_role: string | null; action: string }[];
};

export type PiiPattern = {
  pattern_id: string;
  name: string;
  /** kind: 개인정보(PII) 유형 분류. custom은 관리자가 직접 정의한 패턴을 가리킨다. */
  kind: 'name' | 'rrn' | 'phone' | 'email' | 'custom';
  regex: string;
  is_active: boolean;
};

export type Backup = {
  backup_id: string;
  /** target: 백업 대상 식별자 (예: 'metadb', 'workspace', 'vault') */
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
  /** audit_events_last_24h: 최근 24시간 감사 이벤트 수 — 이상 행동 모니터링 지표 */
  audit_events_last_24h: number;
  backups_successful: number;
  backups_failed: number;
};

// --- Users -------------------------------------------------------------
// 사용자 CRUD + 역할 변경. setRoles는 PATCH로 전체 역할 배열을 교체한다(부분 업데이트 아님).
export const usersApi = {
  list: () => request<User[]>('/users'),
  // password: 초기 로그인 비밀번호. 백엔드가 bcrypt로 해싱해 저장한다. 이 값을 보내지 않으면
  // 생성된 사용자는 비밀번호 해시가 없어 로컬 로그인을 할 수 없다(OIDC 전용 사용자에만 해당).
  create: (body: { email: string; display_name?: string; roles?: string[]; password?: string }) =>
    request<User>('/users', { method: 'POST', body: JSON.stringify(body) }),
  setRoles: (userId: string, roles: string[]) =>
    request<User>(`/users/${userId}/roles`, {
      method: 'PATCH',
      body: JSON.stringify({ roles }),
    }),
  // resetPassword: 관리자가 사용자의 비밀번호를 새 값으로 초기화한다(현재 비밀번호 불요).
  // 백엔드가 bcrypt로 해싱해 저장하므로, 초기화 직후 그 비밀번호로 바로 로그인된다.
  resetPassword: (userId: string, password: string) =>
    request<{ ok: boolean }>(`/users/${userId}/password`, {
      method: 'PUT',
      body: JSON.stringify({ password }),
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
// 데이터 커넥션 관리. test()는 백엔드에서 실제 DB 접속을 시도하고 레이턴시를 반환한다.
// 테스트 결과는 서버 저장 없이 클라이언트 state(testResults)에서만 유지된다.
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
// PII(개인정보 식별 정보) 마스킹 정규식 관리.
// toggle()은 body 없이 PATCH를 보내고, 백엔드가 is_active를 반전시킨다.
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
// 백업 이력 조회 + 즉시 실행. run()은 백그라운드 작업을 시작하고 즉시 Backup 객체를 반환한다.
// 완료 여부는 list() 폴링(5초 간격)으로 추적한다.
export const backupsApi = {
  list: () => request<Backup[]>('/backups'),
  run: () => request<Backup>('/backups/run', { method: 'POST' }),
};

// --- Stats -------------------------------------------------------------
// 대시보드 통계. 10초 간격으로 폴링하므로 GET 한 번의 비용이 낮아야 한다.
export const statsApi = {
  dashboard: () => request<DashboardStats>('/stats'),
};
