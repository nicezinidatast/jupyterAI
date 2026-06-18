/**
 * 관리자 콘솔 SPA 루트 — 앱 전체를 조립하는 진입점.
 *
 * 구조적 결정:
 *   1) MantineProvider — UI 컴포넌트 테마 컨텍스트 공급.
 *      defaultColorScheme="light"로 고정해 다크 모드 토글을 지원하지 않는다.
 *      내부망 전용 도구이므로 단순성을 우선시했다.
 *
 *   2) RequireAuth — 세션 확인이 가장 바깥에 위치한다.
 *      인증 확인이 완료되기 전에는 QueryClientProvider와 BrowserRouter를
 *      전혀 렌더링하지 않아, 미인증 상태에서 API 요청이 발화되는 것을 원천 차단한다.
 *
 *   3) QueryClientProvider — react-query 캐시 컨텍스트 공급.
 *      refetchOnWindowFocus를 전역 비활성화한다. 관리자 탭을 잠깐 벗어났다 돌아올 때
 *      불필요한 re-fetch가 폭발적으로 발생하는 것을 막기 위해서다.
 *
 *   4) BrowserRouter(basename="/admin") — nginx가 /admin/ 접두사 아래 서빙하므로
 *      basename을 명시해야 Link·useLocation이 올바른 경로를 다룬다.
 */
import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { AppShell, Burger, Group, Loader, MantineProvider, NavLink, Text, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import '@mantine/core/styles.css';

import { Dashboard } from './pages/Dashboard';
import { Users } from './pages/Users';
import { Connections } from './pages/Connections';
import { PiiPatterns } from './pages/PiiPatterns';
import { Backups } from './pages/Backups';

// refetchOnWindowFocus 전역 비활성화 — 이유는 파일 상단 JSDoc 참조
const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

// ---------------------------------------------------------------------------
// Auth guard — 마운트 시 /api/auth/me를 호출해 세션 유효성을 검증한다.
// 401 또는 네트워크 오류 시 /login/으로 즉시 리다이렉트한다.
// 검증이 완료되기 전에는 children을 렌더링하지 않아 깜빡임(flash of unauthenticated content)을 방지한다.
//
// 이펙트를 두 개로 분리한 이유:
//   - 첫 번째: fetch 결과에 따라 authState를 결정한다.
//   - 두 번째: authState가 'redirect'로 바뀐 뒤 window.location.assign을 실행한다.
//     하나의 이펙트에서 fetch 후 바로 assign하면 React 경고 없이 동작하지만,
//     상태 머신을 명확히 표현하기 위해 분리했다.
// ---------------------------------------------------------------------------
type AuthState = 'loading' | 'ok' | 'redirect';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>('loading');

  // 세션 확인: credentials: 'include'로 쿠키를 전송해 백엔드가 세션을 검증한다.
  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => {
        if (r.status === 401) {
          setAuthState('redirect');
        } else if (!r.ok) {
          // 401 외의 서버 오류(500 등)도 로그인 페이지로 보낸다.
          // 잘못된 상태에서 관리 화면이 열리는 것보다 재로그인이 안전하다.
          setAuthState('redirect');
        } else {
          setAuthState('ok');
        }
      })
      .catch(() => setAuthState('redirect'));
  }, []);

  // authState 변화를 감지해 리다이렉트를 수행한다.
  // window.location.assign은 히스토리 스택을 교체하므로 뒤로가기로 돌아올 수 없다.
  useEffect(() => {
    if (authState === 'redirect') {
      window.location.assign('/login/');
    }
  }, [authState]);

  // 확인 중이거나 리다이렉트 대기 중일 때 스피너를 보여 준다.
  // 'redirect' 상태에서도 Loader를 유지해 레이아웃 깜빡임을 최소화한다.
  if (authState === 'loading' || authState === 'redirect') {
    return (
      <Group justify="center" align="center" style={{ height: '100vh' }}>
        <Loader />
      </Group>
    );
  }

  return <>{children}</>;
}

// 사이드바 네비게이션 항목 목록.
// to 경로는 BrowserRouter의 basename("/admin") 기준 상대 경로다.
const NAV = [
  { to: '/', label: '대시보드', emoji: '📊' },
  { to: '/users', label: '사용자', emoji: '👥' },
  { to: '/connections', label: '데이터 커넥션', emoji: '🔌' },
  { to: '/pii', label: 'PII 패턴', emoji: '🔒' },
  { to: '/backups', label: '백업', emoji: '💾' },
];

/**
 * Shell — AppShell 기반의 공통 레이아웃 컴포넌트.
 *
 * Mantine의 AppShell은 헤더·사이드바·메인 영역을 선언적으로 배치한다.
 * breakpoint="sm" 미만에서는 사이드바가 자동 숨겨지고 Burger 버튼으로 토글된다.
 *
 * active 판별 로직:
 *   - 루트('/')는 정확히 일치할 때만 active로 표시한다.
 *     startsWith('/')를 쓰면 모든 경로가 루트와 매칭되기 때문이다.
 *   - 나머지 경로는 startsWith를 써서 하위 경로(예: /users/123)도 active로 표시한다.
 */
function Shell() {
  const [opened, { toggle }] = useDisclosure();
  const loc = useLocation();

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            {/* sm 미만 화면에서만 표시되는 햄버거 버튼 — 사이드바 토글 */}
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={4}>🛠️ Dataplatform Admin</Title>
          </Group>
          <Text size="sm" c="dimmed">내부망 데이터 분석 플랫폼 v0.1.0</Text>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            component={Link}
            to={item.to}
            label={`${item.emoji}  ${item.label}`}
            active={
              item.to === '/'
                ? loc.pathname === '/'
                : loc.pathname.startsWith(item.to)
            }
            variant="light"
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/pii" element={<PiiPatterns />} />
          <Route path="/backups" element={<Backups />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}

// React.StrictMode: 개발 환경에서 이펙트를 두 번 실행해 사이드이펙트 문제를 조기 감지한다.
// 프로덕션 빌드에서는 동작하지 않으며 성능에 영향을 주지 않는다.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="light">
      <RequireAuth>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter basename="/admin">
            <Shell />
          </BrowserRouter>
        </QueryClientProvider>
      </RequireAuth>
    </MantineProvider>
  </React.StrictMode>
);
