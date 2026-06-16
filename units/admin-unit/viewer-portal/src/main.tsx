import ReactDOM from 'react-dom/client';
import {
  AppShell,
  Badge,
  Card,
  Code,
  Group,
  Loader,
  MantineProvider,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import Plot from 'react-plotly.js';
import { BrowserRouter, Link, Route, Routes, useParams } from 'react-router-dom';
import '@mantine/core/styles.css';

const qc = new QueryClient();

type ShareLink = {
  link_id: string;
  notebook_id: string;
  permission: 'read' | 'execute' | 'edit';
  created_at: string;
  revoked_at: string | null;
  audience_roles: string[];
};

type ShareContent = {
  link_id: string;
  permission: 'read' | 'execute' | 'edit';
  notebook: { notebook_id: string; path: string };
  content: any;
  saved_at: string | null;
};

function permColor(p: string) {
  if (p === 'edit') return 'red';
  if (p === 'execute') return 'orange';
  return 'teal';
}

function ShareList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['shares'],
    queryFn: () =>
      fetch('/api/share').then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json() as Promise<ShareLink[]>;
      }),
  });

  return (
    <Stack p="md" gap="md">
      <Title order={3}>공유 받은 노트북</Title>
      <Text c="dimmed" size="sm">
        다른 사용자가 공유한 노트북 링크 목록. 클릭하면 결과를 읽기 전용으로 열람합니다.
      </Text>

      {isLoading && <Loader />}
      {error && <Text c="red">{(error as Error).message}</Text>}

      {data && (
        <Table striped withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>노트북</Table.Th>
              <Table.Th>권한</Table.Th>
              <Table.Th>대상 역할</Table.Th>
              <Table.Th>공유 시각</Table.Th>
              <Table.Th>액션</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.map((l) => (
              <Table.Tr key={l.link_id}>
                <Table.Td>{l.notebook_id.slice(0, 8)}…</Table.Td>
                <Table.Td><Badge color={permColor(l.permission)}>{l.permission}</Badge></Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    {l.audience_roles.map((r) => (
                      <Badge key={r} variant="light">{r}</Badge>
                    ))}
                  </Group>
                </Table.Td>
                <Table.Td>{new Date(l.created_at).toLocaleString()}</Table.Td>
                <Table.Td>
                  <Link to={`/share/${l.link_id}`}>열람</Link>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}

function ShareDetail() {
  const { id } = useParams();
  const { data, isLoading, error } = useQuery({
    queryKey: ['share', id],
    queryFn: () =>
      fetch(`/api/share/${id}`).then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json() as Promise<ShareContent>;
      }),
    enabled: !!id,
  });

  if (isLoading) return <Loader />;
  if (error) return <Text c="red" p="md">{(error as Error).message}</Text>;
  if (!data) return null;

  const cells: any[] = Array.isArray(data.content?.cells) ? data.content.cells : [];

  return (
    <Stack p="md" gap="md">
      <Group justify="space-between">
        <Stack gap={2}>
          <Title order={3}>{data.notebook.path}</Title>
          <Text size="sm" c="dimmed">
            저장: {data.saved_at ?? '—'} · 권한 <Badge color={permColor(data.permission)}>{data.permission}</Badge>
          </Text>
        </Stack>
        <Link to="/">← 목록으로</Link>
      </Group>

      {cells.length === 0 && (
        <Text c="dimmed">노트북에 셀이 없습니다.</Text>
      )}

      {cells.map((cell, i) => (
        <Card key={i} withBorder padding="md">
          <Group gap="xs" mb="xs">
            <Badge variant="light">{cell.kind ?? 'cell'}</Badge>
            {cell.connection && <Badge color="blue" variant="light">{cell.connection}</Badge>}
            {cell.type && <Badge color="grape" variant="light">{cell.type} chart</Badge>}
          </Group>
          {cell.sql && (
            <Code block style={{ fontSize: 12 }}>{cell.sql}</Code>
          )}
          {cell.mapping && (
            <DemoChart type={cell.type} mapping={cell.mapping} />
          )}
        </Card>
      ))}

      <Card withBorder>
        <Title order={5} mb="xs">원본 JSON</Title>
        <Code block style={{ fontSize: 11 }}>
          {JSON.stringify(data.content, null, 2)}
        </Code>
      </Card>
    </Stack>
  );
}

function DemoChart({ type, mapping }: { type: string; mapping: any }) {
  // Demo placeholder data so the Viewer screen shows actual chart visuals
  // even though we don't replay the SQL on read-only links.
  const data =
    type === 'pie'
      ? [
          {
            type: 'pie',
            labels: ['new', 'qualified', 'won', 'lost'],
            values: [42, 30, 18, 10],
          },
        ]
      : type === 'line'
      ? [
          {
            type: 'scatter',
            mode: 'lines',
            x: ['2026-04-01', '2026-04-02', '2026-04-03', '2026-04-04', '2026-04-05'],
            y: [120, 140, 170, 155, 190],
          },
        ]
      : [
          {
            type: type === 'box' ? 'box' : 'bar',
            x: ['Seoul', 'Busan', 'Incheon', 'Daegu'],
            y: [340, 210, 180, 150],
          },
        ];
  return (
    <Plot
      data={data as any}
      layout={{
        autosize: true,
        height: 280,
        margin: { l: 50, r: 20, t: 20, b: 50 },
        title: { text: `${mapping.x ?? ''} → ${Array.isArray(mapping.y) ? mapping.y.join(',') : mapping.y ?? ''}` },
      }}
      style={{ width: '100%' }}
    />
  );
}

function App() {
  return (
    <AppShell header={{ height: 56 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={4}>👀 Viewer Portal</Title>
          <Text size="sm" c="dimmed">읽기 전용. 다운로드는 권한 부여 시에만.</Text>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Routes>
          <Route path="/" element={<ShareList />} />
          <Route path="/share/:id" element={<ShareDetail />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <MantineProvider>
    <QueryClientProvider client={qc}>
      <BrowserRouter basename="/viewer">
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </MantineProvider>
);
