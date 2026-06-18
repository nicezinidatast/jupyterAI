import { useEffect, useMemo, useRef, useState } from 'react';
import ReactDOM from 'react-dom/client';
import {
  AppShell,
  Badge,
  Box,
  Burger,
  Button,
  Card,
  Code,
  Group,
  Loader,
  MantineProvider,
  Modal,
  NavLink,
  Notification,
  PasswordInput,
  ScrollArea,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core';
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Plot from 'react-plotly.js';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom';
import '@mantine/core/styles.css';

// 전역 react-query 클라이언트. refetchOnWindowFocus를 끄는 이유: 분석가가
// JupyterLab/다른 탭을 오가며 작업하므로, 창 포커스가 돌아올 때마다 커넥션·
// 노트북·스키마를 다시 불러오면 불필요한 깜빡임·요청만 늘어난다. 데이터는
// 명시적 mutation(쿼리 실행·노트북 저장) 이후 invalidate로만 갱신한다.
const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

// ---------------------------------------------------------------------------
// 백엔드 API 응답 타입 — 게이트웨이(/api)가 내려주는 JSON 형태를 그대로 본뜬다.
// UI는 이 평면(flat) 타입만 다루고, 래핑/언래핑은 아래 `api` 래퍼가 담당한다.
// ---------------------------------------------------------------------------
type Connection = {
  connection_id: string;
  name: string;
  engine: string;
  host: string;
  port: number;
  database: string | null;
};

type SchemaColumn = { name: string; type: string; pii_kind: string | null };
type Schema = {
  connection_id: string;
  name: string;
  tables: { schema?: string; name: string; columns: SchemaColumn[] }[];
};

type Row = Record<string, unknown>;
type QueryResult = {
  connection: string;
  engine: string;
  sql: string;
  columns: string[];
  rows: Row[];
  row_count: number;
  active_pii_patterns: string[];
  executed_at: string;
};

type Notebook = {
  notebook_id: string;
  workspace_id: string;
  path: string;
  latest_version: string | null;
  latest_saved_at: string | null;
};

type Workspace = {
  workspace_id: string;
  name: string;
  kind: string;
  git_repo_url: string;
  git_branch: string;
};

type Me = {
  user_id: string;
  email: string;
  display_name: string | null;
  roles: string[];
  // true면 첫 로그인 후 "초기 비밀번호를 변경하세요" 팝업을 자동으로 띄운다.
  must_change_password?: boolean;
};

// ---------------------------------------------------------------------------
// api — 백엔드 엔드포인트 래퍼 모음. 각 메서드는 fetch 한 번 + JSON 파싱만
// 담당하는 얇은 함수이고, react-query의 queryFn/mutationFn으로 그대로 넘긴다.
// 이렇게 모아 두면 (1) 엔드포인트 경로가 한곳에 모여 변경에 강하고, (2)
// 컴포넌트는 로딩/에러/캐시를 react-query에 맡기고 데이터 모양만 신경 쓰면 된다.
// 인증 쿠키가 필요한 호출만 credentials:'include'를 붙인다(나머지는 동일 출처).
// ---------------------------------------------------------------------------
const api = {
  me: () =>
    fetch('/api/auth/me', { credentials: 'include' }).then((r) => {
      if (r.status === 401) {
        // 세션이 없거나 만료됨 → 로그인 페이지로 보낸다. 여기서 즉시 throw하면
        // react-query가 에러 상태로 리렌더하며 깜빡이므로, 대신 "영원히
        // resolve되지 않는" 프라미스를 반환해 리다이렉트가 일어나는 동안 앱이
        // 더 이상 렌더되지 않도록 멈춘다.
        window.location.assign('/login/');
        return new Promise<Me>(() => {});
      }
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      // 백엔드는 { user: {...} } 로 감싸 내려주므로, UI가 쓰는 평면 Me로 푼다.
      return r.json().then((d) => {
        const u = d.user as Me;
        // 사용자별 JupyterHub 서버 베이스를 확정한다. 허브 사용자명은 user_id(UUID)이며,
        // 사용자 식별이 가능한 가장 이른 시점이 여기(me 응답)이다.
        setCopilotNotebookForUser(u?.user_id);
        return u;
      });
    }),
  // 본인 비밀번호 변경. 현재 세션 쿠키로 서버가 본인을 식별하므로 사용자 id를
  // 따로 보내지 않는다. credentials:'include'로 dp_session 쿠키를 반드시 함께 보낸다.
  // 실패(400 현재 비번 불일치/로컬 비번 없음, 401 세션 만료)는 throw해서 모달이
  // 오류 메시지를 띄우게 한다 — 성공/실패를 호출 측에서 명확히 분기하기 위함.
  changePassword: (current_password: string, new_password: string) =>
    fetch('/api/auth/change-password', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password, new_password }),
    }).then((r) => {
      if (!r.ok) throw new Error(String(r.status));
      return r.json() as Promise<{ ok: boolean }>;
    }),
  connections: () => fetch('/api/connections').then((r) => r.json() as Promise<Connection[]>),
  schema: (id: string) =>
    fetch(`/api/connections/${id}/schema`).then((r) => r.json() as Promise<Schema>),
  runQuery: (body: { connection_id: string; sql: string }) =>
    fetch('/api/queries/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...body, params: {} }),
    }).then(async (r) => {
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      return r.json() as Promise<QueryResult>;
    }),
  workspaces: () => fetch('/api/workspaces').then((r) => r.json() as Promise<Workspace[]>),
  notebooks: () => fetch('/api/notebooks').then((r) => r.json() as Promise<Notebook[]>),
  latestNotebook: (id: string) =>
    fetch(`/api/notebooks/${id}/latest`).then((r) => r.json()),
  // 노트북 저장은 새 "버전"을 POST하는 방식 — 백엔드가 매 저장을 Git 커밋으로
  // 남기므로(이력 추적), 덮어쓰기가 아니라 버전 추가로 모델링되어 있다.
  saveNotebook: (id: string, body: { content: unknown; saved_by: string; commit_message: string }) =>
    fetch(`/api/notebooks/${id}/versions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(async (r) => {
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      return r.json();
    }),
};

// 커넥션 이름별 예시 SQL — 커넥션을 처음 고르면 빈 에디터 대신 곧바로 실행
// 가능한 한 줄을 채워 넣어, 분석가가 "무엇을 칠 수 있는지" 감을 잡게 한다.
// (실데이터 스키마에 맞춘 값이라 키는 커넥션 name과 정확히 일치해야 한다.)
const SAMPLE_SQL: Record<string, string> = {
  sales_db: 'SELECT name, email, phone, rrn, city FROM sales.customers LIMIT 25',
  crm_mysql: 'SELECT lead_name, email, stage FROM leads LIMIT 25',
  warehouse_hive: 'SELECT event_date, channel, revenue FROM events_daily LIMIT 30',
};

// 쿼리 결과를 Plotly 차트로 그리는 위젯. 차트 종류·X/Y 축을 사용자가 바꿀 수
// 있고, 숫자형 컬럼을 자동 추려 Y축 기본값을 잡아 준다.
function ChartPicker({ result }: { result: QueryResult }) {
  const [chartType, setChartType] = useState<'line' | 'bar' | 'scatter' | 'pie' | 'area' | 'box' | 'heatmap'>('bar');
  // 모든 행에서 number인 컬럼만 "숫자형"으로 본다 — Y축 후보를 자동 추리기 위함.
  const numericCols = result.columns.filter((c) =>
    result.rows.every((r) => typeof r[c] === 'number')
  );
  // 축 기본값: X는 첫 컬럼, Y는 첫 숫자형 컬럼(없으면 두 번째/첫 컬럼으로 폴백).
  const [x, setX] = useState<string>(result.columns[0]);
  const [y, setY] = useState<string>(numericCols[0] ?? result.columns[1] ?? result.columns[0]);

  // 새 쿼리 결과로 컬럼 구성이 바뀌면, 이전 결과의 축 선택이 더 이상 존재하지
  // 않을 수 있으므로 유효한 컬럼으로 되돌린다(없는 컬럼을 plot에 넘기지 않도록).
  useEffect(() => {
    if (!result.columns.includes(x)) setX(result.columns[0]);
    if (!result.columns.includes(y)) setY(numericCols[0] ?? result.columns[1] ?? result.columns[0]);
  }, [result.columns]);

  // 선택된 차트 종류·축에 맞춰 Plotly trace 배열을 만든다. 차트 종류별로
  // Plotly가 기대하는 데이터 형태가 달라(scatter/line/area는 mode·fill만 다른
  // 같은 trace, box는 y만, heatmap은 z 행렬) 분기로 구성한다.
  const data = useMemo(() => {
    const xs = result.rows.map((r) => r[x] as string | number);
    const ys = result.rows.map((r) => r[y] as number);
    if (chartType === 'pie') {
      return [{ type: 'pie' as const, labels: xs, values: ys }];
    }
    if (chartType === 'line' || chartType === 'scatter' || chartType === 'area') {
      return [
        {
          type: 'scatter' as const,
          mode: chartType === 'scatter' ? 'markers' : 'lines',
          fill: chartType === 'area' ? 'tozeroy' : 'none',
          x: xs,
          y: ys,
        },
      ];
    }
    if (chartType === 'bar') {
      return [{ type: 'bar' as const, x: xs, y: ys }];
    }
    if (chartType === 'box') {
      return [{ type: 'box' as const, y: ys, name: y }];
    }
    return [{ type: 'heatmap' as const, z: [ys] }];
  }, [chartType, x, y, result.rows]);

  return (
    <Stack>
      <Group>
        <Select
          label="차트 종류"
          value={chartType}
          onChange={(v) => v && setChartType(v as typeof chartType)}
          data={['line', 'bar', 'scatter', 'pie', 'area', 'box', 'heatmap']}
          w={140}
        />
        <Select label="X 축" value={x} onChange={(v) => v && setX(v)} data={result.columns} w={180} />
        <Select label="Y 축" value={y} onChange={(v) => v && setY(v)} data={result.columns} w={180} />
      </Group>
      <Plot
        data={data as any}
        layout={{ autosize: true, height: 360, margin: { l: 50, r: 20, t: 30, b: 60 } }}
        style={{ width: '100%' }}
      />
    </Stack>
  );
}

type UploadResult = {
  file_id: string;
  safe_name: string;
  size_bytes: number;
  kind: string;
  mime: string;
  jupyter_path: string;
  hint: string;
};

// 데이터 파일을 JupyterLab 작업 폴더로 곧장 올리는 업로드 카드. 업로드된
// 파일은 ~/work/uploads/ 에 떨어져 노트북에서 바로 읽을 수 있다(내부망
// 워크플로의 핵심 진입점 — DB 커넥션 없이 파일만으로 분석 시작).
function FileUploadCard() {
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onFiles = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setError(null);
    setBusy(true);
    // multipart/form-data로 전송 — Content-Type 헤더는 브라우저가 boundary와
    // 함께 자동으로 채우게 두고(직접 지정하면 boundary가 빠져 깨진다) 첫 파일만 보낸다.
    const form = new FormData();
    form.append('upload', files[0]);
    try {
      const r = await fetch('/api/files/upload', { method: 'POST', body: form });
      if (!r.ok) {
        // 백엔드가 detail에 사람이 읽을 사유(용량 초과·지원 안 하는 형식 등)를
        // 담아 주면 그걸 우선 노출하고, 없으면 상태 코드로 폴백한다.
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail ?? `${r.status} ${r.statusText}`);
      }
      const data = (await r.json()) as UploadResult;
      setLast(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card withBorder padding="sm" radius="md">
      <Group justify="space-between" align="center">
        <div>
          <Text fw={600}>📂 파일 업로드</Text>
          <Text size="xs" c="dimmed">
            CSV / TSV / JSON / Parquet / Excel / Feather — 최대 1 GiB. 업로드된 파일은
            JupyterLab의 <Code>~/work/uploads/</Code> 에서 바로 읽을 수 있어요.
          </Text>
        </div>
        <Button
          component="label"
          variant="light"
          loading={busy}
        >
          파일 선택
          <input
            type="file"
            style={{ display: 'none' }}
            accept=".csv,.tsv,.json,.jsonl,.ndjson,.parquet,.xlsx,.feather,.arrow"
            onChange={(e) => onFiles(e.currentTarget.files)}
          />
        </Button>
      </Group>
      {error && <Notification color="red" title="업로드 실패" mt="sm">{error}</Notification>}
      {last && (
        <Stack gap={4} mt="sm">
          <Text size="sm">
            ✓ <strong>{last.safe_name}</strong> ({Math.round(last.size_bytes / 1024)} KiB)
          </Text>
          <Text size="xs" c="dimmed">JupyterLab에서: <Code>{last.hint}</Code></Text>
        </Stack>
      )}
    </Card>
  );
}

// 빠른 SQL 편집·실행 화면. 현재 라우팅에서는 비활성(JupyterLab + LLM 중심으로
// 전환)이지만, 커넥션 선택 → 스키마 뱃지 → SQL 실행 → 표/차트 → 노트북 저장의
// 전체 흐름을 담고 있어 코드는 보존한다.
function QueryEditor() {
  const qc = useQueryClient();
  const conns = useQuery({ queryKey: ['conns'], queryFn: api.connections });
  const me = useQuery({ queryKey: ['me'], queryFn: api.me });
  const nbs = useQuery({ queryKey: ['nbs'], queryFn: api.notebooks });

  const [connId, setConnId] = useState<string | null>(null);
  const [sql, setSql] = useState('');

  // 커넥션 목록이 처음 도착하면 첫 커넥션을 자동 선택하고 그에 맞는 예시 SQL을
  // 채운다(빈 화면 방지). 이미 사용자가 고른 게 있으면(!connId가 false) 건드리지 않는다.
  useEffect(() => {
    if (!connId && conns.data?.length) {
      const first = conns.data[0];
      setConnId(first.connection_id);
      setSql(SAMPLE_SQL[first.name] ?? `SELECT * FROM sample LIMIT 10`);
    }
  }, [conns.data]);

  const schema = useQuery({
    queryKey: ['schema', connId],
    queryFn: () => api.schema(connId!),
    enabled: !!connId,
  });

  // SQL 실행은 mutation으로 모델링 — 같은 입력이라도 매번 "지금 실행"이라는
  // 명령형 동작이라 캐시 대상 query가 아니다(run.data로 결과를 들고 있는다).
  const run = useMutation({
    mutationFn: () => api.runQuery({ connection_id: connId!, sql }),
  });

  // 실행한 쿼리 + 결과 미리보기를 노트북 한 건에 스냅샷으로 저장한다. 결과
  // 전체가 아니라 앞 5행만 담는 이유: 노트북은 "이 쿼리를 돌렸다"는 기록용이지
  // 데이터 덤프가 아니며, 큰 결과를 통째로 커밋하면 Git 이력이 비대해진다.
  const save = useMutation({
    mutationFn: async () => {
      if (!nbs.data?.length || !me.data) throw new Error('no notebook to save to');
      const content = {
        title: 'Ad-hoc query result',
        cells: [
          { kind: 'sql', connection_id: connId, sql },
          // 아직 실행 전이면(run.data 없음) 결과 셀은 빼고 SQL만 저장 — filter(Boolean)로 null 제거.
          run.data ? { kind: 'result', preview_rows: run.data.rows.slice(0, 5) } : null,
        ].filter(Boolean),
        saved_at: new Date().toISOString(),
      };
      return api.saveNotebook(nbs.data[0].notebook_id, {
        content,
        saved_by: me.data.user_id,
        commit_message: 'analyst SPA save',
      });
    },
    // 저장이 성공하면 노트북 목록 캐시를 무효화 — 최신 버전/저장 시각이 즉시 반영되도록.
    onSuccess: () => qc.invalidateQueries({ queryKey: ['nbs'] }),
  });

  if (conns.isLoading) return <Loader />;

  return (
    <Stack p="md" gap="md">
      <FileUploadCard />
      <Group align="flex-end">
        <Select
          label="커넥션"
          value={connId}
          onChange={(v) => {
            setConnId(v);
            const c = conns.data?.find((x) => x.connection_id === v);
            if (c) setSql(SAMPLE_SQL[c.name] ?? sql);
          }}
          data={(conns.data ?? []).map((c) => ({
            value: c.connection_id,
            label: `${c.name} (${c.engine})`,
          }))}
          w={280}
        />
        {/* 스키마 테이블을 클릭 가능한 뱃지로 — 클릭하면 그 테이블을 SELECT하는
            SQL을 에디터에 채워 넣어, 컬럼명을 외우지 않고도 바로 시작하게 한다.
            뱃지 title(hover)에는 컬럼·타입·PII 여부를 줄바꿈으로 보여 준다. */}
        {schema.data && (
          <Group gap="xs">
            {schema.data.tables.map((t) => {
              // 미리보기 SQL엔 앞 4개 컬럼만 — 너무 긴 SELECT가 에디터를 덮지 않게.
              const colNames = t.columns.map((c) => c.name).slice(0, 4).join(', ');
              // schema가 있으면 schema.table로 정규화(중복 테이블명 충돌 방지).
              const qualified = t.schema ? `${t.schema}.${t.name}` : t.name;
              return (
                <Badge
                  key={qualified}
                  variant="light"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSql(`SELECT ${colNames} FROM ${qualified} LIMIT 25`)}
                  title={t.columns.map((c) => `${c.name}: ${c.type}${c.pii_kind ? ' [PII]' : ''}`).join('\n')}
                >
                  {qualified} ({t.columns.length})
                </Badge>
              );
            })}
          </Group>
        )}
      </Group>

      <Textarea
        label="SQL"
        autosize
        minRows={4}
        value={sql}
        onChange={(e) => setSql(e.currentTarget.value)}
        styles={{ input: { fontFamily: 'monospace', fontSize: 13 } }}
      />

      <Group>
        <Button loading={run.isPending} onClick={() => run.mutate()} disabled={!connId || !sql}>
          ▶ 실행
        </Button>
        <Button
          variant="light"
          loading={save.isPending}
          onClick={() => save.mutate()}
          disabled={!run.data || !nbs.data?.length}
        >
          💾 노트북에 저장 (Git 자동 커밋)
        </Button>
        {save.isSuccess && (
          <Badge color="teal" variant="filled">
            저장됨 — version {String((save.data as any).version_id).slice(0, 8)}…
          </Badge>
        )}
      </Group>

      {run.error && <Notification color="red" title="에러">{(run.error as Error).message}</Notification>}

      {run.data && (
        <Card padding="md" radius="md" withBorder>
          <Stack gap="sm">
            <Group justify="space-between">
              <Group gap="xs">
                <Badge color="blue">{run.data.engine}</Badge>
                <Text size="sm" c="dimmed">{run.data.row_count}건</Text>
                <Text size="xs" c="dimmed">{run.data.executed_at}</Text>
              </Group>
              {/* 이 쿼리 결과에 적용된 PII(개인식별정보) 마스킹 패턴 — 어떤
                  민감 정보가 가려졌는지 분석가가 한눈에 알도록 백엔드가 함께
                  내려준 값을 그대로 노출한다(거버넌스 가시성). */}
              <Group gap={4}>
                <Text size="xs" c="dimmed">활성 PII 패턴:</Text>
                {run.data.active_pii_patterns.map((p) => (
                  <Badge key={p} color="grape" variant="light">{p}</Badge>
                ))}
              </Group>
            </Group>

            <Tabs defaultValue="table">
              <Tabs.List>
                <Tabs.Tab value="table">표</Tabs.Tab>
                <Tabs.Tab value="chart">차트</Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="table" pt="sm">
                <ScrollArea h={360}>
                  <Table striped withTableBorder withColumnBorders fz="sm">
                    <Table.Thead>
                      <Table.Tr>
                        {run.data.columns.map((c) => (
                          <Table.Th key={c}>{c}</Table.Th>
                        ))}
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {run.data.rows.map((row, i) => (
                        <Table.Tr key={i}>
                          {run.data!.columns.map((c) => (
                            <Table.Td key={c}><Code>{String(row[c] ?? '')}</Code></Table.Td>
                          ))}
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>
              </Tabs.Panel>

              <Tabs.Panel value="chart" pt="sm">
                <ChartPicker result={run.data} />
              </Tabs.Panel>
            </Tabs>
          </Stack>
        </Card>
      )}
    </Stack>
  );
}

// 내 노트북 목록 화면(현재 라우팅에서는 비활성). 각 행에서 상세 화면으로 이동한다.
function NotebookList() {
  const nbs = useQuery({ queryKey: ['nbs'], queryFn: api.notebooks });
  return (
    <Stack p="md" gap="md">
      <Title order={3}>내 노트북</Title>
      {nbs.isLoading && <Loader />}
      {nbs.data && (
        <Table striped withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>경로</Table.Th>
              <Table.Th>최근 저장</Table.Th>
              <Table.Th>버전</Table.Th>
              <Table.Th>액션</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {nbs.data.map((nb) => (
              <Table.Tr key={nb.notebook_id}>
                <Table.Td>{nb.path}</Table.Td>
                <Table.Td>{nb.latest_saved_at ? new Date(nb.latest_saved_at).toLocaleString() : '—'}</Table.Td>
                <Table.Td>{nb.latest_version?.slice(0, 8) ?? '—'}</Table.Td>
                <Table.Td>
                  <Button size="xs" component={Link} to={`/notebooks/${nb.notebook_id}`}>열기</Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}

// 노트북 한 건의 최신 버전을 보여 주는 상세 화면. 렌더 가능한 노트북 뷰어가
// 아니라 저장된 content(JSON 스냅샷)를 그대로 펼쳐 보여 주는 점검용 화면이다.
function NotebookDetail() {
  const { id } = useParams();
  const nb = useQuery({
    queryKey: ['nb', id],
    queryFn: () => api.latestNotebook(id!),
    // id가 라우트 파라미터로 들어와야만 조회 — 없으면 호출 자체를 막는다.
    enabled: !!id,
  });
  return (
    <Stack p="md" gap="md">
      <Group>
        <Button component={Link} to="/notebooks" variant="subtle">← 목록</Button>
      </Group>
      {nb.isLoading && <Loader />}
      {nb.data && (
        <Card withBorder>
          <Title order={3}>{nb.data.path}</Title>
          <Text size="sm" c="dimmed">최근 저장: {nb.data.saved_at ?? '—'}</Text>
          <Code block style={{ marginTop: 8 }}>
            {JSON.stringify(nb.data.content, null, 2)}
          </Code>
        </Card>
      )}
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Markdown — 코파일럿의 산문(제목·굵게·목록·인라인/펜스 코드)을 Mantine 채팅
// 말풍선 안에 렌더한다. 채팅 답변처럼 읽히도록 여백을 촘촘하게, 코드는
// 모노스페이스 + 연회색 배경으로 처리. 인라인 style로는 닿지 않는, react-markdown이
// 실제로 뱉는 엘리먼트들을 범위 한정 <style>(.copilot-md 하위)로 겨냥한다.
// ---------------------------------------------------------------------------
function Markdown({ children }: { children: string }) {
  return (
    <Box className="copilot-md" fz="sm">
      <style>{`
        .copilot-md > :first-child { margin-top: 0; }
        .copilot-md > :last-child { margin-bottom: 0; }
        .copilot-md p { margin: 0.35em 0; line-height: 1.5; }
        .copilot-md ul, .copilot-md ol { margin: 0.35em 0; padding-left: 1.4em; }
        .copilot-md li { margin: 0.15em 0; }
        .copilot-md h1, .copilot-md h2, .copilot-md h3,
        .copilot-md h4, .copilot-md h5, .copilot-md h6 {
          margin: 0.6em 0 0.3em; line-height: 1.3; font-weight: 700;
        }
        .copilot-md code {
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          font-size: 0.85em; background: #f1f3f5; padding: 0.1em 0.35em;
          border-radius: 4px;
        }
        .copilot-md pre {
          background: #f1f3f5; padding: 0.6em 0.75em; border-radius: 6px;
          overflow: auto; margin: 0.45em 0;
        }
        .copilot-md pre code {
          background: transparent; padding: 0; font-size: 0.82em; line-height: 1.45;
        }
        .copilot-md a { color: #1c7ed6; }
        .copilot-md blockquote {
          margin: 0.45em 0; padding-left: 0.75em; border-left: 3px solid #dee2e6;
          color: #495057;
        }
        .copilot-md table { border-collapse: collapse; margin: 0.45em 0; }
        .copilot-md th, .copilot-md td {
          border: 1px solid #dee2e6; padding: 0.25em 0.5em;
        }
      `}</style>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </Box>
  );
}

// 임베드된 JupyterLab을 iframe으로 띄우는 컴포넌트. 같은 출처에서 SPA와 Lab을
// 함께 서빙하므로, 아래의 셀 주입/활성 노트북 조작이 모두 이 iframe을 통해 동작한다.
function JupyterLab({ connectionId }: { connectionId: string | null }) {
  // 사용자 본인 폴더(work/<id>/)에서 시작하게 한다 — 파일 브라우저가 거기서
  // 열리고 Launcher로 만드는 새 파일도 거기에 생겨, 평소 화면이 "내 것"으로
  // 보인다. 폴더를 먼저 만든 뒤 iframe을 /lab/tree/<dir>로 가리키고, 코파일럿은
  // 첫 삽입 때 자기 노트북을 앱 안에서 연다(iframe 새로고침 없음).
  const [loading, setLoading] = useState(true);
  const [src, setSrc] = useState<string | null>(null);

  // 오래 사는 주입 타이머(injector)가 항상 최신 connectionId를 보도록 ref에 담는다.
  // (setInterval 클로저는 마운트 시점 값을 가두므로 ref로 우회.)
  const connRef = useRef(connectionId);
  connRef.current = connectionId;

  // iframe URL을 한 번만 확정: work/<id>/가 있는지 보장한 뒤 그 위치에서 Lab을 연다.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      // 사용자별 JupyterHub 서버로 들어간다. httpOnly 세션 쿠키는 JS가 직접 못 읽으므로
      // 백엔드에서 허브 로그인용 단기 토큰을 받아 허브의 토큰 SSO 로그인으로 넘긴다.
      // 허브가 토큰을 검증하고 사용자별 컨테이너를 스폰한 뒤 그 사람의 Lab으로 보낸다.
      let token = '';
      try {
        const r = await fetch('/api/auth/jupyter-token', { credentials: 'include' });
        if (r.ok) token = ((await r.json()) as { token?: string }).token ?? '';
      } catch {
        /* 토큰 발급 실패 — 토큰 없이 시도(허브가 거부하면 사용자가 재로그인) */
      }
      if (cancelled) return;
      // next는 허브의 spawn 엔드포인트로 둔다. 로그인 직후 사용자 서버를(없으면)
      // 스폰하고, 끝나면 그 사람의 Lab(/jupyter/user/<id>/lab, default_url=/lab)으로
      // 리다이렉트한다. /user/<id>/lab로 곧장 가면 서버 미기동 시 허브가 424를 내므로,
      // 반드시 spawn을 거쳐 자동 기동시킨다. 첫 스폰은 컨테이너 기동에 시간이 걸려
      // 허브의 "서버 시작 중" 화면이 잠깐 보였다가 Lab으로 전환된다.
      const next = '/jupyter/hub/spawn';
      setSrc(
        `/jupyter/hub/login?platform_token=${encodeURIComponent(token)}&next=${encodeURIComponent(next)}`,
      );
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // 임베드된 노트북의 각 셀에 "✨ AI" 수정 버튼을 주입한다. JupyterLab이
  // 리렌더되거나 노트북이 새로 열려 버튼이 사라져도, 폴링(1.2초 주기)이 다시
  // 꽂아 주어 스스로 복구한다(self-heal). Lab이 아직 안 떴거나 열린 노트북이
  // 없으면 injectCellButtons가 조용히 빠지므로 try/catch로 무시.
  useEffect(() => {
    const id = window.setInterval(() => {
      try {
        injectCellButtons(connRef.current);
      } catch {
        /* Lab 미준비 / 아직 열린 노트북 없음 */
      }
    }, 1200);
    return () => window.clearInterval(id);
  }, []);

  if (!src) {
    return (
      <Group justify="center" align="center" style={{ height: '100%' }}>
        <Loader />
      </Group>
    );
  }

  return (
    // title="JupyterLab"은 단순 라벨이 아니라, 아래 getJupyterApp()이 이 iframe을
    // querySelector로 찾는 키이므로 바꾸면 셀 주입/활성 노트북 조작이 끊긴다.
    // 로드 전에는 살짝 흐리게(opacity 0.45) 두었다가 onLoad에서 선명해지게 해
    // 빈 흰 화면 대신 "곧 뜬다"는 느낌을 준다.
    <iframe
      src={src}
      title="JupyterLab"
      onLoad={() => setLoading(false)}
      style={{
        width: '100%',
        height: '100%',
        border: 'none',
        display: 'block',
        transition: 'opacity 250ms ease-in',
        opacity: loading ? 0.45 : 1,
      }}
      allow="clipboard-read; clipboard-write"
    />
  );
}

// ---------------------------------------------------------------------------
// Jupyter 셀 주입 — 공유 copilot.ipynb에 코드 셀을 덧붙인다.
// ---------------------------------------------------------------------------
// 공유 JupyterLab 위에서의 사용자별 작업 폴더 + copilot 노트북.
// 분석가마다 자기 폴더(work/<id>/)에서 시작해 기본 화면에 본인 파일만 보이게
// 한다(소프트 격리 — 단일 토큰을 공유하는 서버라 상위 폴더로의 이동을 강하게
// 막지는 못하지만, 평소 작업 동선은 개인용으로 유지된다). 이 폴더는 영속
// 볼륨 `work` 위에 있어 컨테이너를 다시 만들어도 남는다. api.me()가 사용자
// 식별을 끝내기 전까지는 아래 기본값(일반 copilot.ipynb)을 쓴다.
//
// 주의: 이 4개 값은 모듈 전역 가변 상태다. setCopilotNotebookForUser가 me
// 응답 시점에 한 번 덮어쓰면, 이후 모든 Jupyter contents API 호출이 같은
// 사용자별 경로를 바라본다(REST 헬퍼들이 이 전역을 직접 참조).
// 사용자별 JupyterHub 서버의 베이스 경로. /me의 user_id(=허브 사용자명)로 확정된다.
// 사용자마다 컨테이너가 분리되므로 서버 루트(/home/jovyan/work)가 곧 개인 공간 →
// copilot 노트북은 루트의 copilot.ipynb 하나면 충분하다(work/<id> 하위폴더·공유 토큰 불필요).
let JUPYTER_USER_BASE = '/jupyter'; // 확정 전 임시. 확정 후 /jupyter/user/<id>
let COPILOT_NOTEBOOK = 'copilot.ipynb'; // 사용자 서버 루트 기준 경로
let COPILOT_NOTEBOOK_NAME = 'copilot.ipynb'; // 파일명(basename)
let COPILOT_NOTEBOOK_URL = `${JUPYTER_USER_BASE}/api/contents/${COPILOT_NOTEBOOK}`;

// /me의 user_id(=JupyterHub 사용자명)로 사용자별 서버 베이스를 확정한다. 서버 자체가
// 분리돼 있어 노트북 경로는 루트의 copilot.ipynb로 고정한다 — 예전처럼 파일명에 사용자
// 슬러그를 넣을 필요가 없다(격리는 서버·볼륨이 보장하므로).
function setCopilotNotebookForUser(userId: string | null | undefined): void {
  const id = (userId || '').trim();
  JUPYTER_USER_BASE = id ? `/jupyter/user/${encodeURIComponent(id)}` : '/jupyter';
  COPILOT_NOTEBOOK = 'copilot.ipynb';
  COPILOT_NOTEBOOK_NAME = 'copilot.ipynb';
  COPILOT_NOTEBOOK_URL = `${JUPYTER_USER_BASE}/api/contents/${COPILOT_NOTEBOOK}`;
}

// 사용자별 서버에서는 루트(/home/jovyan/work)가 이미 개인 공간이고 copilot.ipynb를
// 루트에 두므로, 따로 만들어 줄 디렉터리가 없다. 호출부 호환을 위해 no-op로 남긴다.
async function ensureUserDir(): Promise<void> {
  return;
}

// Jupyter contents API용 공통 요청 헤더(아래 모든 copilot.ipynb 호출이 공유).
// 인증은 허브 OAuth 쿠키로 한다(공유 토큰 제거) — 호출부는 반드시 credentials:'include'.
function copilotApiHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    // 이중 안전장치: 캐시된 GET이 방금(사용자가, 혹은 직전 턴이) 추가한 셀을
    // 못 보고 옛 본문을 재사용하면, 이어지는 PUT이 새 셀을 덮어써 버린다.
    // 그 경합을 막으려고 no-cache를 명시한다.
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache',
  };
}

// 최소한이지만 유효한 빈 노트북(nbformat 4, python3 커널). "비어 있으면
// 새로 만드는" 경로와 "존재 보장" 경로가 같은 모양을 쓰도록 한곳에 정의한다.
function emptyCopilotNotebook(): any {
  return {
    type: 'notebook',
    content: {
      cells: [],
      metadata: { kernelspec: { name: 'python3', display_name: 'Python 3' } },
      nbformat: 4,
      nbformat_minor: 5,
    },
    format: 'json',
    name: COPILOT_NOTEBOOK_NAME,
    path: COPILOT_NOTEBOOK,
  };
}

// 노트북의 `content`를 Jupyter contents API로 PUT한다. 셀 덧붙이기 경로와
// 존재 보장 경로가 공유하는 저수준 쓰기 헬퍼.
async function putCopilotNotebook(content: any): Promise<void> {
  const put = await fetch(COPILOT_NOTEBOOK_URL, {
    method: 'PUT',
    headers: copilotApiHeaders(),
    credentials: 'include',
    body: JSON.stringify({ type: 'notebook', format: 'json', content }),
  });
  if (!put.ok) {
    throw new Error(`Jupyter PUT failed: ${put.status}`);
  }
}

// REST 폴백 경로: 디스크의 copilot.ipynb를 GET해 현재 셀들 끝에 새 셀을
// 덧붙인 뒤 통째로 PUT한다. 라이브 모델(insertCellIntoNotebook)이 실패하거나
// 열린 노트북이 없을 때만 쓴다 — 파일을 직접 고치므로 iframe은 "디스크에서
// 바뀜"을 모른 채 새로고침이 필요할 수 있다.
async function appendCellToCopilotNotebook(language: 'sql' | 'python', source: string): Promise<void> {
  const url = COPILOT_NOTEBOOK_URL;
  const headers = copilotApiHeaders();

  let notebook: any | null = null;
  // `?_=` 캐시 무력화용 더미 파라미터 — jupyter는 모르는 쿼리 파라미터를 무시한다.
  const head = await fetch(`${url}?_=${Date.now()}`, {
    headers,
    credentials: 'include',
    cache: 'no-store',
  });
  if (head.ok) {
    notebook = await head.json();
  }
  // 아직 파일이 없으면(404 등) 빈 노트북에서 시작해 첫 셀을 만든다.
  if (!notebook) {
    notebook = emptyCopilotNotebook();
  }
  // SQL은 %%sql 매직을 앞에 붙여 노트북에서 셀 매직으로 실행되게 한다.
  // copilot_generated 메타데이터는 "이 셀은 코파일럿이 만든 것"이라는 표식
  // (감사·구분용).
  const cell = {
    cell_type: 'code',
    metadata: { copilot_generated: true, language },
    source: language === 'sql' ? `%%sql\n${source}` : source,
    outputs: [],
    execution_count: null,
  };
  notebook.content.cells.push(cell);
  notebook.type = 'notebook';
  notebook.format = 'json';
  notebook.name = COPILOT_NOTEBOOK_NAME;
  notebook.path = COPILOT_NOTEBOOK;

  await putCopilotNotebook(notebook.content);
}

// ---------------------------------------------------------------------------
// 활성 노트북 타겟팅 — 포털이 SPA와 JupyterLab을 같은 출처(origin)에서
// 서빙하므로, iframe 안으로 손을 뻗어 살아 있는 Lab 앱 객체
// (`window.jupyterapp`, --LabApp.expose_app_in_browser=True로 노출됨)를 직접
// 쓸 수 있다. 라이브 공유 모델(shared model)을 통해 꽂은 셀은 분석가가 보고
// 있는 노트북에 즉시 나타난다 — iframe 새로고침도, "디스크에서 변경됨" 충돌
// 대화상자도 없다.
// ---------------------------------------------------------------------------
// iframe 안의 JupyterLab 앱 핸들을 가져온다. title='JupyterLab'로 iframe을
// 찾고, 노출된 전역(jupyterapp 또는 구버전 jupyterlab)을 반환한다.
function getJupyterApp(): any | null {
  const iframe = document.querySelector<HTMLIFrameElement>("iframe[title='JupyterLab']");
  try {
    const w = iframe?.contentWindow as any;
    return w?.jupyterapp ?? w?.jupyterlab ?? null;
  } catch {
    return null; // 교차 출처거나 iframe 미준비 — REST로 폴백
  }
}

// 주어진 위젯이 "지금 안전하게 셀을 꽂을 수 있는" 노트북 패널인지 판정한다.
function isNotebookPanel(w: any): boolean {
  // context.isReady 게이트가 핵심: Lab이 파일을 아직 로딩 중이면 패널의
  // 모델이 비어 있는데, 그 상태에서 addCell + save하면 디스크의 진짜 노트북을
  // "새 셀 하나"로 덮어써 날려 버린다. 준비 안 된 패널은 "열린 노트북 없음"
  // 으로 취급해, 호출자가 안전한 REST 덧붙이기 경로를 타게 한다.
  return Boolean(
    w?.context?.path?.endsWith?.('.ipynb') &&
      w?.content?.model?.sharedModel &&
      w?.context?.isReady !== false,
  );
}

// 분석가가 실제로 보고 있는 노트북을 고르는 우선순위:
//   1. 포커스된 메인 영역 위젯이 노트북이면 그것
//   2. 메인 독에서 탭이 보이는 노트북(iframe이 브라우저 포커스를 한 번도
//      못 받으면 포커스 추적이 비어 있을 수 있어 가시성으로 보강)
//   3. 메인 영역에서 처음 열린 노트북(예: Launcher 탭에 포커스가 있을 때)
//   4. null → 호출자가 REST copilot.ipynb 경로로 폴백
// ---------------------------------------------------------------------------
// 셀별 AI 수정 — Colab 스타일. 같은 출처 iframe + JupyterLab 앱 핸들을 통해,
// 각 코드 셀의 기본 셀 툴바(복제/이동/삭제 아이콘 옆)에 "✨" 아이콘을 꽂는다.
// 클릭하면 셀 아래에 인라인 편집 바가 열리고, 적용하면 /api/copilot/edit-cell을
// 호출해 셀 소스를 그 자리에서(새로고침 없이) 교체한다. 폴링 호출자가 이
// 함수를 반복 실행해 Lab 리렌더에도 스스로 복구된다.
// ---------------------------------------------------------------------------
function openCellEditBar(cell: any, connectionId: string | null): void {
  const node: HTMLElement = cell.node;
  // iframe 안의 셀 DOM이므로 SPA의 document가 아니라 셀이 속한 문서(ownerDocument)로
  // 엘리먼트를 만든다 — 안 그러면 다른 document에 붙여 렌더가 깨진다.
  const doc = node.ownerDocument;
  // 같은 셀에 편집 바가 이미 있으면 새로 만들지 않고 입력란에 포커스만 준다(토글).
  const existing = node.querySelector('.zini-edit-bar') as HTMLElement | null;
  if (existing) {
    (existing.querySelector('input') as HTMLInputElement | null)?.focus();
    return;
  }
  const bar = doc.createElement('div');
  bar.className = 'zini-edit-bar';
  Object.assign(bar.style, {
    display: 'flex', gap: '6px', alignItems: 'center',
    padding: '6px 10px',
    marginTop: '2px', marginRight: '12px', marginBottom: '8px',
    background: '#f3f0ff', border: '1px solid #d0bfff', borderRadius: '6px',
  } as Partial<CSSStyleDeclaration>);
  // 편집 바의 왼쪽 끝을 셀 왼쪽이 아니라 회색 코드 에디터 영역(In[] 거터
  // 다음)에 맞춰, 입력란이 코드와 세로로 정렬되게 한다. 에디터 엘리먼트를
  // 못 찾으면 대략적인 64px로 폴백.
  const editorEl = (node.querySelector('.jp-InputArea-editor')
    || node.querySelector('.cm-editor')) as HTMLElement | null;
  const leftOffset = editorEl
    ? Math.max(0, Math.round(editorEl.getBoundingClientRect().left - node.getBoundingClientRect().left))
    : 64;
  bar.style.marginLeft = `${leftOffset}px`;
  const input = doc.createElement('input');
  input.type = 'text';
  input.placeholder = '이 셀을 어떻게 고칠까요? (예: 에러 처리 추가) — Enter 적용, Esc 취소';
  Object.assign(input.style, {
    flex: '1', fontSize: '12px', padding: '4px 6px',
    border: '1px solid #b197fc', borderRadius: '4px',
  } as Partial<CSSStyleDeclaration>);
  const apply = doc.createElement('button');
  apply.type = 'button'; apply.textContent = '적용';
  Object.assign(apply.style, {
    fontSize: '12px', padding: '4px 10px', cursor: 'pointer', color: '#fff',
    background: '#7048e8', border: 'none', borderRadius: '4px',
  } as Partial<CSSStyleDeclaration>);
  const cancel = doc.createElement('button');
  cancel.type = 'button'; cancel.textContent = '취소';
  Object.assign(cancel.style, {
    fontSize: '12px', padding: '4px 8px', cursor: 'pointer', color: '#495057',
    background: 'transparent', border: '1px solid #ced4da', borderRadius: '4px',
  } as Partial<CSSStyleDeclaration>);
  const status = doc.createElement('span');
  Object.assign(status.style, { fontSize: '11px', color: '#868e96', whiteSpace: 'nowrap' } as Partial<CSSStyleDeclaration>);

  const close = () => bar.remove();
  const run = async () => {
    const instruction = input.value.trim();
    if (!instruction) return;
    // 셀의 현재 소스를 라이브 공유 모델에서 읽는다(getSource). 구버전 호환을
    // 위해 model.source 문자열 폴백도 둔다.
    const sm = cell.model?.sharedModel;
    const source: string =
      typeof sm?.getSource === 'function' ? sm.getSource() : String(cell.model?.source ?? '');
    // 첫 줄의 %%sql 매직 유무로 언어를 추정해 백엔드에 힌트로 넘긴다.
    const language = /^\s*%%sql\b/.test(source) ? 'sql' : 'python';
    apply.disabled = true; input.disabled = true; status.textContent = 'AI 처리 중…';
    try {
      // 인증 쿠키가 필요하므로 credentials:'include'. 현재 소스 + 사용자 지시 +
      // 언어/커넥션을 보내면 백엔드가 수정된 소스를 돌려준다.
      const res = await fetch('/api/copilot/edit-cell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ source, instruction, language, connection_id: connectionId }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      // 라이브 모델에 바로 setSource — 디스크 저장/iframe 새로고침 없이 셀
      // 내용이 그 자리에서 바뀐다.
      sm.setSource(data.source ?? '');
      close();
    } catch (err) {
      // 실패해도 바를 닫지 않고 상태 텍스트로 사유를 보여 준 뒤 재시도 가능하게
      // 버튼/입력을 다시 활성화한다.
      status.textContent = '실패: ' + ((err as Error).message || String(err));
      apply.disabled = false; input.disabled = false;
    }
  };
  apply.addEventListener('click', run);
  cancel.addEventListener('click', close);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); run(); }
    else if (e.key === 'Escape') { e.preventDefault(); close(); }
  });
  bar.append(input, apply, cancel, status);
  node.appendChild(bar);
  input.focus();
}

// 활성 노트북의 모든 코드 셀 툴바에 "✨" 버튼을 한 번씩 꽂는다(이미 있으면 건너뜀).
// JupyterLab 폴링(1.2초)이 반복 호출하므로 멱등성이 중요하다.
function injectCellButtons(connectionId: string | null): void {
  const panel = getActiveNotebookPanel();
  const widgets: any[] | undefined = panel?.content?.widgets;
  if (!widgets) return;
  for (const cell of widgets) {
    if (cell?.model?.type !== 'code') continue; // 마크다운/raw 셀은 제외
    const node: HTMLElement | undefined = cell.node;
    if (!node) continue;
    // 기본 셀 툴바 아이콘(복제/이동/삭제) 옆에 꽂는다. 툴바가 없거나 이미
    // 우리 버튼이 있으면 건너뛴다(중복 주입 방지).
    const toolbar = node.querySelector('.jp-cell-toolbar');
    if (!toolbar || toolbar.querySelector('.zini-cell-btn')) continue;
    const doc = node.ownerDocument;
    const btn = doc.createElement('button');
    btn.className = 'zini-cell-btn';
    btn.type = 'button';
    btn.textContent = '✨';
    btn.title = 'AI로 이 셀 수정 (다분석할Zini)';
    Object.assign(btn.style, {
      cursor: 'pointer', background: 'transparent', border: 'none',
      fontSize: '14px', lineHeight: '1', padding: '0 4px', color: '#7048e8',
    } as Partial<CSSStyleDeclaration>);
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      openCellEditBar(cell, connectionId);
    });
    // 툴바 맨 앞에(복제/이동/삭제 이전) 둔다 — 가장 눈에 띄는 자리.
    toolbar.insertBefore(btn, toolbar.firstChild);
  }
}

// 위 우선순위(포커스 → 가시 탭 → 첫 노트북)에 따라 활성 노트북 패널을 고른다.
function getActiveNotebookPanel(): any | null {
  const app = getJupyterApp();
  if (!app) return null;
  // 1순위: 현재 포커스된 위젯이 (준비된) 노트북이면 그것.
  const cur = app.shell?.currentWidget;
  if (isNotebookPanel(cur)) return cur;
  try {
    let firstNotebook: any | null = null;
    // 메인 영역 위젯을 순회: 보이는 노트북이 있으면 즉시 반환(2순위),
    // 없으면 처음 만난 노트북을 폴백 후보로 기억(3순위).
    for (const w of app.shell.widgets('main')) {
      if (!isNotebookPanel(w)) continue;
      if (w.isVisible) return w;
      if (!firstNotebook) firstNotebook = w;
    }
    return firstNotebook;
  } catch {
    /* lumino 이터레이터 버전 불일치 — "열린 노트북 없음"으로 취급 */
  }
  return null;
}

// copilot.ipynb가 디스크에 있는지 보장한다(없으면 빈 노트북 생성). 그래야
// "could not find path" 에러 없이 앱 안에서 열 수 있다.
async function ensureCopilotFileExists(): Promise<void> {
  const head = await fetch(`${COPILOT_NOTEBOOK_URL}?_=${Date.now()}`, {
    headers: copilotApiHeaders(),
    credentials: 'include',
    cache: 'no-store',
  });
  if (head.ok) return;
  if (head.status !== 404) throw new Error(`Jupyter GET failed: ${head.status}`);
  // 노트북은 사용자 서버 루트에 두므로 따로 만들 부모 디렉터리가 없다(ensureUserDir는 no-op).
  await ensureUserDir();
  await putCopilotNotebook(emptyCopilotNotebook().content);
}

// 코파일럿이 만든 셀을 노트북에 꽂는 핵심 함수. 가능한 한 "라이브 경로"를 쓰고
// (분석가가 보는 화면에 즉시 반영, 충돌 대화상자 없음), 안 되면 REST로 폴백한다.
// 반환값의 mode로 호출자가 iframe 새로고침이 필요한지(rest일 때만) 판단한다.
async function insertCellIntoNotebook(
  language: 'sql' | 'python',
  source: string,
): Promise<{ path: string; mode: 'live' | 'rest' }> {
  const app = getJupyterApp();
  let panel = getActiveNotebookPanel();
  // 열린 노트북이 없으면 → copilot.ipynb를 앱 안에서(iframe 새로고침 없이) 열어
  // 삽입한 셀이 라이브로 보이게 한다. 파일이 없으면 먼저 만든다.
  if (!panel && app) {
    try {
      await ensureCopilotFileExists();
      const w = await app.commands.execute('docmanager:open', { path: COPILOT_NOTEBOOK });
      // 모델 로딩이 끝날 때까지 기다린다 — 준비 전 패널에 쓰면 디스크를 덮어쓸 위험.
      if (w?.context?.ready) await w.context.ready;
      panel = isNotebookPanel(w) ? w : getActiveNotebookPanel();
    } catch {
      panel = getActiveNotebookPanel();
    }
  }
  if (panel?.content?.model?.sharedModel) {
    try {
      // 라이브 경로: 공유 모델에 직접 addCell → 화면에 즉시 나타난다.
      panel.content.model.sharedModel.addCell({
        cell_type: 'code',
        source: language === 'sql' ? `%%sql\n${source}` : source,
        metadata: { copilot_generated: true, language },
      });
      try {
        await panel.context.save();
      } catch {
        // 셀은 이미 라이브 모델에 들어가 있다. 저장 실패는 "분석가가 나중에
        // 수동 저장"이면 그만이므로, 이걸로 삽입 자체를 실패시키지 않는다.
      }
      return { path: panel.context.path as string, mode: 'live' };
    } catch {
      // 라이브 경로 예외(Lab 부팅 중, API 변경 등) — 아래 REST로 폴백.
    }
  }
  // 최후 수단: REST로 파일에 직접 쓴다. iframe 새로고침은 없고, 사용자가 파일을 열면 보인다.
  await appendCellToCopilotNotebook(language, source);
  return { path: COPILOT_NOTEBOOK, mode: 'rest' };
}

// ---------------------------------------------------------------------------
// CopilotPanel — LLM(대규모 언어 모델)과의 채팅. 응답을 스트리밍으로 받아
// 산문은 말풍선에, 코드 블록은 노트북 셀로 삽입할 수 있게 렌더한다.
// ---------------------------------------------------------------------------
type CopilotMsg = { role: 'user' | 'assistant'; content: string };
type CopilotCodeBlock = { language: 'sql' | 'python'; source: string };

// 응답 텍스트에서 ```sql / ```python 펜스 코드 블록을 추출한다.
function splitMarkdownCodeBlocks(text: string): Array<{ text: string; blocks: CopilotCodeBlock[] }> {
  // 전체 텍스트 + 검출된 블록 목록을 한 "세그먼트"로 묶어 반환한다. 이 블록
  // 목록이 있어야 메시지 아래에 "셀에 삽입" 버튼을 그릴 수 있다.
  const blocks: CopilotCodeBlock[] = [];
  const re = /```(sql|python)\n([\s\S]*?)```/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    blocks.push({ language: m[1].toLowerCase() as 'sql' | 'python', source: m[2].trim() });
  }
  return [{ text, blocks }];
}

// 채팅엔 코드 자체가 아니라 코드 "주변 산문"만 보여 준다 — 코드는
// copilot.ipynb(노트북)에 들어가기 때문. 펜스 블록을 제거하고 공백을 정리한다.
function stripCodeFences(text: string): string {
  return text
    .replace(/```(sql|python)\n[\s\S]*?```/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// 활성 노트북의 셀들을 끌어와, 다음 턴에서 모델이 그것을 참조/리팩토링할 수
// 있게 컨텍스트 프롬프트를 만든다. 우선순위는 라이브 공유 모델(지금 분석가가
// 보고 있는 미저장 편집까지 포함) → REST copilot.ipynb 폴백 순(fetchNotebookContext).
function buildNotebookContextPrompt(
  path: string,
  codeCells: string[],
): { prompt: string; cellCount: number } {
  // 셀이 없으면 빈 프롬프트 — 호출부에서 원 질문만 그대로 보낸다.
  if (codeCells.length === 0) return { prompt: '', cellCount: 0 };
  // 셀마다 "--- Cell #n ---" 구분선을 붙여 모델이 셀 경계를 인식하게 한다.
  const body = codeCells
    .map((s, i) => `--- Cell #${i + 1} ---\n${s}`)
    .join('\n\n');
  const prompt =
    `현재 활성 노트북(${path})에 들어있는 코드 셀입니다. ` +
    `사용자의 새 요청이 "이 코드 수정/리팩토링/이어서" 같은 의도면 ` +
    `이 셀들을 기준으로 답하세요. 새 셀이 필요하면 새 코드 블록을 추가하세요.\n\n` +
    body;
  return { prompt, cellCount: codeCells.length };
}

// 활성 노트북의 코드 셀을 모아 컨텍스트 프롬프트를 만든다. 라이브 모델 우선,
// 실패 시 REST 폴백.
async function fetchNotebookContext(): Promise<{
  prompt: string;
  cellCount: number;
}> {
  const panel = getActiveNotebookPanel();
  if (panel) {
    try {
      // 라이브 경로: 분석가가 지금 보고 있는(미저장 편집 포함) 셀을 그대로 읽는다.
      const shared = panel.content.model.sharedModel;
      const codeCells: string[] = [];
      for (const c of shared.cells ?? []) {
        if (c?.cell_type !== 'code') continue;
        const s = (
          typeof c.getSource === 'function' ? c.getSource() : String(c.source ?? '')
        ).trim();
        if (s) codeCells.push(s); // 빈 셀은 제외
      }
      return buildNotebookContextPrompt(panel.context.path as string, codeCells);
    } catch {
      /* 라이브 읽기 실패 — 아래 REST 경로로 폴백 */
    }
  }

  // 최대 4초 상한 — Jupyter가 재시작 중이거나 느리면, 컨텍스트 없이라도 질문을
  // 보내 채팅이 무한정 막히지 않게 한다(AbortController로 강제 중단).
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), 4000);
  try {
    const r = await fetch(
      `${COPILOT_NOTEBOOK_URL}?_=${Date.now()}`,
      {
        headers: { 'Cache-Control': 'no-cache' },
        credentials: 'include',
        cache: 'no-store',
        signal: ctrl.signal,
      },
    );
    if (!r.ok) return { prompt: '', cellCount: 0 };
    const nb = await r.json();
    const cells: any[] = nb?.content?.cells ?? [];
    // nbformat의 source는 문자열 또는 줄 단위 문자열 배열이라 둘 다 처리한다.
    const codeCells = cells
      .filter((c) => c.cell_type === 'code')
      .map((c) => (Array.isArray(c.source) ? c.source.join('') : c.source ?? ''))
      .map((s: string) => s.trim())
      .filter((s) => s.length > 0);
    return buildNotebookContextPrompt(COPILOT_NOTEBOOK, codeCells);
  } catch {
    return { prompt: '', cellCount: 0 };
  } finally {
    window.clearTimeout(timer);
  }
}

