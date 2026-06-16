import { useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { useQuery } from '@tanstack/react-query';
import {
  AppShell,
  Badge,
  Button,
  Code,
  Group,
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

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

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

async function fetchEvents(params: URLSearchParams): Promise<{ items: AuditEvent[]; count: number }> {
  const res = await fetch(`/api/audit?${params.toString()}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function fetchEventTypes(): Promise<string[]> {
  const res = await fetch('/api/audit/event-types');
  if (!res.ok) return [];
  return res.json();
}

function resultColor(r: string) {
  return r === 'success' ? 'teal' : 'red';
}

function App() {
  const [actor, setActor] = useState('');
  const [eventType, setEventType] = useState<string | null>(null);
  const [resource, setResource] = useState('');
  const [result, setResult] = useState<string | null>(null);

  const typesQuery = useQuery({ queryKey: ['audit-types'], queryFn: fetchEventTypes });

  const params = useMemo(() => {
    const p = new URLSearchParams();
    if (actor) p.set('actor', actor);
    if (eventType) p.set('event_type', eventType);
    if (resource) p.set('resource', resource);
    if (result) p.set('result', result);
    p.set('limit', '200');
    return p;
  }, [actor, eventType, resource, result]);

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
                      <Table.Td>{new Date(e.occurred_at).toLocaleString()}</Table.Td>
                      <Table.Td><Badge variant="light">{e.event_type}</Badge></Table.Td>
                      <Table.Td>{e.actor_id ?? '—'}</Table.Td>
                      <Table.Td>{e.resource ?? '—'}</Table.Td>
                      <Table.Td><Badge color={resultColor(e.result)}>{e.result}</Badge></Table.Td>
                      <Table.Td><Code>{e.corr_id ?? '—'}</Code></Table.Td>
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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <MantineProvider>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </MantineProvider>
);
