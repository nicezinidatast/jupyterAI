import { useEffect, useMemo, useRef, useState } from 'react';
import ReactDOM from 'react-dom/client';
import {
  AppShell,
  Badge,
  Burger,
  Button,
  Card,
  Code,
  Group,
  Loader,
  MantineProvider,
  NavLink,
  Notification,
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

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

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
};

const api = {
  me: () => fetch('/api/auth/me').then((r) => r.json() as Promise<Me>),
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

const SAMPLE_SQL: Record<string, string> = {
  sales_db: 'SELECT name, email, phone, rrn, city FROM sales.customers LIMIT 25',
  crm_mysql: 'SELECT lead_name, email, stage FROM leads LIMIT 25',
  warehouse_hive: 'SELECT event_date, channel, revenue FROM events_daily LIMIT 30',
};

function ChartPicker({ result }: { result: QueryResult }) {
  const [chartType, setChartType] = useState<'line' | 'bar' | 'scatter' | 'pie' | 'area' | 'box' | 'heatmap'>('bar');
  const numericCols = result.columns.filter((c) =>
    result.rows.every((r) => typeof r[c] === 'number')
  );
  const [x, setX] = useState<string>(result.columns[0]);
  const [y, setY] = useState<string>(numericCols[0] ?? result.columns[1] ?? result.columns[0]);

  useEffect(() => {
    if (!result.columns.includes(x)) setX(result.columns[0]);
    if (!result.columns.includes(y)) setY(numericCols[0] ?? result.columns[1] ?? result.columns[0]);
  }, [result.columns]);

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

function FileUploadCard() {
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onFiles = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setError(null);
    setBusy(true);
    const form = new FormData();
    form.append('upload', files[0]);
    try {
      const r = await fetch('/api/files/upload', { method: 'POST', body: form });
      if (!r.ok) {
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

function QueryEditor() {
  const qc = useQueryClient();
  const conns = useQuery({ queryKey: ['conns'], queryFn: api.connections });
  const me = useQuery({ queryKey: ['me'], queryFn: api.me });
  const nbs = useQuery({ queryKey: ['nbs'], queryFn: api.notebooks });

  const [connId, setConnId] = useState<string | null>(null);
  const [sql, setSql] = useState('');

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

  const run = useMutation({
    mutationFn: () => api.runQuery({ connection_id: connId!, sql }),
  });

  const save = useMutation({
    mutationFn: async () => {
      if (!nbs.data?.length || !me.data) throw new Error('no notebook to save to');
      const content = {
        title: 'Ad-hoc query result',
        cells: [
          { kind: 'sql', connection_id: connId, sql },
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
        {schema.data && (
          <Group gap="xs">
            {schema.data.tables.map((t) => {
              const colNames = t.columns.map((c) => c.name).slice(0, 4).join(', ');
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

function NotebookDetail() {
  const { id } = useParams();
  const nb = useQuery({
    queryKey: ['nb', id],
    queryFn: () => api.latestNotebook(id!),
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

function JupyterLab({ reloadToken }: { reloadToken: number }) {
  // Land directly on copilot.ipynb so the user sees freshly-inserted cells
  // without having to navigate the file browser. The `reloadToken` is bumped
  // by the parent after every PUT so we re-mount the iframe and re-read the
  // notebook from disk (JupyterLab itself does not auto-refresh on external
  // file changes — it only shows a "changed on disk" modal that the user
  // would have to click every single time).
  //
  // While the new iframe is loading we fade the contents so the user sees a
  // smooth transition instead of a hard white flash.
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
  }, [reloadToken]);

  const src = `/jupyter/lab/tree/copilot.ipynb?token=dataplatform&reset&t=${reloadToken}`;
  return (
    <iframe
      key={reloadToken}
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
// Jupyter cell injection — append a code cell to the shared copilot.ipynb
// ---------------------------------------------------------------------------
const COPILOT_NOTEBOOK = 'copilot.ipynb';
const JUPYTER_TOKEN = 'dataplatform';

async function appendCellToCopilotNotebook(language: 'sql' | 'python', source: string): Promise<void> {
  const url = `/jupyter/api/contents/${COPILOT_NOTEBOOK}`;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    Authorization: `token ${JUPYTER_TOKEN}`,
    // Belt-and-suspenders against a stale GET hiding cells the user (or a
    // previous turn) just added — the browser otherwise reuses the cached
    // body and the next PUT would clobber the new cells.
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache',
  };

  let notebook: any | null = null;
  // `?_=` cache buster — jupyter ignores unknown query params.
  const head = await fetch(`${url}?_=${Date.now()}`, {
    headers,
    credentials: 'omit',
    cache: 'no-store',
  });
  if (head.ok) {
    notebook = await head.json();
  }
  if (!notebook) {
    notebook = {
      type: 'notebook',
      content: {
        cells: [],
        metadata: { kernelspec: { name: 'python3', display_name: 'Python 3' } },
        nbformat: 4,
        nbformat_minor: 5,
      },
      format: 'json',
      name: COPILOT_NOTEBOOK,
      path: COPILOT_NOTEBOOK,
    };
  }
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
  notebook.name = COPILOT_NOTEBOOK;
  notebook.path = COPILOT_NOTEBOOK;

  const put = await fetch(url, {
    method: 'PUT',
    headers,
    credentials: 'omit',
    body: JSON.stringify({
      type: 'notebook',
      format: 'json',
      content: notebook.content,
    }),
  });
  if (!put.ok) {
    throw new Error(`Jupyter PUT failed: ${put.status}`);
  }
}

// ---------------------------------------------------------------------------
// Active-notebook targeting — the portal serves the SPA and JupyterLab from
// the SAME origin, so we can reach into the iframe and use the live Lab app
// (`window.jupyterapp`, exposed via --LabApp.expose_app_in_browser=True).
// Cells inserted through the live shared model appear instantly in whatever
// notebook the analyst is working in — no iframe reload, no "changed on
// disk" conflict dialog.
// ---------------------------------------------------------------------------
function getJupyterApp(): any | null {
  const iframe = document.querySelector<HTMLIFrameElement>("iframe[title='JupyterLab']");
  try {
    const w = iframe?.contentWindow as any;
    return w?.jupyterapp ?? w?.jupyterlab ?? null;
  } catch {
    return null; // cross-origin or iframe not ready — fall back to REST
  }
}

function isNotebookPanel(w: any): boolean {
  // context.isReady gate: while Lab is still loading the file the panel's
  // model is EMPTY — addCell + save on it would clobber the real notebook
  // on disk with just the new cell. Not-ready panels are treated as "no
  // notebook open" so the caller takes the safe REST append path instead.
  return Boolean(
    w?.context?.path?.endsWith?.('.ipynb') &&
      w?.content?.model?.sharedModel &&
      w?.context?.isReady !== false,
  );
}

// The notebook the analyst is actually looking at. Priority:
//   1. the focused main-area widget, if it's a notebook
//   2. the notebook whose tab is visible in the main dock (focus tracking
//      can be empty when the iframe never received browser focus)
//   3. the first open notebook in the main area (e.g. Launcher tab focused)
//   4. null → caller falls back to the REST copilot.ipynb path
function getActiveNotebookPanel(): any | null {
  const app = getJupyterApp();
  if (!app) return null;
  const cur = app.shell?.currentWidget;
  if (isNotebookPanel(cur)) return cur;
  try {
    let firstNotebook: any | null = null;
    for (const w of app.shell.widgets('main')) {
      if (!isNotebookPanel(w)) continue;
      if (w.isVisible) return w;
      if (!firstNotebook) firstNotebook = w;
    }
    return firstNotebook;
  } catch {
    /* lumino iterator mismatch — treat as "no notebook open" */
  }
  return null;
}

async function insertCellIntoNotebook(
  language: 'sql' | 'python',
  source: string,
): Promise<{ path: string; mode: 'live' | 'rest' }> {
  const panel = getActiveNotebookPanel();
  if (panel) {
    try {
      panel.content.model.sharedModel.addCell({
        cell_type: 'code',
        source: language === 'sql' ? `%%sql\n${source}` : source,
        metadata: { copilot_generated: true, language },
      });
      try {
        await panel.context.save();
      } catch {
        // The cell is already in the live model; a failed save just means
        // the analyst saves manually later. Don't fail the insert for it.
      }
      return { path: panel.context.path as string, mode: 'live' };
    } catch {
      // Any live-path surprise (Lab mid-boot, API drift) — fall through to
      // the REST append below rather than dropping the cell.
    }
  }
  await appendCellToCopilotNotebook(language, source);
  return { path: COPILOT_NOTEBOOK, mode: 'rest' };
}

// ---------------------------------------------------------------------------
// CopilotPanel — chat with the LLM, render code blocks with insert buttons
// ---------------------------------------------------------------------------
type CopilotMsg = { role: 'user' | 'assistant'; content: string };
type CopilotCodeBlock = { language: 'sql' | 'python'; source: string };

function splitMarkdownCodeBlocks(text: string): Array<{ text: string; blocks: CopilotCodeBlock[] }> {
  // We keep one "segment" with the full text plus a list of detected blocks.
  // The block list lets us render "Insert as cell" buttons under the message.
  const blocks: CopilotCodeBlock[] = [];
  const re = /```(sql|python)\n([\s\S]*?)```/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    blocks.push({ language: m[1].toLowerCase() as 'sql' | 'python', source: m[2].trim() });
  }
  return [{ text, blocks }];
}

// The chat shows the prose AROUND the code blocks, not the code itself —
// the code lives in copilot.ipynb. Strip fenced blocks + collapse whitespace.
function stripCodeFences(text: string): string {
  return text
    .replace(/```(sql|python)\n[\s\S]*?```/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// Pull the active notebook's cells so the model can refer to / refactor them
// in the next turn. Live shared model first (includes unsaved edits the
// analyst is looking at right now), REST copilot.ipynb as the fallback.
function buildNotebookContextPrompt(
  path: string,
  codeCells: string[],
): { prompt: string; cellCount: number } {
  if (codeCells.length === 0) return { prompt: '', cellCount: 0 };
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

async function fetchNotebookContext(): Promise<{
  prompt: string;
  cellCount: number;
}> {
  const panel = getActiveNotebookPanel();
  if (panel) {
    try {
      const shared = panel.content.model.sharedModel;
      const codeCells: string[] = [];
      for (const c of shared.cells ?? []) {
        if (c?.cell_type !== 'code') continue;
        const s = (
          typeof c.getSource === 'function' ? c.getSource() : String(c.source ?? '')
        ).trim();
        if (s) codeCells.push(s);
      }
      return buildNotebookContextPrompt(panel.context.path as string, codeCells);
    } catch {
      /* live read failed — fall through to the REST path below */
    }
  }

  // Hard 4 s ceiling — if Jupyter is restarting / slow, ship the question
  // without context rather than blocking the chat indefinitely.
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), 4000);
  try {
    const r = await fetch(
      `/jupyter/api/contents/${COPILOT_NOTEBOOK}?_=${Date.now()}`,
      {
        headers: {
          Authorization: `token ${JUPYTER_TOKEN}`,
          'Cache-Control': 'no-cache',
        },
        cache: 'no-store',
        signal: ctrl.signal,
      },
    );
    if (!r.ok) return { prompt: '', cellCount: 0 };
    const nb = await r.json();
    const cells: any[] = nb?.content?.cells ?? [];
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
  // Track which (sendSeq, blockIdx) pairs have already auto-inserted so
  // re-renders don't fire duplicate PUT/audit round-trips for the same block.
  // The key MUST NOT come from a setHistory updater side effect — React 18
  // may defer the updater past the insert loop, leaving every turn keyed
  // "-1:0" and silently skipping all auto-inserts after the first message.
  const insertedRef = useRef<Set<string>>(new Set());
  const sendSeqRef = useRef(0);
  // The scrolling chat container. We follow the stream only while the user is
  // already pinned to the bottom — if they scroll up to re-read a past
  // question, streaming chunks must NOT yank the view back down.
  const chatRef = useRef<HTMLDivElement | null>(null);
  const [autoFollow, setAutoFollow] = useState(true);

  useEffect(() => {
    fetch('/api/copilot/provider')
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => j && setProviderName(j.provider))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!autoFollow) return;
    const el = chatRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [history, pending, autoFollow]);

  const onChatScroll = () => {
    const el = chatRef.current;
    if (!el) return;
    // 24 px tolerance so a tiny rounding gap still counts as "at the bottom".
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
    if (!input.trim() || busy) return;
    setError(null);
    const question = input.trim();
    setInput('');
    setBusy(true);
    // Sending a new question is an explicit "follow the stream" intent — re-arm
    // auto-scroll even if the user had scrolled up to read the previous answer.
    setAutoFollow(true);
    setHistory((h) => [...h, { role: 'user', content: question }]);
    setPending('');

    try {
      // Pull the live notebook contents so follow-up requests like "이 코드
      // 리팩토링 해줘" carry the actual cells the user is looking at. The
      // chat UI still shows the user's original question — only the API
      // payload is augmented.
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
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      let assembled = '';
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
              setPending(assembled);
            }
          } catch (e) {
            // Pass through to the catch below if it's a real error.
            if ((e as Error).message !== 'JSON.parse') throw e;
          }
        }
      }
      // Commit the assembled answer to history, then auto-insert every code
      // block we detect. The user explicitly asked for "make the code" → the
      // code lands in the active notebook without an extra click.
      setHistory((h) => [...h, { role: 'assistant', content: assembled }]);
      setPending('');
      const seq = ++sendSeqRef.current;
      const blocks = splitMarkdownCodeBlocks(assembled)[0].blocks;
      for (let k = 0; k < blocks.length; k++) {
        const key = `${seq}:${k}`;
        if (insertedRef.current.has(key)) continue;
        insertedRef.current.add(key);
        // Don't fail the whole reply if any one insert blows up — the manual
        // "다시 삽입" button is still rendered as a fallback.
        try {
          await onInsert(blocks[k]);
        } catch {
          /* surfaced inline via setError already */
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onInsert = async (block: CopilotCodeBlock) => {
    setError(null);
    try {
      const { path, mode } = await insertCellIntoNotebook(block.language, block.source);
      // Record the cell insertion in the audit trail so the Auditor can see
      // exactly which generated code landed in which notebook.
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
        // Audit failure must not break the user-visible action; the user
        // sees the success toast, the backend logs the audit failure.
      }
      setLastInsert(`${block.language.toUpperCase()} 셀이 ${path} 에 추가됨`);
      window.setTimeout(() => setLastInsert(null), 4000);
      // Live inserts are already visible inside Lab — only the REST fallback
      // (file changed on disk behind Lab's back) needs an iframe reload.
      if (mode === 'rest') onCellInserted?.();
    } catch (e) {
      setError(`셀 삽입 실패: ${(e as Error).message}`);
    }
  };

  return (
    // The CopilotPanel lives inside AppShell.Main, which Mantine sizes via
    // a layered layout that breaks naïve height:100% chains. Pin the panel
    // itself to a viewport-relative height so the chat list always gets a
    // bounded box to scroll inside.
    //   88 px ≈ SPA header (44) + panel-header (~44) above us.
    <Stack
      p="sm"
      gap="sm"
      style={{ height: 'calc(100vh - 88px)', overflow: 'hidden' }}
    >
      <Group justify="space-between">
        <Title order={5}>🤖 분석 코파일럿</Title>
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
            (열린 노트북이 없으면 {COPILOT_NOTEBOOK}).
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
            // flexShrink: 0 — without it the flex-column chat container
            // compresses old messages to min-content instead of scrolling
            // (the "기존 대화가 짜부되는" bug).
            <Card key={i} withBorder padding="sm" radius="sm" style={{ flexShrink: 0 }}>
              <Group gap="xs" mb={4}>
                <Badge size="xs" color={m.role === 'user' ? 'blue' : 'grape'}>
                  {m.role === 'user' ? '나' : '코파일럿'}
                </Badge>
              </Group>
              {/* Code answers: show the prose around the code (if any), not
                 the code itself — the code lives in copilot.ipynb. Pure-text
                 answers ("스키마를 알려주세요" 등) are shown unchanged. */}
              {narration && (
                <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                  {narration}
                </Text>
              )}
              {m.role === 'assistant' && blocks.length > 0 && (
                <Group mt={6} gap="xs">
                  <Badge variant="outline" color="green" size="sm">
                    ✅ {blocks.length}개 셀이 노트북에 자동 추가됨
                  </Badge>
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
                    variant="subtle"
                    onClick={() => blocks.forEach((b) => onInsert(b))}
                  >
                    🔁 다시 삽입
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
            <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>{pending}</Text>
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

function JupyterWithCopilot() {
  // Pick a default connection — the analyst likely wants sales_db context.
  const conns = useQuery({ queryKey: ['conns'], queryFn: api.connections });
  const defaultConn = conns.data?.find((c) => c.engine !== 'hive')?.connection_id ?? null;
  const [connId, setConnId] = useState<string | null>(null);
  const activeConn = connId ?? defaultConn;
  const [labReloadToken, setLabReloadToken] = useState(0);

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%' }}>
      <div style={{ flex: '1 1 65%', minWidth: 320, height: '100%' }}>
        <JupyterLab reloadToken={labReloadToken} />
      </div>
      <div style={{ flex: '0 0 35%', minWidth: 320, maxWidth: 600, height: '100%', borderLeft: '1px solid #e9ecef', background: '#fafafa' }}>
        <Stack p={0} gap={0} style={{ height: '100%' }}>
          <Group p="xs" gap="xs" align="center" style={{ borderBottom: '1px solid #e9ecef' }}>
            <Text size="xs" c="dimmed">커넥션 컨텍스트</Text>
            <Select
              size="xs"
              value={activeConn}
              data={(conns.data ?? []).map((c) => ({ value: c.connection_id, label: c.name }))}
              onChange={setConnId}
              placeholder="선택"
              style={{ flex: 1 }}
            />
          </Group>
          <div style={{ flex: 1, minHeight: 0 }}>
            <CopilotPanel
              connectionId={activeConn}
              onCellInserted={() => setLabReloadToken((n) => n + 1)}
            />
          </div>
        </Stack>
      </div>
    </div>
  );
}

function Shell() {
  const me = useQuery({ queryKey: ['me'], queryFn: api.me });
  const loc = useLocation();
  // JupyterLab needs the full viewport so its own left panel has room. Other
  // routes keep the SPA's navbar visible by default.
  const isJupyter = loc.pathname === '/' || loc.pathname === '';
  const [navOpen, setNavOpen] = useState(false);
  const navCollapsed = isJupyter && !navOpen;

  return (
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
        <NavLink
          component={Link}
          to="/sql"
          label="📝  빠른 SQL"
          onClick={() => setNavOpen(true)}
        />
        <NavLink
          component={Link}
          to="/notebooks"
          label="📚  내 노트북"
          onClick={() => setNavOpen(true)}
        />
      </AppShell.Navbar>
      <AppShell.Main
        style={{
          // 44px clears the fixed header; the JupyterLab embed wants the full
          // viewport (it has its own left rail) so we strip the SPA's navbar
          // gutter there. Every other route needs to push past the 220-px
          // navbar so the action buttons aren't hidden behind it.
          padding: isJupyter ? '44px 0 0 0' : '44px 0 0 220px',
          height: '100vh',
          boxSizing: 'border-box',
          overflow: isJupyter ? 'hidden' : 'auto',
        }}
      >
        <Routes>
          <Route path="/" element={<JupyterWithCopilot />} />
          <Route path="/sql" element={<QueryEditor />} />
          <Route path="/notebooks" element={<NotebookList />} />
          <Route path="/notebooks/:id" element={<NotebookDetail />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <MantineProvider>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/analyst">
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  </MantineProvider>
);