function CopilotPanel({
  connectionId,
  onCellInserted,
}: {
  connectionId: string | null;
  onCellInserted?: () => void;
}) {
  const [history, setHistory] = useState<CopilotMsg[]>([]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providerName, setProviderName] = useState<string>('');
  const [lastInsert, setLastInsert] = useState<string | null>(null);
  // 어떤 (sendSeq, blockIdx) 쌍이 이미 자동 삽입됐는지 추적해, 리렌더가 같은
  // 블록에 대해 PUT/감사 왕복을 중복 발사하지 않게 한다. 이 키는 절대
  // setHistory 업데이터의 부수효과에서 만들면 안 된다 — React 18은 업데이터를
  // 삽입 루프 이후로 미룰 수 있어, 매 턴이 "-1:0"으로 키잉되며 첫 메시지 이후
  // 모든 자동 삽입이 조용히 건너뛰어진다(과거에 실제로 겪은 버그).
  const insertedRef = useRef<Set<string>>(new Set());
  const sendSeqRef = useRef(0);
  // 스크롤되는 채팅 컨테이너. 사용자가 이미 바닥에 붙어 있을 때만 스트림을
  // 따라간다 — 과거 질문을 다시 읽으려고 위로 스크롤했다면, 스트리밍 청크가
  // 화면을 아래로 홱 끌어내리면 안 된다.
  const chatRef = useRef<HTMLDivElement | null>(null);
  const [autoFollow, setAutoFollow] = useState(true);

  // 어떤 LLM 제공자(provider)가 붙어 있는지 한 번 조회해 헤더 뱃지에 표시한다.
  // 실패해도 조용히 무시 — 제공자 표시는 부가 정보이고 채팅 자체엔 영향 없다.
  useEffect(() => {
    fetch('/api/copilot/provider')
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => j && setProviderName(j.provider))
      .catch(() => {});
  }, []);

  // history/pending이 바뀔 때마다(=새 메시지·스트리밍 청크) 바닥으로 스크롤하되,
  // autoFollow가 켜져 있을 때만. 사용자가 위로 올려 둔 경우엔 따라가지 않는다.
  useEffect(() => {
    if (!autoFollow) return;
    const el = chatRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [history, pending, autoFollow]);

  // 사용자가 스크롤하면 "바닥에 붙어 있는지"를 다시 판정해 autoFollow를 갱신한다.
  const onChatScroll = () => {
    const el = chatRef.current;
    if (!el) return;
    // 24px 여유 — 소수점 반올림으로 생기는 미세한 틈도 "바닥"으로 친다.
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
    setAutoFollow(atBottom);
  };

  const scrollToLatest = () => {
    const el = chatRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    setAutoFollow(true);
  };

  const send = async () => {
    if (!input.trim() || busy) return; // 빈 입력·전송 중이면 무시
    setError(null);
    const question = input.trim();
    setInput('');
    setBusy(true);
    // 새 질문을 보낸다는 건 명시적으로 "스트림을 따라가겠다"는 의도 — 사용자가
    // 직전 답을 읽으려 위로 올려 뒀더라도 자동 스크롤을 다시 켠다.
    setAutoFollow(true);
    setHistory((h) => [...h, { role: 'user', content: question }]);
    setPending('');

    try {
      // 라이브 노트북 내용을 끌어와, "이 코드 리팩토링 해줘" 같은 후속 요청이
      // 사용자가 실제로 보고 있는 셀을 함께 싣게 한다. 채팅 UI엔 여전히
      // 원본 질문만 보이고, API 페이로드만 컨텍스트로 증강된다.
      const { prompt: nbPrompt } = await fetchNotebookContext();
      const augmentedQuestion = nbPrompt
        ? `${nbPrompt}\n\n---\n\n사용자 요청:\n${question}`
        : question;

      const res = await fetch('/api/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: augmentedQuestion,
          history,
          connection_id: connectionId,
        }),
      });
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
      }
      // 응답은 NDJSON 스트림(줄마다 하나의 JSON: {chunk} 또는 {error}). 읽은
      // 바이트를 버퍼에 모았다가 개행(\n) 단위로 잘라 한 줄씩 파싱한다 —
      // 청크 경계가 줄 중간을 가를 수 있으므로 완전한 한 줄이 모일 때까지 기다린다.
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      let assembled = ''; // 지금까지 누적된 응답 본문(부분 렌더 + 최종 커밋용)
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let nl: number;
        while ((nl = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, nl).trim();
          buf = buf.slice(nl + 1);
          if (!line) continue;
          try {
            const obj = JSON.parse(line);
            if (obj.error) {
              throw new Error(obj.error);
            }
            if (obj.chunk) {
              assembled += obj.chunk;
              setPending(assembled); // 부분 응답을 실시간 렌더(스트리밍 표시)
            }
          } catch (e) {
            // 진짜 에러면 아래 catch로 던진다(불완전한 JSON 한 줄은 제외).
            if ((e as Error).message !== 'JSON.parse') throw e;
          }
        }
      }
      // 완성된 답을 대화 이력에 커밋한다. 코드는 사용자가 실제로 요청했을
      // 때만(삽입/넣어/셀에…) 노트북에 자동 삽입한다. 그렇지 않으면 수동
      // "셀에 삽입" 버튼만 달아, 그냥 읽어 보려던 코드로 노트북을 어지럽히지 않는다.
      setHistory((h) => [...h, { role: 'assistant', content: assembled }]);
      setPending('');
      const blocks = splitMarkdownCodeBlocks(assembled)[0].blocks;
      // 사용자 "질문"의 의도로 자동 삽입 여부를 가른다(응답 내용이 아니라).
      const wantsInsert = /(삽입|넣어|넣고|셀에|셀\s*추가|추가해|추가 해|insert|add\s*cell)/i.test(question);
      if (wantsInsert) {
        // 이번 전송에 고유한 시퀀스를 발급(++) — 블록 키를 "seq:idx"로 만들어
        // 같은 블록의 중복 삽입을 막는다. setHistory 부수효과가 아니라 ref에서
        // 증가시켜야 React 18의 업데이터 지연 버그를 피한다(위 insertedRef 설명).
        const seq = ++sendSeqRef.current;
        for (let k = 0; k < blocks.length; k++) {
          const key = `${seq}:${k}`;
          if (insertedRef.current.has(key)) continue; // 이미 삽입한 블록은 건너뜀
          insertedRef.current.add(key);
          // 한 블록 삽입이 터져도 답변 전체를 실패시키지 않는다 — 수동
          // "셀에 삽입" 버튼이 폴백으로 남아 있다.
          try {
            await onInsert(blocks[k]);
          } catch {
            /* 이미 setError로 인라인 노출됨 */
          }
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // 코드 블록 하나를 노트북에 삽입하고, 감사 로그를 남기고, 결과 토스트를 띄운다.
  const onInsert = async (block: CopilotCodeBlock) => {
    setError(null);
    try {
      const { path, mode } = await insertCellIntoNotebook(block.language, block.source);
      // 셀 삽입을 감사 추적(audit trail)에 기록 — 감사자(Auditor)가 어떤 생성
      // 코드가 어느 노트북에 들어갔는지 정확히 볼 수 있게 한다. 코드 본문이
      // 아니라 길이(source_length)만 보내 민감 내용 노출을 피한다.
      try {
        await fetch('/api/copilot/cell-inserted', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            notebook_path: path,
            language: block.language,
            source_length: block.source.length,
            connection_id: connectionId,
          }),
        });
      } catch {
        // 감사 기록 실패가 사용자에게 보이는 동작을 깨면 안 된다 — 사용자는
        // 성공 토스트를 보고, 감사 실패는 백엔드 로그에만 남긴다.
      }
      setLastInsert(`${block.language.toUpperCase()} 셀이 ${path} 에 추가됨`);
      window.setTimeout(() => setLastInsert(null), 4000); // 4초 후 토스트 자동 사라짐
      // 라이브 삽입은 Lab 안에 이미 보인다 — REST 폴백(Lab 몰래 디스크 파일이
      // 바뀐 경우)일 때만 iframe 새로고침이 필요하다.
      if (mode === 'rest') onCellInserted?.();
    } catch (e) {
      setError(`셀 삽입 실패: ${(e as Error).message}`);
    }
  };

  return (
    // CopilotPanel은 AppShell.Main 안에 있는데, Mantine이 이를 여러 겹의 레이아웃
    // 으로 크기 잡아 순진한 height:100% 사슬이 끊긴다. 그래서 패널 자체를 뷰포트
    // 기준 높이로 고정해, 채팅 리스트가 항상 스크롤 가능한 "경계 있는" 박스를
    // 갖게 한다. 88px ≈ 위쪽 SPA 헤더(44) + 패널 헤더(~44).
    <Stack
      p="sm"
      gap="sm"
      style={{ height: 'calc(100vh - 88px)', overflow: 'hidden' }}
    >
      <Group justify="space-between">
        <Title order={5}>🤖 다분석할Zini</Title>
        {providerName && <Badge variant="light">{providerName}</Badge>}
      </Group>

      <div
        ref={chatRef}
        onScroll={onChatScroll}
        data-testid="copilot-chat"
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          paddingRight: 4,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          position: 'relative',
        }}
      >
        {history.length === 0 && !pending && (
          <Text size="sm" c="dimmed" style={{ flexShrink: 0 }}>
            예: "지난 30일 매출 상위 도시 5개 알려줘" — 커넥션을 고르면 스키마 컨텍스트를 자동 주입합니다.
            응답에 SQL/Python 코드가 포함되면 현재 활성화된 노트북에 자동으로 셀을 추가합니다
            (열린 노트북이 없으면 {COPILOT_NOTEBOOK_NAME}).
          </Text>
        )}

        {history.map((m, i) => {
          const blocks =
            m.role === 'assistant' ? splitMarkdownCodeBlocks(m.content)[0].blocks : [];
          const narration =
            m.role === 'assistant' && blocks.length > 0
              ? stripCodeFences(m.content)
              : m.content;
          return (
            // flexShrink: 0 — 없으면 flex-column 채팅 컨테이너가 옛 메시지를
            // 스크롤하는 대신 min-content로 짓눌러 버린다("기존 대화가 짜부되는" 버그).
            <Card key={i} withBorder padding="sm" radius="sm" style={{ flexShrink: 0 }}>
              <Group gap="xs" mb={4}>
                <Badge size="xs" color={m.role === 'user' ? 'blue' : 'grape'}>
                  {m.role === 'user' ? '나' : 'Zini'}
                </Badge>
              </Group>
              {/* 코드가 포함된 답변: 코드 자체가 아니라 그 주변 산문만 보여
                 준다 — 코드는 copilot.ipynb에 들어간다. 순수 텍스트 답변
                 ("스키마를 알려주세요" 등)은 그대로 보여 준다. */}
              {narration && <Markdown>{narration}</Markdown>}
              {m.role === 'assistant' && blocks.length > 0 && (
                <Group mt={6} gap="xs">
                  {blocks.map((b, k) => (
                    <Badge
                      key={k}
                      variant="light"
                      color={b.language === 'sql' ? 'teal' : 'orange'}
                      size="sm"
                    >
                      {b.language.toUpperCase()} #{k + 1}
                    </Badge>
                  ))}
                  <Button
                    size="xs"
                    variant="light"
                    color="grape"
                    onClick={() => blocks.forEach((b) => onInsert(b))}
                  >
                    📥 셀에 삽입
                  </Button>
                </Group>
              )}
            </Card>
          );
        })}

        {pending && (
          <Card withBorder padding="sm" radius="sm" bg="gray.0" style={{ flexShrink: 0 }}>
            <Group gap="xs" mb={4}>
              <Loader size="xs" />
              <Badge size="xs" color="grape">코파일럿</Badge>
            </Group>
            <Markdown>{pending}</Markdown>
          </Card>
        )}
      </div>

      {!autoFollow && (
        <Group justify="center">
          <Button size="xs" variant="light" onClick={scrollToLatest}>
            ▼ 최신 메시지로
          </Button>
        </Group>
      )}
      {error && <Notification color="red" title="실패" onClose={() => setError(null)}>{error}</Notification>}
      {lastInsert && <Notification color="green" title="삽입 완료" onClose={() => setLastInsert(null)}>{lastInsert}</Notification>}

      <Group gap={6}>
        <Textarea
          placeholder="자연어로 질문하세요…"
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send();
          }}
          autosize
          minRows={2}
          maxRows={6}
          style={{ flex: 1 }}
        />
        <Button onClick={send} loading={busy} disabled={!input.trim()}>
          ▶ 보내기
        </Button>
      </Group>
      <Text size="xs" c="dimmed">⌘/Ctrl + Enter 로 전송 — 응답은 스트리밍됩니다.</Text>
    </Stack>
  );
}

