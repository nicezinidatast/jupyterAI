/**
 * 인증 API 클라이언트 (얇은 fetch 래퍼).
 *
 * 설계 원칙:
 *  - 쿠키 기반 세션: 모든 요청에 `credentials: 'include'` 를 사용한다.
 *    서버가 /signup 또는 /login 응답으로 Set-Cookie(httpOnly) 를 내려주면
 *    브라우저가 이후 모든 요청에 쿠키를 자동 포함한다. JWT 를 localStorage 에
 *    저장하지 않아도 되므로 XSS 노출 위험이 없다.
 *  - 동일 오리진 상대 URL: 포털이 /api/* 를 백엔드로 프록시하므로
 *    절대 URL 없이 rooted 상대 경로만으로 동작한다.
 *    (개발: Vite proxy, 운영: Nginx upstream)
 *  - ApiError: 백엔드의 `detail` 문자열(예: "invalid_credentials")을 포함해
 *    호출자가 응답 본문을 직접 파싱하지 않고 상태 코드로 분기할 수 있게 한다.
 */
const BASE = '/api/auth';

/**
 * 인증 API 오류 클래스.
 *
 * status: HTTP 상태 코드 (401, 409, 422 등).
 * detail: 백엔드 응답 body 의 `detail` 필드 또는 HTTP statusText.
 *         호출자는 e.status 로 분기하고, e.detail 로 로그/디버깅에 활용한다.
 */
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

/**
 * 내부 공통 fetch 헬퍼.
 *
 * - 기본 메서드: POST. GET 이 필요한 엔드포인트(/me)는 init 에서 override 한다.
 * - Content-Type: 'application/json' 을 기본으로 설정하되, init.headers 로 덮어쓸 수 있다.
 * - 204 No Content: 본문 없이 성공하는 엔드포인트(로그아웃 등)를 대비해
 *   undefined 를 T 로 캐스팅해 반환한다.
 * - 에러 응답: JSON 파싱을 시도해 `detail` 을 추출하고, 파싱 실패 시 statusText 를 사용한다.
 */
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
      detail = body.detail ?? detail; // FastAPI 의 HTTPException detail 필드를 우선한다
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/**
 * 인증된 사용자 정보 타입.
 *
 * email 필드는 실제로 username 을 담는다(백엔드 AuthUser 스키마가
 * email 키를 유지하지만 내부망에서는 이메일 없이 username 만 사용한다).
 * display_name: 프로필 표시명. 설정하지 않으면 null.
 * roles: 역할 목록(예: ['admin', 'auditor']). 없으면 undefined.
 */
export type AuthUser = {
  email: string; // holds the username
  display_name: string | null;
  roles?: string[];
};

/**
 * 인증 API 메서드 모음.
 *
 * signup:
 *  회원가입 즉시 활성화 + 자동 로그인이다. 서버가 응답 시 세션 쿠키를 발급하므로
 *  호출자는 성공 시 바로 워크스페이스로 리다이렉트하면 된다.
 *
 * login:
 *  POST /api/auth/login → 세션 쿠키 수신. 실패 시 401 ApiError.
 *
 * me:
 *  GET /api/auth/me → 현재 세션의 사용자 정보 반환.
 *  마운트 시 기존 세션 확인에 사용한다. 401 이면 세션 없음.
 */
export const authApi = {
  // Free signup: id (username) + password. Active immediately + auto-logged-in
  // (the backend sets the session cookie), so callers just redirect on success.
  // 자유 회원가입: username + password. 가입 즉시 활성화 + 자동 로그인(백엔드가 세션 쿠키 발급).
  // 성공 시 호출자는 단순히 리다이렉트하면 된다.
  signup: (body: { username: string; password: string }) =>
    request<{ user: AuthUser }>('/signup', { body: JSON.stringify(body) }),

  login: (body: { username: string; password: string }) =>
    request<{ user: AuthUser }>('/login', { body: JSON.stringify(body) }),

  // GET — no body. Used on mount to skip the form for already-authenticated users.
  // GET 요청 — body 없음. 마운트 시 이미 인증된 사용자를 식별해 로그인 폼을 건너뛴다.
  me: () => request<{ user: AuthUser }>('/me', { method: 'GET' }),
};

/**
 * 로그인 성공 후 이동할 분석 워크스페이스 URL.
 * 상수로 분리해 두면 경로가 바뀔 때 이 파일 한 곳만 수정하면 된다.
 */
/** Where we send the browser once a session cookie exists. */
export const ANALYST_URL = '/analyst/';

/**
 * 세션 쿠키가 존재하는 상태에서 분석 워크스페이스로 이동한다.
 * window.location.assign 을 사용하는 이유: SPA 라우터(React Router 등)가 없고
 * 감사자 콘솔과 로그인 페이지가 별도 Vite 빌드이므로 하드 네비게이션이 필요하다.
 */
export function goToAnalyst() {
  window.location.assign(ANALYST_URL);
}
