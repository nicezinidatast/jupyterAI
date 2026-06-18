/**
 * 감사자 콘솔(Auditor Console) 진입점.
 *
 * 구조 개요:
 *  - RequireAuth: 마운트 시 세션 쿠키를 검증하고, 미인증이면 /login/ 으로 리다이렉트한다.
 *    인증 확인이 끝나기 전까지 자식 컴포넌트를 렌더링하지 않으므로
 *    감사 로그 데이터를 비인가 사용자에게 순간이라도 노출하지 않는다.
 *  - QueryClientProvider: React Query(TanStack Query) 컨텍스트를 제공한다.
 *    refetchOnWindowFocus를 끈 이유: 탭 전환 때마다 대용량 감사 로그를 다시 가져오면
 *    네트워크 낭비가 크고, 이미 15초 자동 갱신(refetchInterval)이 있어 충분하다.
 *  - App: 필터 UI + 감사 이벤트 테이블. 감사 로그는 보안 민감 데이터이므로
 *    RequireAuth 아래에 배치해 인증 없이는 도달 불가능하게 한다.
 */
import React, { useEffect, useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { useQuery } from '@tanstack/react-query';
import {
  AppShell,
  Badge,
  Button,
  Code,
  Group,
  Loader,
  MantineProvider,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@mantine/core/styles.css';

/**
 * React Query 클라이언트 싱글톤.
 * refetchOnWindowFocus: false — 창 포커스 복귀 시 자동 재요청을 비활성화한다.
 * 감사 로그는 실시간성보다 주기적 폴링(refetchInterval)이 더 적합하기 때문이다.
 */
const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

// ---------------------------------------------------------------------------
// Auth guard — checks /api/auth/me on mount; redirects to /login/ on 401
// or any network failure. Children are not rendered until the check resolves.
// ---------------------------------------------------------------------------
// 인증 가드 — 마운트 시 /api/auth/me 를 호출해 세션 쿠키 유효성을 확인한다.
// 401 또는 네트워크 오류 시 /login/ 으로 리다이렉트한다.
// 확인이 완료되기 전까지는 자식 컴포넌트를 렌더링하지 않는다.
// ---------------------------------------------------------------------------
type AuthState = 'loading' | 'ok' | 'redirect';

/**
 * 인증 보호 래퍼 컴포넌트.
 *
 * 왜 두 개의 useEffect 를 사용하는가:
 *  1) 첫 번째 effect: 마운트 시 세션 확인 — fetch 결과에 따라 authState 를 갱신한다.
 *  2) 두 번째 effect: authState 가 'redirect' 로 바뀌면 즉시 /login/ 으로 이동한다.
 *     리다이렉트 로직을 별도 effect 로 분리한 이유는, fetch 콜백 내에서 직접
 *     window.location.assign 을 호출하면 React 상태 갱신 사이클을 건너뛰어
 *     Loader 를 표시하지 못하고 화면이 잠깐 비는 현상이 생길 수 있기 때문이다.
 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>('loading');

  useEffect(() => {
    // credentials: 'include' — httpOnly 세션 쿠키를 같은 오리진 요청에 포함시킨다.
    fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => {
        if (r.status === 401 || !r.ok) {
          setAuthState('redirect');
        } else {
          setAuthState('ok');
        }
      })
      .catch(() => setAuthState('redirect')); // 네트워크 오류도 미인증으로 처리한다
  }, []);

  useEffect(() => {
    if (authState === 'redirect') {
      window.location.assign('/login/');
    }
  }, [authState]);

  // 확인 중이거나 리다이렉트 예정인 경우 스피너만 표시한다.
  // 자식 컴포넌트(감사 데이터)를 절대 먼저 그리지 않는다.
  if (authState === 'loading' || authState === 'redirect') {
    return (
      <Group justify="center" align="center" style={{ height: '100vh' }}>
        <Loader />
      </Group>
    );
  }

  return <>{children}</>;
}

/**
 * 감사 이벤트 레코드 타입.
 *
 * 필드 설명:
 *  - occurred_at: ISO 8601 타임스탬프 문자열 (DB 저장값 그대로).
 *  - actor_id: 이벤트를 발생시킨 사용자 식별자(이메일 또는 시스템 ID). 시스템 이벤트이면 null.
 *  - resource: 조작 대상 리소스(예: "connection:sales_db"). 없으면 null.
 *  - result: 'success' | 'failure' — 뱃지 색상 분기에 사용한다.
 *  - corr_id: 상관관계 ID(correlation ID). 분산 트레이싱에서 같은 요청을 묶는 키.
 *  - payload: 이벤트별 추가 데이터. 구조가 이벤트 종류마다 달라 unknown 으로 처리한다.
 */
type AuditEvent = {
  id: number;
  occurred_at: string;
  event_type: string;
  actor_id: string | null;
  resource: string | null;
  result: 'success' | 'failure';
  corr_id: string | null;
  payload: Record<string, unknown>;
};

/**
 * 감사 이벤트 목록을 API 에서 가져온다.
 * URLSearchParams 로 필터(actor / event_type / resource / result / limit)를 전달한다.
 * credentials: 'include' 로 세션 쿠키를 포함하지 않으면 401 이 반환된다.
 */
async function fetchEvents(params: URLSearchParams): Promise<{ items: AuditEvent[]; count: number }> {
  const res = await fetch(`/api/audit?${params.toString()}`, { credentials: 'include' });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

/**
 * 드롭다운용 이벤트 종류 목록을 가져온다.
 * 오류 시 빈 배열을 반환해 필터 UI 가 깨지지 않게 한다(실패-소리 없이 처리).
 */
async function fetchEventTypes(): Promise<string[]> {
  const res = await fetch('/api/audit/event-types', { credentials: 'include' });
  if (!res.ok) return [];
  return res.json();
}

/**
 * 결과(result) 값에 따라 Mantine 색상 이름을 반환한다.
 * 'success' → teal(초록), 'failure' → red(빨강).
 */
function resultColor(r: string) {
  return r === 'success' ? 'teal' : 'red';
}

/**
 * 감사 로그 검색·표시 메인 컴포넌트.
 *
 * 주요 설계 결정:
 *  - params 를 useMemo 로 메모이제이션한다: actor/eventType/resource/result 중 하나라도
 *    바뀌면 새 URLSearchParams 객체를 만들고, 그 toString() 을 queryKey 에 포함시켜
 *    React Query 가 자동으로 재요청하게 한다. 의존성 배열을 직접 나열하는 것보다
 *    params 하나를 queryKey 에 넘기는 쪽이 캐시 키 관리가 단순하다.
 *  - refetchInterval: 15_000 (15초): 감사 콘솔은 실시간 모니터링 도구이므로
 *    사용자가 필터를 만지지 않아도 최신 이벤트를 주기적으로 가져온다.
 *  - limit: 200: 한 번에 너무 많은 레코드를 렌더링하면 DOM 성능이 떨어진다.
 *    더 많은 데이터가 필요한 경우 CSV 내보내기를 유도한다.
 */
function App() {
  const [actor, setActor] = useState('');
  const [eventType, setEventType] = useState<string | null>(null);
  const [resource, setResource] = useState('');
  const [result, setResult] = useState<string | null>(null);

  // 이벤트 종류 드롭다운 데이터 — 마운트 시 1회 가져온다.
  const typesQuery = useQuery({ queryKey: ['audit-types'], queryFn: fetchEventTypes });

  /**
   * 필터 상태가 바뀔 때마다 새 URLSearchParams 를 생성한다.
   * 빈 값은 서버에 보내지 않아 불필요한 WHERE 조건이 추가되지 않게 한다.
   */
  const params = useMemo(() => {
    const p = new URLSearchParams();
    if (actor) p.set('actor', actor);
    if (eventType) p.set('event_type', eventType);
    if (resource) p.set('resource', resource);
    if (result) p.set('result', result);
    p.set('limit', '200');
    return p;
  }, [actor, eventType, resource, result]);

  /**
   * 감사 이벤트 쿼리.
   * queryKey 에 params.toString() 을 넣어 필터가 바뀌면 자동으로 다시 요청한다.
   * refetchInterval: 15초 주기 자동 갱신 (헤더에도 표시됨).
   */
  const events = useQuery({
    queryKey: ['audit', params.toString()],
    queryFn: () => fetchEvents(params),
    refetchInterval: 15_000,
  });

  return (
    <AppShell header={{ height: 56 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={4}>🔍 Auditor Console</Title>
          <Text size="sm" c="dimmed">감사 로그 검색 · 15초 자동 갱신</Text>
        </Group>
      </AppShell.Header>

      <AppShell.Main>
        <Stack gap="md">
          {/* 필터 영역: 각 필드 변경 즉시 params 가 재계산되어 쿼리가 자동 갱신된다 */}
          <Group align="flex-end">
            <TextInput
              label="사용자 (이메일)"
              placeholder="alice.kim@example.test"
              value={actor}
              onChange={(e) => setActor(e.currentTarget.value)}
              w={260}
            />
            <Select
              label="이벤트 종류"
              data={typesQuery.data ?? []}
              clearable
              searchable
              value={eventType}
              onChange={setEventType}
              w={220}
            />
            <TextInput
              label="리소스 (부분 일치)"
              placeholder="connection:sales_db"
              value={resource}
              onChange={(e) => setResource(e.currentTarget.value)}
              w={240}
            />
            <Select
              label="결과"
              data={['success', 'failure']}
              clearable
              value={result}
              onChange={setResult}
              w={140}
            />
            {/* CSV 내보내기: 현재 필터 조건을 그대로 URL 파라미터로 전달한다.
                limit 제한 없이 전체 결과를 다운로드받을 수 있다. */}
            <Button
              component="a"
              href={`/api/audit/export.csv?${params.toString()}`}
              variant="light"
            >
              ⬇ CSV 내보내기
            </Button>
          </Group>

          {events.isLoading && <Text>불러오는 중…</Text>}
          {events.error && <Text c="red">{(events.error as Error).message}</Text>}

          {events.data && (
            <>
              {/* 총 건수와 표시 한도를 안내해 사용자가 필터 좁히기 또는 CSV 내보내기를 선택하게 한다 */}
              <Text c="dimmed" size="sm">
                {events.data.count}건 / 최대 200건 표시. 더 보려면 필터를 좁히거나 CSV 내보내기 사용.
              </Text>
              <Table striped withTableBorder withColumnBorders fz="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>발생 시각</Table.Th>
                    <Table.Th>종류</Table.Th>
                    <Table.Th>사용자</Table.Th>
                    <Table.Th>리소스</Table.Th>
                    <Table.Th>결과</Table.Th>
                    <Table.Th>상관관계</Table.Th>
                    <Table.Th>페이로드</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {events.data.items.map((e) => (
                    <Table.Tr key={e.id}>
                      {/* occurred_at 은 ISO 문자열이므로 Date 객체로 변환해 로컬 시각으로 표시한다 */}
                      <Table.Td>{new Date(e.occurred_at).toLocaleString()}</Table.Td>
                      <Table.Td><Badge variant="light">{e.event_type}</Badge></Table.Td>
                      {/* null 인 경우 em dash(—)로 표시해 빈 셀이 아님을 명확히 한다 */}
                      <Table.Td>{e.actor_id ?? '—'}</Table.Td>
                      <Table.Td>{e.resource ?? '—'}</Table.Td>
                      {/* resultColor 로 성공/실패를 색상으로 즉시 구분한다 */}
                      <Table.Td><Badge color={resultColor(e.result)}>{e.result}</Badge></Table.Td>
                      <Table.Td><Code>{e.corr_id ?? '—'}</Code></Table.Td>
                      {/* payload 는 이벤트마다 구조가 다르므로 JSON 직렬화해 원문 그대로 표시한다 */}
                      <Table.Td>
                        <Code style={{ fontSize: 11 }}>{JSON.stringify(e.payload)}</Code>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </>
          )}
        </Stack>
      </AppShell.Main>
    </AppShell>
  );
}

/**
 * React 앱 루트 렌더링.
 *
 * 컴포넌트 중첩 순서의 의미:
 *  MantineProvider → Mantine 테마/스타일 컨텍스트를 전체에 제공한다.
 *  RequireAuth     → 세션 확인 전에는 자식(QueryClientProvider + App)을 렌더링하지 않는다.
 *  QueryClientProvider → React Query 캐시를 App 에 공급한다.
 *  App             → 실제 감사 로그 UI. 인증된 사용자만 여기까지 도달한다.
 */
ReactDOM.createRoot(document.getElementById('root')!).render(
  <MantineProvider>
    <RequireAuth>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </RequireAuth>
  </MantineProvider>
);