// JupyterLab(좌) + 코파일럿 패널(우)을 나란히 놓고, 가운데 구분선을 드래그해
// 패널 폭을 조절하거나 패널을 접을 수 있게 하는 레이아웃 컨테이너.
function JupyterWithCopilot() {
  // DB 커넥션은 의도적으로 뺐다 — 이건 내부망·파일 업로드 워크플로(데이터
  // 파일을 JupyterLab으로 직접 올림)다. 코파일럿은 커넥션 없이도 동작한다
  // (일반 Python/pandas 도움).

  // 접을 수 있고 드래그로 폭 조절되는 코파일럿 패널 상태.
  // draggingRef와 dragging(state)를 둘 다 두는 이유: ref는 mousemove 핸들러가
  // 클로저에 갇히지 않고 "지금 드래그 중인가"를 즉시 읽기 위함, state는 드래그
  // 중 시각 효과(구분선 색·오버레이)를 리렌더로 반영하기 위함.
  const [panelOpen, setPanelOpen] = useState(true);
  const [panelWidth, setPanelWidth] = useState(420);
  const draggingRef = useRef(false);
  const [dragging, setDragging] = useState(false);
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!draggingRef.current) return;
      // 패널이 오른쪽 끝에 붙어 있으므로 폭 = 커서에서 그 끝까지의 거리.
      // 320~900px로 클램프해 너무 좁거나 넓어지지 않게 한다.
      setPanelWidth(Math.min(900, Math.max(320, window.innerWidth - e.clientX)));
      e.preventDefault();
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      setDragging(false);
      document.body.style.userSelect = ''; // 드래그 중 막아둔 텍스트 선택 복원
    };
    // 드래그는 커서가 구분선을 벗어나도 이어져야 하므로 window 전역에 건다.
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', position: 'relative' }}>
      <div style={{ flex: '1 1 auto', minWidth: 280, height: '100%' }}>
        <JupyterLab connectionId={null} />
      </div>

      {/* 드래그 중에는 이 오버레이가 iframe 위를 덮어, 부모가 계속
          mousemove/mouseup을 받게 한다 — 안 그러면 iframe이 이벤트를 삼켜
          버튼을 떼도 리사이즈가 "들러붙어" 따라온다. */}
      {dragging && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, cursor: 'col-resize' }} />
      )}

      {panelOpen ? (
        <>
          {/* 이 구분선을 드래그하면 패널 폭이 조절된다. */}
          <div
            onMouseDown={(e) => {
              e.preventDefault();
              draggingRef.current = true;
              setDragging(true);
              document.body.style.userSelect = 'none';
            }}
            title="드래그해서 크기 조절"
            style={{ flex: '0 0 auto', width: 6, cursor: 'col-resize', background: dragging ? '#7048e8' : '#e9ecef' }}
          />
          <div
            style={{
              flex: '0 0 auto',
              width: panelWidth,
              minWidth: 300,
              height: '100%',
              borderLeft: '1px solid #e9ecef',
              background: '#fafafa',
            }}
          >
            <Stack p={0} gap={0} style={{ height: '100%' }}>
              <Group p="xs" gap="xs" align="center" justify="flex-end" wrap="nowrap" style={{ borderBottom: '1px solid #e9ecef' }}>
                <Button
                  size="xs"
                  variant="light"
                  color="grape"
                  onClick={() => setPanelOpen(false)}
                  title="패널 숨기기"
                >
                  숨기기
                </Button>
              </Group>
              <div style={{ flex: 1, minHeight: 0 }}>
                <CopilotPanel connectionId={null} />
              </div>
            </Stack>
          </div>
        </>
      ) : (
        // 우상단 가장자리 탭 — 클릭하면 패널이 슬라이드되어 나온다. 눈에 잘
        // 띄도록 더 크고 높게 배치했다.
        <div
          role="button"
          tabIndex={0}
          onClick={() => setPanelOpen(true)}
          title="다분석할Zini 열기"
          style={{
            position: 'absolute',
            top: 16,
            right: 0,
            zIndex: 5,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 6,
            padding: '14px 9px',
            background: '#7048e8',
            color: '#fff',
            borderRadius: '10px 0 0 10px',
            boxShadow: '-2px 2px 10px rgba(0,0,0,.22)',
            fontWeight: 700,
            lineHeight: 1,
          }}
        >
          <span style={{ fontSize: 20 }}>‹</span>
          <span style={{ writingMode: 'vertical-rl', letterSpacing: 1, fontSize: 13 }}>다분석할Zini</span>
        </div>
      )}
    </div>
  );
}

// 본인 비밀번호 변경 모달. 헤더의 "비밀번호 변경" 버튼이 opened를 제어한다.
// 자체 폼 상태(현재/새/확인)와 제출·검증을 모두 안에서 처리하고, 성공 시 성공
// 화면으로 전환한다. 현재 비밀번호 확인은 서버가 하므로, 여기선 새 비밀번호의
// 길이(>=4)와 확인 일치만 사전 검증해 불필요한 왕복을 줄인다.
function ChangePasswordModal({
  opened,
  onClose,
  forced = false,
}: {
  opened: boolean;
  onClose: () => void;
  // forced: 초기 비밀번호 미변경 상태에서 자동으로 열린 경우. 상단에 변경 권유 안내를 띄운다.
  forced?: boolean;
}) {
  const qc = useQueryClient();
  const [cur, setCur] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);

  // 모달을 닫을 때마다 입력·상태를 초기화해, 다음에 열 때 이전 입력이 남지 않게 한다.
  const close = () => {
    setCur('');
    setNext('');
    setConfirm('');
    setErr(null);
    setOk(false);
    setBusy(false);
    onClose();
  };

  const submit = async () => {
    setErr(null);
    if (next.length < 4) {
      setErr('새 비밀번호는 최소 4자입니다.');
      return;
    }
    if (next !== confirm) {
      setErr('새 비밀번호가 일치하지 않습니다.');
      return;
    }
    setBusy(true);
    try {
      await api.changePassword(cur, next);
      // 변경 성공 → /me를 다시 불러 must_change_password가 false로 갱신되게 한다
      // (강제 안내 팝업이 다시 열리지 않도록).
      qc.invalidateQueries({ queryKey: ['me'] });
      setOk(true);
    } catch {
      // 서버가 400/401을 주면 여기로 온다. 어느 쪽이든 사용자가 할 일은 같으므로
      // (현재 비밀번호 재확인) 메시지를 하나로 합친다.
      setErr('현재 비밀번호가 올바르지 않거나 변경할 수 없습니다.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal opened={opened} onClose={close} title="비밀번호 변경">
      <Stack>
        {ok ? (
          <>
            <Text c="teal" size="sm">비밀번호가 변경되었습니다.</Text>
            <Group justify="flex-end">
              <Button onClick={close}>닫기</Button>
            </Group>
          </>
        ) : (
          <>
            {/* 강제(첫 로그인) 상황이면 변경을 권유하는 안내 문구를 띄운다 */}
            {forced && (
              <Notification color="orange" withCloseButton={false} title="초기 비밀번호 변경 권장">
                관리자가 설정한 초기 비밀번호로 로그인했습니다. 보안을 위해 비밀번호를 변경해 주세요.
              </Notification>
            )}
            <PasswordInput
              label="현재 비밀번호"
              value={cur}
              onChange={(e) => setCur(e.currentTarget.value)}
            />
            <PasswordInput
              label="새 비밀번호"
              description="최소 4자"
              value={next}
              onChange={(e) => setNext(e.currentTarget.value)}
            />
            <PasswordInput
              label="새 비밀번호 확인"
              value={confirm}
              onChange={(e) => setConfirm(e.currentTarget.value)}
            />
            {err && <Text c="red" size="sm">{err}</Text>}
            <Group justify="flex-end">
              <Button variant="default" onClick={close}>취소</Button>
              {/* 현재 비번 미입력·새 비번 4자 미만이면 비활성화 */}
              <Button loading={busy} disabled={!cur || next.length < 4} onClick={submit}>
                변경
              </Button>
            </Group>
          </>
        )}
      </Stack>
    </Modal>
  );
}

// 앱 껍데기 — 인증 게이트 + 헤더/사이드바/메인 레이아웃 + 라우팅을 묶는다.
function Shell() {
  const me = useQuery({ queryKey: ['me'], queryFn: api.me });
  const loc = useLocation();
  // JupyterLab은 자체 좌측 패널을 위해 전체 뷰포트가 필요하다(그래서 SPA
  // 사이드바를 접는다). 그 외 라우트는 기본적으로 SPA 사이드바를 보인다.
  const isJupyter = loc.pathname === '/' || loc.pathname === '';
  const [navOpen, setNavOpen] = useState(false);
  // 비밀번호 변경 모달 열림 상태. 헤더 버튼이 켜고, 모달이 onClose로 끈다.
  const [pwOpen, setPwOpen] = useState(false);
  // 첫 로그인(관리자 지정 초기 비밀번호 미변경)이면 변경 모달을 자동으로 띄운다.
  // 변경에 성공하면 ['me']가 갱신되어 must_change_password가 false가 되므로 다시 열리지 않는다.
  useEffect(() => {
    if (me.data?.must_change_password) setPwOpen(true);
  }, [me.data?.must_change_password]);
  // Jupyter 화면에서는 사용자가 햄버거로 명시적으로 열지 않는 한 사이드바를 접는다.
  const navCollapsed = isJupyter && !navOpen;

  // 인증 확인이 진행 중이면 가벼운 로더만 보여 준다.
  // api.me()는 401에서 /login/으로 리다이렉트하므로, 세션이 유효함이 확인된
  // 뒤에야 앱 본체를 렌더한다(미인증 화면 깜빡임 방지).
  if (me.isLoading || me.isError) {
    return (
      <Group justify="center" align="center" style={{ height: '100vh' }}>
        <Loader />
      </Group>
    );
  }

  // 로그아웃: 백엔드 세션 + JupyterHub 세션을 모두 지운 뒤, 성공/실패와
  // 무관하게 로그인 페이지로 보낸다(finally) — 서버 응답이 실패해도 클라이언트는
  // 일단 빠져나가게 한다. 허브 로그아웃(/jupyter/hub/logout)을 함께 호출하는
  // 이유: dp_session만 지우면 허브 로그인 쿠키와 사용자 노트북 컨테이너가 남아,
  // 공용 PC에서 앞사람 서버가 RAM을 계속 점유한다(유출은 아님 — 다음 사람이
  // 토큰으로 재로그인하면 허브가 그 사람으로 전환). 허브 logout은 쿠키를 지우고,
  // 허브 설정의 shutdown_on_logout=True가 그 사용자 컨테이너를 즉시 회수한다.
  // 두 호출 모두 best-effort(실패해도 무시) — 어차피 로그인 페이지로 나간다.
  const handleLogout = async () => {
    try {
      await Promise.allSettled([
        fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }),
        // 허브 logout은 GET. 리다이렉트 본문은 필요 없으니 결과를 보지 않는다.
        fetch('/jupyter/hub/logout', { credentials: 'include' }),
      ]);
    } finally {
      window.location.assign('/login/');
    }
  };

  return (
    <>
    <AppShell
      header={{ height: 44 }}
      navbar={{
        width: 220,
        breakpoint: 'sm',
        collapsed: { desktop: navCollapsed, mobile: navCollapsed },
      }}
      padding={0}
    >
      <AppShell.Header>
        <Group h="100%" px="sm" justify="space-between">
          <Group gap="xs">
            <Burger
              opened={!navCollapsed}
              onClick={() => setNavOpen((o) => !o)}
              size="sm"
              aria-label="사이드바 토글"
            />
            <Title order={5}>🧪 Analyst Workspace</Title>
          </Group>
          {me.data && (
            <Group gap="xs">
              <Text size="sm" c="dimmed">{me.data.display_name ?? me.data.email}</Text>
              {me.data.roles.map((r) => (
                <Badge key={r} variant="light">{r}</Badge>
              ))}
              <Button size="xs" variant="subtle" color="gray" onClick={() => setPwOpen(true)}>
                비밀번호 변경
              </Button>
              <Button size="xs" variant="subtle" color="gray" onClick={handleLogout}>
                로그아웃
              </Button>
            </Group>
          )}
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="sm">
        <NavLink
          component={Link}
          to="/"
          label="📓  JupyterLab"
          onClick={() => setNavOpen(false)}
        />
      </AppShell.Navbar>
      <AppShell.Main
        style={{
          // 위 44px는 고정 헤더를 피하기 위함. JupyterLab 임베드는 자체 좌측
          // 레일이 있어 전체 뷰포트를 원하므로 SPA 사이드바 여백(좌측 220px)을
          // 없앤다. 그 외 라우트는 220px 사이드바 너머로 밀어, 액션 버튼이
          // 사이드바 뒤에 가리지 않게 한다.
          padding: isJupyter ? '44px 0 0 0' : '44px 0 0 220px',
          height: '100vh',
          boxSizing: 'border-box',
          overflow: isJupyter ? 'hidden' : 'auto',
        }}
      >
        <Routes>
          <Route path="/" element={<JupyterWithCopilot />} />
          {/* 빠른 SQL / 내 노트북 페이지는 비활성화 — JupyterLab + LLM 중심. */}
          <Route path="*" element={<JupyterWithCopilot />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
    {/* 비밀번호 변경 모달은 Mantine이 포털로 body에 렌더하므로 위치는 무관하지만,
        AppShell 바깥 형제로 두어 레이아웃 계산에 끼어들지 않게 한다 */}
    <ChangePasswordModal
      opened={pwOpen}
      onClose={() => setPwOpen(false)}
      forced={!!me.data?.must_change_password}
    />
    </>
  );
}

// 앱 부트스트랩 — Provider를 바깥에서부터 감싼다(테마 → react-query → 라우터).
// basename="/analyst": 포털 게이트웨이가 이 SPA를 /analyst 하위 경로로
// 서빙하므로, 라우터가 그 접두사를 기준으로 경로를 해석하게 한다(vite base와 일치).
ReactDOM.createRoot(document.getElementById('root')!).render(
  <MantineProvider>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/analyst">
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  </MantineProvider>
);
