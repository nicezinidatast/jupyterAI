import { createHotContext as __vite__createHotContext } from "/analyst/@vite/client";import.meta.hot = __vite__createHotContext("/src/main.tsx");import __vite__cjsImport0_react_jsxDevRuntime from "/analyst/node_modules/.vite/deps/react_jsx-dev-runtime.js?v=31add2ee"; const jsxDEV = __vite__cjsImport0_react_jsxDevRuntime["jsxDEV"];
import * as RefreshRuntime from "/analyst/@react-refresh";
const inWebWorker = typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope;
let prevRefreshReg;
let prevRefreshSig;
if (import.meta.hot && !inWebWorker) {
  if (!window.$RefreshReg$) {
    throw new Error(
      "@vitejs/plugin-react can't detect preamble. Something is wrong."
    );
  }
  prevRefreshReg = window.$RefreshReg$;
  prevRefreshSig = window.$RefreshSig$;
  window.$RefreshReg$ = RefreshRuntime.getRefreshReg("/app/src/main.tsx");
  window.$RefreshSig$ = RefreshRuntime.createSignatureFunctionForTransform;
}
var _s = $RefreshSig$(), _s2 = $RefreshSig$(), _s3 = $RefreshSig$(), _s4 = $RefreshSig$(), _s5 = $RefreshSig$(), _s6 = $RefreshSig$(), _s7 = $RefreshSig$(), _s8 = $RefreshSig$(), _s9 = $RefreshSig$();
import __vite__cjsImport3_react from "/analyst/node_modules/.vite/deps/react.js?v=31add2ee"; const useEffect = __vite__cjsImport3_react["useEffect"]; const useMemo = __vite__cjsImport3_react["useMemo"]; const useRef = __vite__cjsImport3_react["useRef"]; const useState = __vite__cjsImport3_react["useState"];
import __vite__cjsImport4_reactDom_client from "/analyst/node_modules/.vite/deps/react-dom_client.js?v=31add2ee"; const ReactDOM = __vite__cjsImport4_reactDom_client.__esModule ? __vite__cjsImport4_reactDom_client.default : __vite__cjsImport4_reactDom_client;
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
  Textarea,
  Title
} from "/analyst/node_modules/.vite/deps/@mantine_core.js?v=31add2ee";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "/analyst/node_modules/.vite/deps/@tanstack_react-query.js?v=31add2ee";
import __vite__cjsImport7_reactPlotly_js from "/analyst/node_modules/.vite/deps/react-plotly__js.js?v=31add2ee"; const Plot = __vite__cjsImport7_reactPlotly_js.__esModule ? __vite__cjsImport7_reactPlotly_js.default : __vite__cjsImport7_reactPlotly_js;
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useLocation,
  useParams
} from "/analyst/node_modules/.vite/deps/react-router-dom.js?v=31add2ee";
import "/analyst/node_modules/@mantine/core/styles.css";
const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } }
});
const api = {
  me: () => fetch("/api/auth/me").then((r) => r.json()),
  connections: () => fetch("/api/connections").then((r) => r.json()),
  schema: (id) => fetch(`/api/connections/${id}/schema`).then((r) => r.json()),
  runQuery: (body) => fetch("/api/queries/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, params: {} })
  }).then(async (r) => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  }),
  workspaces: () => fetch("/api/workspaces").then((r) => r.json()),
  notebooks: () => fetch("/api/notebooks").then((r) => r.json()),
  latestNotebook: (id) => fetch(`/api/notebooks/${id}/latest`).then((r) => r.json()),
  saveNotebook: (id, body) => fetch(`/api/notebooks/${id}/versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).then(async (r) => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  })
};
const SAMPLE_SQL = {
  sales_db: "SELECT name, email, phone, rrn, city FROM sales.customers LIMIT 25",
  crm_mysql: "SELECT lead_name, email, stage FROM leads LIMIT 25",
  warehouse_hive: "SELECT event_date, channel, revenue FROM events_daily LIMIT 30"
};
function ChartPicker({ result }) {
  _s();
  const [chartType, setChartType] = useState("bar");
  const numericCols = result.columns.filter(
    (c) => result.rows.every((r) => typeof r[c] === "number")
  );
  const [x, setX] = useState(result.columns[0]);
  const [y, setY] = useState(numericCols[0] ?? result.columns[1] ?? result.columns[0]);
  useEffect(() => {
    if (!result.columns.includes(x)) setX(result.columns[0]);
    if (!result.columns.includes(y)) setY(numericCols[0] ?? result.columns[1] ?? result.columns[0]);
  }, [result.columns]);
  const data = useMemo(() => {
    const xs = result.rows.map((r) => r[x]);
    const ys = result.rows.map((r) => r[y]);
    if (chartType === "pie") {
      return [{ type: "pie", labels: xs, values: ys }];
    }
    if (chartType === "line" || chartType === "scatter" || chartType === "area") {
      return [
        {
          type: "scatter",
          mode: chartType === "scatter" ? "markers" : "lines",
          fill: chartType === "area" ? "tozeroy" : "none",
          x: xs,
          y: ys
        }
      ];
    }
    if (chartType === "bar") {
      return [{ type: "bar", x: xs, y: ys }];
    }
    if (chartType === "box") {
      return [{ type: "box", y: ys, name: y }];
    }
    return [{ type: "heatmap", z: [ys] }];
  }, [chartType, x, y, result.rows]);
  return /* @__PURE__ */ jsxDEV(Stack, { children: [
    /* @__PURE__ */ jsxDEV(Group, { children: [
      /* @__PURE__ */ jsxDEV(
        Select,
        {
          label: "차트 종류",
          value: chartType,
          onChange: (v) => v && setChartType(v),
          data: ["line", "bar", "scatter", "pie", "area", "box", "heatmap"],
          w: 140
        },
        void 0,
        false,
        {
          fileName: "/app/src/main.tsx",
          lineNumber: 189,
          columnNumber: 9
        },
        this
      ),
      /* @__PURE__ */ jsxDEV(Select, { label: "X 축", value: x, onChange: (v) => v && setX(v), data: result.columns, w: 180 }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 196,
        columnNumber: 9
      }, this),
      /* @__PURE__ */ jsxDEV(Select, { label: "Y 축", value: y, onChange: (v) => v && setY(v), data: result.columns, w: 180 }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 197,
        columnNumber: 9
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 188,
      columnNumber: 7
    }, this),
    /* @__PURE__ */ jsxDEV(
      Plot,
      {
        data,
        layout: { autosize: true, height: 360, margin: { l: 50, r: 20, t: 30, b: 60 } },
        style: { width: "100%" }
      },
      void 0,
      false,
      {
        fileName: "/app/src/main.tsx",
        lineNumber: 199,
        columnNumber: 7
      },
      this
    )
  ] }, void 0, true, {
    fileName: "/app/src/main.tsx",
    lineNumber: 187,
    columnNumber: 5
  }, this);
}
_s(ChartPicker, "xcwLqGvOxkw2aDondRKhV0DiEr0=");
_c = ChartPicker;
function FileUploadCard() {
  _s2();
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);
  const [error, setError] = useState(null);
  const onFiles = async (files) => {
    if (!files || !files.length) return;
    setError(null);
    setBusy(true);
    const form = new FormData();
    form.append("upload", files[0]);
    try {
      const r = await fetch("/api/files/upload", { method: "POST", body: form });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail ?? `${r.status} ${r.statusText}`);
      }
      const data = await r.json();
      setLast(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return /* @__PURE__ */ jsxDEV(Card, { withBorder: true, padding: "sm", radius: "md", children: [
    /* @__PURE__ */ jsxDEV(Group, { justify: "space-between", align: "center", children: [
      /* @__PURE__ */ jsxDEV("div", { children: [
        /* @__PURE__ */ jsxDEV(Text, { fw: 600, children: "📂 파일 업로드" }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 248,
          columnNumber: 11
        }, this),
        /* @__PURE__ */ jsxDEV(Text, { size: "xs", c: "dimmed", children: [
          "CSV / TSV / JSON / Parquet / Excel / Feather — 최대 1 GiB. 업로드된 파일은 JupyterLab의 ",
          /* @__PURE__ */ jsxDEV(Code, { children: "~/work/uploads/" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 251,
            columnNumber: 25
          }, this),
          " 에서 바로 읽을 수 있어요."
        ] }, void 0, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 249,
          columnNumber: 11
        }, this)
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 247,
        columnNumber: 9
      }, this),
      /* @__PURE__ */ jsxDEV(
        Button,
        {
          component: "label",
          variant: "light",
          loading: busy,
          children: [
            "파일 선택",
            /* @__PURE__ */ jsxDEV(
              "input",
              {
                type: "file",
                style: { display: "none" },
                accept: ".csv,.tsv,.json,.jsonl,.ndjson,.parquet,.xlsx,.feather,.arrow",
                onChange: (e) => onFiles(e.currentTarget.files)
              },
              void 0,
              false,
              {
                fileName: "/app/src/main.tsx",
                lineNumber: 260,
                columnNumber: 11
              },
              this
            )
          ]
        },
        void 0,
        true,
        {
          fileName: "/app/src/main.tsx",
          lineNumber: 254,
          columnNumber: 9
        },
        this
      )
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 246,
      columnNumber: 7
    }, this),
    error && /* @__PURE__ */ jsxDEV(Notification, { color: "red", title: "업로드 실패", mt: "sm", children: error }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 268,
      columnNumber: 17
    }, this),
    last && /* @__PURE__ */ jsxDEV(Stack, { gap: 4, mt: "sm", children: [
      /* @__PURE__ */ jsxDEV(Text, { size: "sm", children: [
        "✓ ",
        /* @__PURE__ */ jsxDEV("strong", { children: last.safe_name }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 272,
          columnNumber: 15
        }, this),
        " (",
        Math.round(last.size_bytes / 1024),
        " KiB)"
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 271,
        columnNumber: 11
      }, this),
      /* @__PURE__ */ jsxDEV(Text, { size: "xs", c: "dimmed", children: [
        "JupyterLab에서: ",
        /* @__PURE__ */ jsxDEV(Code, { children: last.hint }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 274,
          columnNumber: 52
        }, this)
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 274,
        columnNumber: 11
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 270,
      columnNumber: 7
    }, this)
  ] }, void 0, true, {
    fileName: "/app/src/main.tsx",
    lineNumber: 245,
    columnNumber: 5
  }, this);
}
_s2(FileUploadCard, "X7RQw2fXaAvt/D6c6Jz1R9JaPyY=");
_c2 = FileUploadCard;
function QueryEditor() {
  _s3();
  const qc = useQueryClient();
  const conns = useQuery({ queryKey: ["conns"], queryFn: api.connections });
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const nbs = useQuery({ queryKey: ["nbs"], queryFn: api.notebooks });
  const [connId, setConnId] = useState(null);
  const [sql, setSql] = useState("");
  useEffect(() => {
    if (!connId && conns.data?.length) {
      const first = conns.data[0];
      setConnId(first.connection_id);
      setSql(SAMPLE_SQL[first.name] ?? `SELECT * FROM sample LIMIT 10`);
    }
  }, [conns.data]);
  const schema = useQuery({
    queryKey: ["schema", connId],
    queryFn: () => api.schema(connId),
    enabled: !!connId
  });
  const run = useMutation({
    mutationFn: () => api.runQuery({ connection_id: connId, sql })
  });
  const save = useMutation({
    mutationFn: async () => {
      if (!nbs.data?.length || !me.data) throw new Error("no notebook to save to");
      const content = {
        title: "Ad-hoc query result",
        cells: [
          { kind: "sql", connection_id: connId, sql },
          run.data ? { kind: "result", preview_rows: run.data.rows.slice(0, 5) } : null
        ].filter(Boolean),
        saved_at: (/* @__PURE__ */ new Date()).toISOString()
      };
      return api.saveNotebook(nbs.data[0].notebook_id, {
        content,
        saved_by: me.data.user_id,
        commit_message: "analyst SPA save"
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nbs"] })
  });
  if (conns.isLoading) return /* @__PURE__ */ jsxDEV(Loader, {}, void 0, false, {
    fileName: "/app/src/main.tsx",
    lineNumber: 328,
    columnNumber: 31
  }, this);
  return /* @__PURE__ */ jsxDEV(Stack, { p: "md", gap: "md", children: [
    /* @__PURE__ */ jsxDEV(FileUploadCard, {}, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 332,
      columnNumber: 7
    }, this),
    /* @__PURE__ */ jsxDEV(Group, { align: "flex-end", children: [
      /* @__PURE__ */ jsxDEV(
        Select,
        {
          label: "커넥션",
          value: connId,
          onChange: (v) => {
            setConnId(v);
            const c = conns.data?.find((x) => x.connection_id === v);
            if (c) setSql(SAMPLE_SQL[c.name] ?? sql);
          },
          data: (conns.data ?? []).map((c) => ({
            value: c.connection_id,
            label: `${c.name} (${c.engine})`
          })),
          w: 280
        },
        void 0,
        false,
        {
          fileName: "/app/src/main.tsx",
          lineNumber: 334,
          columnNumber: 9
        },
        this
      ),
      schema.data && /* @__PURE__ */ jsxDEV(Group, { gap: "xs", children: schema.data.tables.map((t) => {
        const colNames = t.columns.map((c) => c.name).slice(0, 4).join(", ");
        const qualified = t.schema ? `${t.schema}.${t.name}` : t.name;
        return /* @__PURE__ */ jsxDEV(
          Badge,
          {
            variant: "light",
            style: { cursor: "pointer" },
            onClick: () => setSql(`SELECT ${colNames} FROM ${qualified} LIMIT 25`),
            title: t.columns.map((c) => `${c.name}: ${c.type}${c.pii_kind ? " [PII]" : ""}`).join("\n"),
            children: [
              qualified,
              " (",
              t.columns.length,
              ")"
            ]
          },
          qualified,
          true,
          {
            fileName: "/app/src/main.tsx",
            lineNumber: 354,
            columnNumber: 15
          },
          this
        );
      }) }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 349,
        columnNumber: 9
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 333,
      columnNumber: 7
    }, this),
    /* @__PURE__ */ jsxDEV(
      Textarea,
      {
        label: "SQL",
        autosize: true,
        minRows: 4,
        value: sql,
        onChange: (e) => setSql(e.currentTarget.value),
        styles: { input: { fontFamily: "monospace", fontSize: 13 } }
      },
      void 0,
      false,
      {
        fileName: "/app/src/main.tsx",
        lineNumber: 369,
        columnNumber: 7
      },
      this
    ),
    /* @__PURE__ */ jsxDEV(Group, { children: [
      /* @__PURE__ */ jsxDEV(Button, { loading: run.isPending, onClick: () => run.mutate(), disabled: !connId || !sql, children: "▶ 실행" }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 379,
        columnNumber: 9
      }, this),
      /* @__PURE__ */ jsxDEV(
        Button,
        {
          variant: "light",
          loading: save.isPending,
          onClick: () => save.mutate(),
          disabled: !run.data || !nbs.data?.length,
          children: "💾 노트북에 저장 (Git 자동 커밋)"
        },
        void 0,
        false,
        {
          fileName: "/app/src/main.tsx",
          lineNumber: 382,
          columnNumber: 9
        },
        this
      ),
      save.isSuccess && /* @__PURE__ */ jsxDEV(Badge, { color: "teal", variant: "filled", children: [
        "저장됨 — version ",
        String(save.data.version_id).slice(0, 8),
        "…"
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 391,
        columnNumber: 9
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 378,
      columnNumber: 7
    }, this),
    run.error && /* @__PURE__ */ jsxDEV(Notification, { color: "red", title: "에러", children: run.error.message }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 397,
      columnNumber: 21
    }, this),
    run.data && /* @__PURE__ */ jsxDEV(Card, { padding: "md", radius: "md", withBorder: true, children: /* @__PURE__ */ jsxDEV(Stack, { gap: "sm", children: [
      /* @__PURE__ */ jsxDEV(Group, { justify: "space-between", children: [
        /* @__PURE__ */ jsxDEV(Group, { gap: "xs", children: [
          /* @__PURE__ */ jsxDEV(Badge, { color: "blue", children: run.data.engine }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 404,
            columnNumber: 17
          }, this),
          /* @__PURE__ */ jsxDEV(Text, { size: "sm", c: "dimmed", children: [
            run.data.row_count,
            "건"
          ] }, void 0, true, {
            fileName: "/app/src/main.tsx",
            lineNumber: 405,
            columnNumber: 17
          }, this),
          /* @__PURE__ */ jsxDEV(Text, { size: "xs", c: "dimmed", children: run.data.executed_at }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 406,
            columnNumber: 17
          }, this)
        ] }, void 0, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 403,
          columnNumber: 15
        }, this),
        /* @__PURE__ */ jsxDEV(Group, { gap: 4, children: [
          /* @__PURE__ */ jsxDEV(Text, { size: "xs", c: "dimmed", children: "활성 PII 패턴:" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 409,
            columnNumber: 17
          }, this),
          run.data.active_pii_patterns.map(
            (p) => /* @__PURE__ */ jsxDEV(Badge, { color: "grape", variant: "light", children: p }, p, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 411,
              columnNumber: 15
            }, this)
          )
        ] }, void 0, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 408,
          columnNumber: 15
        }, this)
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 402,
        columnNumber: 13
      }, this),
      /* @__PURE__ */ jsxDEV(Tabs, { defaultValue: "table", children: [
        /* @__PURE__ */ jsxDEV(Tabs.List, { children: [
          /* @__PURE__ */ jsxDEV(Tabs.Tab, { value: "table", children: "표" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 418,
            columnNumber: 17
          }, this),
          /* @__PURE__ */ jsxDEV(Tabs.Tab, { value: "chart", children: "차트" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 419,
            columnNumber: 17
          }, this)
        ] }, void 0, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 417,
          columnNumber: 15
        }, this),
        /* @__PURE__ */ jsxDEV(Tabs.Panel, { value: "table", pt: "sm", children: /* @__PURE__ */ jsxDEV(ScrollArea, { h: 360, children: /* @__PURE__ */ jsxDEV(Table, { striped: true, withTableBorder: true, withColumnBorders: true, fz: "sm", children: [
          /* @__PURE__ */ jsxDEV(Table.Thead, { children: /* @__PURE__ */ jsxDEV(Table.Tr, { children: run.data.columns.map(
            (c) => /* @__PURE__ */ jsxDEV(Table.Th, { children: c }, c, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 428,
              columnNumber: 23
            }, this)
          ) }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 426,
            columnNumber: 23
          }, this) }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 425,
            columnNumber: 21
          }, this),
          /* @__PURE__ */ jsxDEV(Table.Tbody, { children: run.data.rows.map(
            (row, i) => /* @__PURE__ */ jsxDEV(Table.Tr, { children: run.data.columns.map(
              (c) => /* @__PURE__ */ jsxDEV(Table.Td, { children: /* @__PURE__ */ jsxDEV(Code, { children: String(row[c] ?? "") }, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 436,
                columnNumber: 41
              }, this) }, c, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 436,
                columnNumber: 23
              }, this)
            ) }, i, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 434,
              columnNumber: 21
            }, this)
          ) }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 432,
            columnNumber: 21
          }, this)
        ] }, void 0, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 424,
          columnNumber: 19
        }, this) }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 423,
          columnNumber: 17
        }, this) }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 422,
          columnNumber: 15
        }, this),
        /* @__PURE__ */ jsxDEV(Tabs.Panel, { value: "chart", pt: "sm", children: /* @__PURE__ */ jsxDEV(ChartPicker, { result: run.data }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 446,
          columnNumber: 17
        }, this) }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 445,
          columnNumber: 15
        }, this)
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 416,
        columnNumber: 13
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 401,
      columnNumber: 11
    }, this) }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 400,
      columnNumber: 7
    }, this)
  ] }, void 0, true, {
    fileName: "/app/src/main.tsx",
    lineNumber: 331,
    columnNumber: 5
  }, this);
}
_s3(QueryEditor, "37N/VtXWIUqn8s2apmWTPwsZaJ8=", false, function() {
  return [useQueryClient, useQuery, useQuery, useQuery, useQuery, useMutation, useMutation];
});
_c3 = QueryEditor;
function NotebookList() {
  _s4();
  const nbs = useQuery({ queryKey: ["nbs"], queryFn: api.notebooks });
  return /* @__PURE__ */ jsxDEV(Stack, { p: "md", gap: "md", children: [
    /* @__PURE__ */ jsxDEV(Title, { order: 3, children: "내 노트북" }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 460,
      columnNumber: 7
    }, this),
    nbs.isLoading && /* @__PURE__ */ jsxDEV(Loader, {}, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 461,
      columnNumber: 25
    }, this),
    nbs.data && /* @__PURE__ */ jsxDEV(Table, { striped: true, withTableBorder: true, withColumnBorders: true, children: [
      /* @__PURE__ */ jsxDEV(Table.Thead, { children: /* @__PURE__ */ jsxDEV(Table.Tr, { children: [
        /* @__PURE__ */ jsxDEV(Table.Th, { children: "경로" }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 466,
          columnNumber: 15
        }, this),
        /* @__PURE__ */ jsxDEV(Table.Th, { children: "최근 저장" }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 467,
          columnNumber: 15
        }, this),
        /* @__PURE__ */ jsxDEV(Table.Th, { children: "버전" }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 468,
          columnNumber: 15
        }, this),
        /* @__PURE__ */ jsxDEV(Table.Th, { children: "액션" }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 469,
          columnNumber: 15
        }, this)
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 465,
        columnNumber: 13
      }, this) }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 464,
        columnNumber: 11
      }, this),
      /* @__PURE__ */ jsxDEV(Table.Tbody, { children: nbs.data.map(
        (nb) => /* @__PURE__ */ jsxDEV(Table.Tr, { children: [
          /* @__PURE__ */ jsxDEV(Table.Td, { children: nb.path }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 475,
            columnNumber: 17
          }, this),
          /* @__PURE__ */ jsxDEV(Table.Td, { children: nb.latest_saved_at ? new Date(nb.latest_saved_at).toLocaleString() : "—" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 476,
            columnNumber: 17
          }, this),
          /* @__PURE__ */ jsxDEV(Table.Td, { children: nb.latest_version?.slice(0, 8) ?? "—" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 477,
            columnNumber: 17
          }, this),
          /* @__PURE__ */ jsxDEV(Table.Td, { children: /* @__PURE__ */ jsxDEV(Button, { size: "xs", component: Link, to: `/notebooks/${nb.notebook_id}`, children: "열기" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 479,
            columnNumber: 19
          }, this) }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 478,
            columnNumber: 17
          }, this)
        ] }, nb.notebook_id, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 474,
          columnNumber: 11
        }, this)
      ) }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 472,
        columnNumber: 11
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 463,
      columnNumber: 7
    }, this)
  ] }, void 0, true, {
    fileName: "/app/src/main.tsx",
    lineNumber: 459,
    columnNumber: 5
  }, this);
}
_s4(NotebookList, "rZNf2tB+DCHLeoOaqFYEbPTs+SM=", false, function() {
  return [useQuery];
});
_c4 = NotebookList;
function NotebookDetail() {
  _s5();
  const { id } = useParams();
  const nb = useQuery({
    queryKey: ["nb", id],
    queryFn: () => api.latestNotebook(id),
    enabled: !!id
  });
  return /* @__PURE__ */ jsxDEV(Stack, { p: "md", gap: "md", children: [
    /* @__PURE__ */ jsxDEV(Group, { children: /* @__PURE__ */ jsxDEV(Button, { component: Link, to: "/notebooks", variant: "subtle", children: "← 목록" }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 500,
      columnNumber: 9
    }, this) }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 499,
      columnNumber: 7
    }, this),
    nb.isLoading && /* @__PURE__ */ jsxDEV(Loader, {}, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 502,
      columnNumber: 24
    }, this),
    nb.data && /* @__PURE__ */ jsxDEV(Card, { withBorder: true, children: [
      /* @__PURE__ */ jsxDEV(Title, { order: 3, children: nb.data.path }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 505,
        columnNumber: 11
      }, this),
      /* @__PURE__ */ jsxDEV(Text, { size: "sm", c: "dimmed", children: [
        "최근 저장: ",
        nb.data.saved_at ?? "—"
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 506,
        columnNumber: 11
      }, this),
      /* @__PURE__ */ jsxDEV(Code, { block: true, style: { marginTop: 8 }, children: JSON.stringify(nb.data.content, null, 2) }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 507,
        columnNumber: 11
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 504,
      columnNumber: 7
    }, this)
  ] }, void 0, true, {
    fileName: "/app/src/main.tsx",
    lineNumber: 498,
    columnNumber: 5
  }, this);
}
_s5(NotebookDetail, "4W6n0YEcWoSqleEW5GPhzYHrnKA=", false, function() {
  return [useParams, useQuery];
});
_c5 = NotebookDetail;
function JupyterLab({ reloadToken }) {
  _s6();
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
  }, [reloadToken]);
  const src = `/jupyter/lab/tree/copilot.ipynb?token=dataplatform&reset&t=${reloadToken}`;
  return /* @__PURE__ */ jsxDEV(
    "iframe",
    {
      src,
      title: "JupyterLab",
      onLoad: () => setLoading(false),
      style: {
        width: "100%",
        height: "100%",
        border: "none",
        display: "block",
        transition: "opacity 250ms ease-in",
        opacity: loading ? 0.45 : 1
      },
      allow: "clipboard-read; clipboard-write"
    },
    reloadToken,
    false,
    {
      fileName: "/app/src/main.tsx",
      lineNumber: 533,
      columnNumber: 5
    },
    this
  );
}
_s6(JupyterLab, "J7PPXooW06IQ11rfabbvgk72KFw=");
_c6 = JupyterLab;
const COPILOT_NOTEBOOK = "copilot.ipynb";
const JUPYTER_TOKEN = "dataplatform";
async function appendCellToCopilotNotebook(language, source) {
  const url = `/jupyter/api/contents/${COPILOT_NOTEBOOK}`;
  const headers = {
    "Content-Type": "application/json",
    Authorization: `token ${JUPYTER_TOKEN}`
  };
  let notebook = null;
  const head = await fetch(url, { headers, credentials: "omit" });
  if (head.ok) {
    notebook = await head.json();
  }
  if (!notebook) {
    notebook = {
      type: "notebook",
      content: {
        cells: [],
        metadata: { kernelspec: { name: "python3", display_name: "Python 3" } },
        nbformat: 4,
        nbformat_minor: 5
      },
      format: "json",
      name: COPILOT_NOTEBOOK,
      path: COPILOT_NOTEBOOK
    };
  }
  const cell = {
    cell_type: "code",
    metadata: { copilot_generated: true, language },
    source: language === "sql" ? `%%sql
${source}` : source,
    outputs: [],
    execution_count: null
  };
  notebook.content.cells.push(cell);
  notebook.type = "notebook";
  notebook.format = "json";
  notebook.name = COPILOT_NOTEBOOK;
  notebook.path = COPILOT_NOTEBOOK;
  const put = await fetch(url, {
    method: "PUT",
    headers,
    credentials: "omit",
    body: JSON.stringify({
      type: "notebook",
      format: "json",
      content: notebook.content
    })
  });
  if (!put.ok) {
    throw new Error(`Jupyter PUT failed: ${put.status}`);
  }
}
function splitMarkdownCodeBlocks(text) {
  const blocks = [];
  const re = /```(sql|python)\n([\s\S]*?)```/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    blocks.push({ language: m[1].toLowerCase(), source: m[2].trim() });
  }
  return [{ text, blocks }];
}
function stripCodeFences(text) {
  return text.replace(/```(sql|python)\n[\s\S]*?```/gi, "").replace(/\n{3,}/g, "\n\n").trim();
}
async function fetchNotebookContext() {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), 4e3);
  try {
    const r = await fetch(`/jupyter/api/contents/${COPILOT_NOTEBOOK}`, {
      headers: { Authorization: `token ${JUPYTER_TOKEN}` },
      signal: ctrl.signal
    });
    if (!r.ok) return { prompt: "", cellCount: 0 };
    const nb = await r.json();
    const cells = nb?.content?.cells ?? [];
    const codeCells = cells.filter((c) => c.cell_type === "code").map((c) => Array.isArray(c.source) ? c.source.join("") : c.source ?? "").map((s) => s.trim()).filter((s) => s.length > 0);
    if (codeCells.length === 0) return { prompt: "", cellCount: 0 };
    const body = codeCells.map((s, i) => `--- Cell #${i + 1} ---
${s}`).join("\n\n");
    const prompt = `현재 ${COPILOT_NOTEBOOK} 에 들어있는 코드 셀입니다. 사용자의 새 요청이 "이 코드 수정/리팩토링/이어서" 같은 의도면 이 셀들을 기준으로 답하세요. 새 셀이 필요하면 새 코드 블록을 추가하세요.

` + body;
    return { prompt, cellCount: codeCells.length };
  } catch {
    return { prompt: "", cellCount: 0 };
  } finally {
    window.clearTimeout(timer);
  }
}
function CopilotPanel({
  connectionId,
  onCellInserted
}) {
  _s7();
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [providerName, setProviderName] = useState("");
  const [lastInsert, setLastInsert] = useState(null);
  const insertedRef = useRef(/* @__PURE__ */ new Set());
  const chatRef = useRef(null);
  const [autoFollow, setAutoFollow] = useState(true);
  useEffect(() => {
    fetch("/api/copilot/provider").then((r) => r.ok ? r.json() : null).then((j) => j && setProviderName(j.provider)).catch(() => {
    });
  }, []);
  useEffect(() => {
    if (!autoFollow) return;
    const el = chatRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [history, pending, autoFollow]);
  const onChatScroll = () => {
    const el = chatRef.current;
    if (!el) return;
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
    setInput("");
    setBusy(true);
    setAutoFollow(true);
    setHistory((h) => [...h, { role: "user", content: question }]);
    setPending("");
    try {
      const { prompt: nbPrompt } = await fetchNotebookContext();
      const augmentedQuestion = nbPrompt ? `${nbPrompt}

---

사용자 요청:
${question}` : question;
      const res = await fetch("/api/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: augmentedQuestion,
          history,
          connection_id: connectionId
        })
      });
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      let assembled = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let nl;
        while ((nl = buf.indexOf("\n")) >= 0) {
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
            if (e.message !== "JSON.parse") throw e;
          }
        }
      }
      let assistantIdx = -1;
      setHistory((h) => {
        assistantIdx = h.length;
        return [...h, { role: "assistant", content: assembled }];
      });
      setPending("");
      const blocks = splitMarkdownCodeBlocks(assembled)[0].blocks;
      for (let k = 0; k < blocks.length; k++) {
        const key = `${assistantIdx}:${k}`;
        if (insertedRef.current.has(key)) continue;
        insertedRef.current.add(key);
        try {
          await onInsert(blocks[k]);
        } catch {
        }
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const onInsert = async (block) => {
    setError(null);
    try {
      await appendCellToCopilotNotebook(block.language, block.source);
      try {
        await fetch("/api/copilot/cell-inserted", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            notebook_path: COPILOT_NOTEBOOK,
            language: block.language,
            source_length: block.source.length,
            connection_id: connectionId
          })
        });
      } catch {
      }
      setLastInsert(`${block.language.toUpperCase()} 셀이 copilot.ipynb 에 추가됨`);
      window.setTimeout(() => setLastInsert(null), 4e3);
      onCellInserted?.();
    } catch (e) {
      setError(`셀 삽입 실패: ${e.message}`);
    }
  };
  return (
    // The CopilotPanel lives inside AppShell.Main, which Mantine sizes via
    // a layered layout that breaks naïve height:100% chains. Pin the panel
    // itself to a viewport-relative height so the chat list always gets a
    // bounded box to scroll inside.
    //   88 px ≈ SPA header (44) + panel-header (~44) above us.
    /* @__PURE__ */ jsxDEV(
      Stack,
      {
        p: "sm",
        gap: "sm",
        style: { height: "calc(100vh - 88px)", overflow: "hidden" },
        children: [
          /* @__PURE__ */ jsxDEV(Group, { justify: "space-between", children: [
            /* @__PURE__ */ jsxDEV(Title, { order: 5, children: "🤖 분석 코파일럿" }, void 0, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 865,
              columnNumber: 9
            }, this),
            providerName && /* @__PURE__ */ jsxDEV(Badge, { variant: "light", children: providerName }, void 0, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 866,
              columnNumber: 26
            }, this)
          ] }, void 0, true, {
            fileName: "/app/src/main.tsx",
            lineNumber: 864,
            columnNumber: 7
          }, this),
          /* @__PURE__ */ jsxDEV(
            "div",
            {
              ref: chatRef,
              onScroll: onChatScroll,
              "data-testid": "copilot-chat",
              style: {
                flex: 1,
                minHeight: 0,
                overflowY: "auto",
                paddingRight: 4,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                position: "relative"
              },
              children: [
                history.length === 0 && !pending && /* @__PURE__ */ jsxDEV(Text, { size: "sm", c: "dimmed", children: [
                  '예: "지난 30일 매출 상위 도시 5개 알려줘" — 커넥션을 고르면 스키마 컨텍스트를 자동 주입합니다. 응답에 SQL/Python 코드가 포함되면 자동으로 ',
                  COPILOT_NOTEBOOK,
                  " 에 셀을 추가합니다."
                ] }, void 0, true, {
                  fileName: "/app/src/main.tsx",
                  lineNumber: 885,
                  columnNumber: 9
                }, this),
                history.map((m, i) => {
                  const blocks = m.role === "assistant" ? splitMarkdownCodeBlocks(m.content)[0].blocks : [];
                  const narration = m.role === "assistant" && blocks.length > 0 ? stripCodeFences(m.content) : m.content;
                  return /* @__PURE__ */ jsxDEV(Card, { withBorder: true, padding: "sm", radius: "sm", children: [
                    /* @__PURE__ */ jsxDEV(Group, { gap: "xs", mb: 4, children: /* @__PURE__ */ jsxDEV(Badge, { size: "xs", color: m.role === "user" ? "blue" : "grape", children: m.role === "user" ? "나" : "코파일럿" }, void 0, false, {
                      fileName: "/app/src/main.tsx",
                      lineNumber: 901,
                      columnNumber: 17
                    }, this) }, void 0, false, {
                      fileName: "/app/src/main.tsx",
                      lineNumber: 900,
                      columnNumber: 15
                    }, this),
                    narration && /* @__PURE__ */ jsxDEV(Text, { size: "sm", style: { whiteSpace: "pre-wrap" }, children: narration }, void 0, false, {
                      fileName: "/app/src/main.tsx",
                      lineNumber: 909,
                      columnNumber: 15
                    }, this),
                    m.role === "assistant" && blocks.length > 0 && /* @__PURE__ */ jsxDEV(Group, { mt: 6, gap: "xs", children: [
                      /* @__PURE__ */ jsxDEV(Badge, { variant: "outline", color: "green", size: "sm", children: [
                        "✅ ",
                        blocks.length,
                        "개 셀이 ",
                        COPILOT_NOTEBOOK,
                        " 에 자동 추가됨"
                      ] }, void 0, true, {
                        fileName: "/app/src/main.tsx",
                        lineNumber: 915,
                        columnNumber: 19
                      }, this),
                      blocks.map(
                        (b, k) => /* @__PURE__ */ jsxDEV(
                          Badge,
                          {
                            variant: "light",
                            color: b.language === "sql" ? "teal" : "orange",
                            size: "sm",
                            children: [
                              b.language.toUpperCase(),
                              " #",
                              k + 1
                            ]
                          },
                          k,
                          true,
                          {
                            fileName: "/app/src/main.tsx",
                            lineNumber: 919,
                            columnNumber: 17
                          },
                          this
                        )
                      ),
                      /* @__PURE__ */ jsxDEV(
                        Button,
                        {
                          size: "xs",
                          variant: "subtle",
                          onClick: () => blocks.forEach((b) => onInsert(b)),
                          children: "🔁 다시 삽입"
                        },
                        void 0,
                        false,
                        {
                          fileName: "/app/src/main.tsx",
                          lineNumber: 928,
                          columnNumber: 19
                        },
                        this
                      )
                    ] }, void 0, true, {
                      fileName: "/app/src/main.tsx",
                      lineNumber: 914,
                      columnNumber: 15
                    }, this)
                  ] }, i, true, {
                    fileName: "/app/src/main.tsx",
                    lineNumber: 899,
                    columnNumber: 13
                  }, this);
                }),
                pending && /* @__PURE__ */ jsxDEV(Card, { withBorder: true, padding: "sm", radius: "sm", bg: "gray.0", children: [
                  /* @__PURE__ */ jsxDEV(Group, { gap: "xs", mb: 4, children: [
                    /* @__PURE__ */ jsxDEV(Loader, { size: "xs" }, void 0, false, {
                      fileName: "/app/src/main.tsx",
                      lineNumber: 944,
                      columnNumber: 15
                    }, this),
                    /* @__PURE__ */ jsxDEV(Badge, { size: "xs", color: "grape", children: "코파일럿" }, void 0, false, {
                      fileName: "/app/src/main.tsx",
                      lineNumber: 945,
                      columnNumber: 15
                    }, this)
                  ] }, void 0, true, {
                    fileName: "/app/src/main.tsx",
                    lineNumber: 943,
                    columnNumber: 13
                  }, this),
                  /* @__PURE__ */ jsxDEV(Text, { size: "sm", style: { whiteSpace: "pre-wrap" }, children: pending }, void 0, false, {
                    fileName: "/app/src/main.tsx",
                    lineNumber: 947,
                    columnNumber: 13
                  }, this)
                ] }, void 0, true, {
                  fileName: "/app/src/main.tsx",
                  lineNumber: 942,
                  columnNumber: 9
                }, this)
              ]
            },
            void 0,
            true,
            {
              fileName: "/app/src/main.tsx",
              lineNumber: 869,
              columnNumber: 7
            },
            this
          ),
          !autoFollow && /* @__PURE__ */ jsxDEV(Group, { justify: "center", children: /* @__PURE__ */ jsxDEV(Button, { size: "xs", variant: "light", onClick: scrollToLatest, children: "▼ 최신 메시지로" }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 954,
            columnNumber: 11
          }, this) }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 953,
            columnNumber: 7
          }, this),
          error && /* @__PURE__ */ jsxDEV(Notification, { color: "red", title: "실패", onClose: () => setError(null), children: error }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 959,
            columnNumber: 17
          }, this),
          lastInsert && /* @__PURE__ */ jsxDEV(Notification, { color: "green", title: "삽입 완료", onClose: () => setLastInsert(null), children: lastInsert }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 960,
            columnNumber: 22
          }, this),
          /* @__PURE__ */ jsxDEV(Group, { gap: 6, children: [
            /* @__PURE__ */ jsxDEV(
              Textarea,
              {
                placeholder: "자연어로 질문하세요…",
                value: input,
                onChange: (e) => setInput(e.currentTarget.value),
                onKeyDown: (e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
                },
                autosize: true,
                minRows: 2,
                maxRows: 6,
                style: { flex: 1 }
              },
              void 0,
              false,
              {
                fileName: "/app/src/main.tsx",
                lineNumber: 963,
                columnNumber: 9
              },
              this
            ),
            /* @__PURE__ */ jsxDEV(Button, { onClick: send, loading: busy, disabled: !input.trim(), children: "▶ 보내기" }, void 0, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 975,
              columnNumber: 9
            }, this)
          ] }, void 0, true, {
            fileName: "/app/src/main.tsx",
            lineNumber: 962,
            columnNumber: 7
          }, this),
          /* @__PURE__ */ jsxDEV(Text, { size: "xs", c: "dimmed", children: "⌘/Ctrl + Enter 로 전송 — 응답은 스트리밍됩니다." }, void 0, false, {
            fileName: "/app/src/main.tsx",
            lineNumber: 979,
            columnNumber: 7
          }, this)
        ]
      },
      void 0,
      true,
      {
        fileName: "/app/src/main.tsx",
        lineNumber: 859,
        columnNumber: 5
      },
      this
    )
  );
}
_s7(CopilotPanel, "I7njS2+0wqCA9N5UDZ4z/GMGLQw=");
_c7 = CopilotPanel;
function JupyterWithCopilot() {
  _s8();
  const conns = useQuery({ queryKey: ["conns"], queryFn: api.connections });
  const defaultConn = conns.data?.find((c) => c.engine !== "hive")?.connection_id ?? null;
  const [connId, setConnId] = useState(null);
  const activeConn = connId ?? defaultConn;
  const [labReloadToken, setLabReloadToken] = useState(0);
  return /* @__PURE__ */ jsxDEV("div", { style: { display: "flex", height: "100%", width: "100%" }, children: [
    /* @__PURE__ */ jsxDEV("div", { style: { flex: "1 1 65%", minWidth: 320, height: "100%" }, children: /* @__PURE__ */ jsxDEV(JupyterLab, { reloadToken: labReloadToken }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 995,
      columnNumber: 9
    }, this) }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 994,
      columnNumber: 7
    }, this),
    /* @__PURE__ */ jsxDEV("div", { style: { flex: "0 0 35%", minWidth: 320, maxWidth: 600, height: "100%", borderLeft: "1px solid #e9ecef", background: "#fafafa" }, children: /* @__PURE__ */ jsxDEV(Stack, { p: 0, gap: 0, style: { height: "100%" }, children: [
      /* @__PURE__ */ jsxDEV(Group, { p: "xs", gap: "xs", align: "center", style: { borderBottom: "1px solid #e9ecef" }, children: [
        /* @__PURE__ */ jsxDEV(Text, { size: "xs", c: "dimmed", children: "커넥션 컨텍스트" }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 1e3,
          columnNumber: 13
        }, this),
        /* @__PURE__ */ jsxDEV(
          Select,
          {
            size: "xs",
            value: activeConn,
            data: (conns.data ?? []).map((c) => ({ value: c.connection_id, label: c.name })),
            onChange: setConnId,
            placeholder: "선택",
            style: { flex: 1 }
          },
          void 0,
          false,
          {
            fileName: "/app/src/main.tsx",
            lineNumber: 1001,
            columnNumber: 13
          },
          this
        )
      ] }, void 0, true, {
        fileName: "/app/src/main.tsx",
        lineNumber: 999,
        columnNumber: 11
      }, this),
      /* @__PURE__ */ jsxDEV("div", { style: { flex: 1, minHeight: 0 }, children: /* @__PURE__ */ jsxDEV(
        CopilotPanel,
        {
          connectionId: activeConn,
          onCellInserted: () => setLabReloadToken((n) => n + 1)
        },
        void 0,
        false,
        {
          fileName: "/app/src/main.tsx",
          lineNumber: 1011,
          columnNumber: 13
        },
        this
      ) }, void 0, false, {
        fileName: "/app/src/main.tsx",
        lineNumber: 1010,
        columnNumber: 11
      }, this)
    ] }, void 0, true, {
      fileName: "/app/src/main.tsx",
      lineNumber: 998,
      columnNumber: 9
    }, this) }, void 0, false, {
      fileName: "/app/src/main.tsx",
      lineNumber: 997,
      columnNumber: 7
    }, this)
  ] }, void 0, true, {
    fileName: "/app/src/main.tsx",
    lineNumber: 993,
    columnNumber: 5
  }, this);
}
_s8(JupyterWithCopilot, "O8Qq8VWhhxI0YEN7bWXXZHdrKCw=", false, function() {
  return [useQuery];
});
_c8 = JupyterWithCopilot;
function Shell() {
  _s9();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  const loc = useLocation();
  const isJupyter = loc.pathname === "/" || loc.pathname === "";
  const [navOpen, setNavOpen] = useState(false);
  const navCollapsed = isJupyter && !navOpen;
  return /* @__PURE__ */ jsxDEV(
    AppShell,
    {
      header: { height: 44 },
      navbar: {
        width: 220,
        breakpoint: "sm",
        collapsed: { desktop: navCollapsed, mobile: navCollapsed }
      },
      padding: 0,
      children: [
        /* @__PURE__ */ jsxDEV(AppShell.Header, { children: /* @__PURE__ */ jsxDEV(Group, { h: "100%", px: "sm", justify: "space-between", children: [
          /* @__PURE__ */ jsxDEV(Group, { gap: "xs", children: [
            /* @__PURE__ */ jsxDEV(
              Burger,
              {
                opened: !navCollapsed,
                onClick: () => setNavOpen((o) => !o),
                size: "sm",
                "aria-label": "사이드바 토글"
              },
              void 0,
              false,
              {
                fileName: "/app/src/main.tsx",
                lineNumber: 1044,
                columnNumber: 13
              },
              this
            ),
            /* @__PURE__ */ jsxDEV(Title, { order: 5, children: "🧪 Analyst Workspace" }, void 0, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 1050,
              columnNumber: 13
            }, this)
          ] }, void 0, true, {
            fileName: "/app/src/main.tsx",
            lineNumber: 1043,
            columnNumber: 11
          }, this),
          me.data && /* @__PURE__ */ jsxDEV(Group, { gap: "xs", children: [
            /* @__PURE__ */ jsxDEV(Text, { size: "sm", c: "dimmed", children: me.data.display_name ?? me.data.email }, void 0, false, {
              fileName: "/app/src/main.tsx",
              lineNumber: 1054,
              columnNumber: 15
            }, this),
            me.data.roles.map(
              (r) => /* @__PURE__ */ jsxDEV(Badge, { variant: "light", children: r }, r, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1056,
                columnNumber: 13
              }, this)
            )
          ] }, void 0, true, {
            fileName: "/app/src/main.tsx",
            lineNumber: 1053,
            columnNumber: 11
          }, this)
        ] }, void 0, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 1042,
          columnNumber: 9
        }, this) }, void 0, false, {
          fileName: "/app/src/main.tsx",
          lineNumber: 1041,
          columnNumber: 7
        }, this),
        /* @__PURE__ */ jsxDEV(AppShell.Navbar, { p: "sm", children: [
          /* @__PURE__ */ jsxDEV(
            NavLink,
            {
              component: Link,
              to: "/",
              label: "📓  JupyterLab",
              onClick: () => setNavOpen(false)
            },
            void 0,
            false,
            {
              fileName: "/app/src/main.tsx",
              lineNumber: 1063,
              columnNumber: 9
            },
            this
          ),
          /* @__PURE__ */ jsxDEV(
            NavLink,
            {
              component: Link,
              to: "/sql",
              label: "📝  빠른 SQL",
              onClick: () => setNavOpen(true)
            },
            void 0,
            false,
            {
              fileName: "/app/src/main.tsx",
              lineNumber: 1069,
              columnNumber: 9
            },
            this
          ),
          /* @__PURE__ */ jsxDEV(
            NavLink,
            {
              component: Link,
              to: "/notebooks",
              label: "📚  내 노트북",
              onClick: () => setNavOpen(true)
            },
            void 0,
            false,
            {
              fileName: "/app/src/main.tsx",
              lineNumber: 1075,
              columnNumber: 9
            },
            this
          )
        ] }, void 0, true, {
          fileName: "/app/src/main.tsx",
          lineNumber: 1062,
          columnNumber: 7
        }, this),
        /* @__PURE__ */ jsxDEV(
          AppShell.Main,
          {
            style: {
              // 44px clears the fixed header; the JupyterLab embed wants the full
              // viewport (it has its own left rail) so we strip the SPA's navbar
              // gutter there. Every other route needs to push past the 220-px
              // navbar so the action buttons aren't hidden behind it.
              padding: isJupyter ? "44px 0 0 0" : "44px 0 0 220px",
              height: "100vh",
              boxSizing: "border-box",
              overflow: isJupyter ? "hidden" : "auto"
            },
            children: /* @__PURE__ */ jsxDEV(Routes, { children: [
              /* @__PURE__ */ jsxDEV(Route, { path: "/", element: /* @__PURE__ */ jsxDEV(JupyterWithCopilot, {}, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1095,
                columnNumber: 36
              }, this) }, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1095,
                columnNumber: 11
              }, this),
              /* @__PURE__ */ jsxDEV(Route, { path: "/sql", element: /* @__PURE__ */ jsxDEV(QueryEditor, {}, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1096,
                columnNumber: 39
              }, this) }, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1096,
                columnNumber: 11
              }, this),
              /* @__PURE__ */ jsxDEV(Route, { path: "/notebooks", element: /* @__PURE__ */ jsxDEV(NotebookList, {}, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1097,
                columnNumber: 45
              }, this) }, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1097,
                columnNumber: 11
              }, this),
              /* @__PURE__ */ jsxDEV(Route, { path: "/notebooks/:id", element: /* @__PURE__ */ jsxDEV(NotebookDetail, {}, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1098,
                columnNumber: 49
              }, this) }, void 0, false, {
                fileName: "/app/src/main.tsx",
                lineNumber: 1098,
                columnNumber: 11
              }, this)
            ] }, void 0, true, {
              fileName: "/app/src/main.tsx",
              lineNumber: 1094,
              columnNumber: 9
            }, this)
          },
          void 0,
          false,
          {
            fileName: "/app/src/main.tsx",
            lineNumber: 1082,
            columnNumber: 7
          },
          this
        )
      ]
    },
    void 0,
    true,
    {
      fileName: "/app/src/main.tsx",
      lineNumber: 1032,
      columnNumber: 5
    },
    this
  );
}
_s9(Shell, "b1YrnmlQl2t3s3dOpTW5aq04x2U=", false, function() {
  return [useQuery, useLocation];
});
_c9 = Shell;
ReactDOM.createRoot(document.getElementById("root")).render(
  /* @__PURE__ */ jsxDEV(MantineProvider, { children: /* @__PURE__ */ jsxDEV(QueryClientProvider, { client: queryClient, children: /* @__PURE__ */ jsxDEV(BrowserRouter, { basename: "/analyst", children: /* @__PURE__ */ jsxDEV(Shell, {}, void 0, false, {
    fileName: "/app/src/main.tsx",
    lineNumber: 1109,
    columnNumber: 9
  }, this) }, void 0, false, {
    fileName: "/app/src/main.tsx",
    lineNumber: 1108,
    columnNumber: 7
  }, this) }, void 0, false, {
    fileName: "/app/src/main.tsx",
    lineNumber: 1107,
    columnNumber: 5
  }, this) }, void 0, false, {
    fileName: "/app/src/main.tsx",
    lineNumber: 1106,
    columnNumber: 3
  }, this)
);
var _c, _c2, _c3, _c4, _c5, _c6, _c7, _c8, _c9;
$RefreshReg$(_c, "ChartPicker");
$RefreshReg$(_c2, "FileUploadCard");
$RefreshReg$(_c3, "QueryEditor");
$RefreshReg$(_c4, "NotebookList");
$RefreshReg$(_c5, "NotebookDetail");
$RefreshReg$(_c6, "JupyterLab");
$RefreshReg$(_c7, "CopilotPanel");
$RefreshReg$(_c8, "JupyterWithCopilot");
$RefreshReg$(_c9, "Shell");
if (import.meta.hot && !inWebWorker) {
  window.$RefreshReg$ = prevRefreshReg;
  window.$RefreshSig$ = prevRefreshSig;
}
if (import.meta.hot && !inWebWorker) {
  RefreshRuntime.__hmr_import(import.meta.url).then((currentExports) => {
    RefreshRuntime.registerExportsForReactRefresh("/app/src/main.tsx", currentExports);
    import.meta.hot.accept((nextExports) => {
      if (!nextExports) return;
      const invalidateMessage = RefreshRuntime.validateRefreshBoundaryAndEnqueueUpdate("/app/src/main.tsx", currentExports, nextExports);
      if (invalidateMessage) import.meta.hot.invalidate(invalidateMessage);
    });
  });
}

//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJtYXBwaW5ncyI6IkFBeUtROzs7Ozs7Ozs7Ozs7Ozs7OztBQXpLUixTQUFTQSxXQUFXQyxTQUFTQyxRQUFRQyxnQkFBZ0I7QUFDckQsT0FBT0MsY0FBYztBQUNyQjtBQUFBLEVBQ0VDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBQ0FDO0FBQUFBLEVBRUFDO0FBQUFBLEVBQ0FDO0FBQUFBLE9BQ0s7QUFDUCxTQUFTQyxhQUFhQyxxQkFBcUJDLGFBQWFDLFVBQVVDLHNCQUFzQjtBQUN4RixPQUFPQyxVQUFVO0FBQ2pCO0FBQUEsRUFDRUM7QUFBQUEsRUFDQUM7QUFBQUEsRUFDQUM7QUFBQUEsRUFDQUM7QUFBQUEsRUFDQUM7QUFBQUEsRUFFQUM7QUFBQUEsT0FDSztBQUNQLE9BQU87QUFFUCxNQUFNQyxjQUFjLElBQUlaLFlBQVk7QUFBQSxFQUNsQ2EsZ0JBQWdCLEVBQUVDLFNBQVMsRUFBRUMsc0JBQXNCLE1BQU0sRUFBRTtBQUM3RCxDQUFDO0FBcURELE1BQU1DLE1BQU07QUFBQSxFQUNWQyxJQUFJQSxNQUFNQyxNQUFNLGNBQWMsRUFBRUMsS0FBSyxDQUFDQyxNQUFNQSxFQUFFQyxLQUFLLENBQWdCO0FBQUEsRUFDbkVDLGFBQWFBLE1BQU1KLE1BQU0sa0JBQWtCLEVBQUVDLEtBQUssQ0FBQ0MsTUFBTUEsRUFBRUMsS0FBSyxDQUEwQjtBQUFBLEVBQzFGRSxRQUFRQSxDQUFDQyxPQUNQTixNQUFNLG9CQUFvQk0sRUFBRSxTQUFTLEVBQUVMLEtBQUssQ0FBQ0MsTUFBTUEsRUFBRUMsS0FBSyxDQUFvQjtBQUFBLEVBQ2hGSSxVQUFVQSxDQUFDQyxTQUNUUixNQUFNLHdCQUF3QjtBQUFBLElBQzVCUyxRQUFRO0FBQUEsSUFDUkMsU0FBUyxFQUFFLGdCQUFnQixtQkFBbUI7QUFBQSxJQUM5Q0YsTUFBTUcsS0FBS0MsVUFBVSxFQUFFLEdBQUdKLE1BQU1LLFFBQVEsQ0FBQyxFQUFFLENBQUM7QUFBQSxFQUM5QyxDQUFDLEVBQUVaLEtBQUssT0FBT0MsTUFBTTtBQUNuQixRQUFJLENBQUNBLEVBQUVZLEdBQUksT0FBTSxJQUFJQyxNQUFNLEdBQUdiLEVBQUVjLE1BQU0sSUFBSWQsRUFBRWUsVUFBVSxFQUFFO0FBQ3hELFdBQU9mLEVBQUVDLEtBQUs7QUFBQSxFQUNoQixDQUFDO0FBQUEsRUFDSGUsWUFBWUEsTUFBTWxCLE1BQU0saUJBQWlCLEVBQUVDLEtBQUssQ0FBQ0MsTUFBTUEsRUFBRUMsS0FBSyxDQUF5QjtBQUFBLEVBQ3ZGZ0IsV0FBV0EsTUFBTW5CLE1BQU0sZ0JBQWdCLEVBQUVDLEtBQUssQ0FBQ0MsTUFBTUEsRUFBRUMsS0FBSyxDQUF3QjtBQUFBLEVBQ3BGaUIsZ0JBQWdCQSxDQUFDZCxPQUNmTixNQUFNLGtCQUFrQk0sRUFBRSxTQUFTLEVBQUVMLEtBQUssQ0FBQ0MsTUFBTUEsRUFBRUMsS0FBSyxDQUFDO0FBQUEsRUFDM0RrQixjQUFjQSxDQUFDZixJQUFZRSxTQUN6QlIsTUFBTSxrQkFBa0JNLEVBQUUsYUFBYTtBQUFBLElBQ3JDRyxRQUFRO0FBQUEsSUFDUkMsU0FBUyxFQUFFLGdCQUFnQixtQkFBbUI7QUFBQSxJQUM5Q0YsTUFBTUcsS0FBS0MsVUFBVUosSUFBSTtBQUFBLEVBQzNCLENBQUMsRUFBRVAsS0FBSyxPQUFPQyxNQUFNO0FBQ25CLFFBQUksQ0FBQ0EsRUFBRVksR0FBSSxPQUFNLElBQUlDLE1BQU0sR0FBR2IsRUFBRWMsTUFBTSxJQUFJZCxFQUFFZSxVQUFVLEVBQUU7QUFDeEQsV0FBT2YsRUFBRUMsS0FBSztBQUFBLEVBQ2hCLENBQUM7QUFDTDtBQUVBLE1BQU1tQixhQUFxQztBQUFBLEVBQ3pDQyxVQUFVO0FBQUEsRUFDVkMsV0FBVztBQUFBLEVBQ1hDLGdCQUFnQjtBQUNsQjtBQUVBLFNBQVNDLFlBQVksRUFBRUMsT0FBZ0MsR0FBRztBQUFBQyxLQUFBO0FBQ3hELFFBQU0sQ0FBQ0MsV0FBV0MsWUFBWSxJQUFJckUsU0FBMEUsS0FBSztBQUNqSCxRQUFNc0UsY0FBY0osT0FBT0ssUUFBUUM7QUFBQUEsSUFBTyxDQUFDQyxNQUN6Q1AsT0FBT1EsS0FBS0MsTUFBTSxDQUFDbEMsTUFBTSxPQUFPQSxFQUFFZ0MsQ0FBQyxNQUFNLFFBQVE7QUFBQSxFQUNuRDtBQUNBLFFBQU0sQ0FBQ0csR0FBR0MsSUFBSSxJQUFJN0UsU0FBaUJrRSxPQUFPSyxRQUFRLENBQUMsQ0FBQztBQUNwRCxRQUFNLENBQUNPLEdBQUdDLElBQUksSUFBSS9FLFNBQWlCc0UsWUFBWSxDQUFDLEtBQUtKLE9BQU9LLFFBQVEsQ0FBQyxLQUFLTCxPQUFPSyxRQUFRLENBQUMsQ0FBQztBQUUzRjFFLFlBQVUsTUFBTTtBQUNkLFFBQUksQ0FBQ3FFLE9BQU9LLFFBQVFTLFNBQVNKLENBQUMsRUFBR0MsTUFBS1gsT0FBT0ssUUFBUSxDQUFDLENBQUM7QUFDdkQsUUFBSSxDQUFDTCxPQUFPSyxRQUFRUyxTQUFTRixDQUFDLEVBQUdDLE1BQUtULFlBQVksQ0FBQyxLQUFLSixPQUFPSyxRQUFRLENBQUMsS0FBS0wsT0FBT0ssUUFBUSxDQUFDLENBQUM7QUFBQSxFQUNoRyxHQUFHLENBQUNMLE9BQU9LLE9BQU8sQ0FBQztBQUVuQixRQUFNVSxPQUFPbkYsUUFBUSxNQUFNO0FBQ3pCLFVBQU1vRixLQUFLaEIsT0FBT1EsS0FBS1MsSUFBSSxDQUFDMUMsTUFBTUEsRUFBRW1DLENBQUMsQ0FBb0I7QUFDekQsVUFBTVEsS0FBS2xCLE9BQU9RLEtBQUtTLElBQUksQ0FBQzFDLE1BQU1BLEVBQUVxQyxDQUFDLENBQVc7QUFDaEQsUUFBSVYsY0FBYyxPQUFPO0FBQ3ZCLGFBQU8sQ0FBQyxFQUFFaUIsTUFBTSxPQUFnQkMsUUFBUUosSUFBSUssUUFBUUgsR0FBRyxDQUFDO0FBQUEsSUFDMUQ7QUFDQSxRQUFJaEIsY0FBYyxVQUFVQSxjQUFjLGFBQWFBLGNBQWMsUUFBUTtBQUMzRSxhQUFPO0FBQUEsUUFDTDtBQUFBLFVBQ0VpQixNQUFNO0FBQUEsVUFDTkcsTUFBTXBCLGNBQWMsWUFBWSxZQUFZO0FBQUEsVUFDNUNxQixNQUFNckIsY0FBYyxTQUFTLFlBQVk7QUFBQSxVQUN6Q1EsR0FBR007QUFBQUEsVUFDSEosR0FBR007QUFBQUEsUUFDTDtBQUFBLE1BQUM7QUFBQSxJQUVMO0FBQ0EsUUFBSWhCLGNBQWMsT0FBTztBQUN2QixhQUFPLENBQUMsRUFBRWlCLE1BQU0sT0FBZ0JULEdBQUdNLElBQUlKLEdBQUdNLEdBQUcsQ0FBQztBQUFBLElBQ2hEO0FBQ0EsUUFBSWhCLGNBQWMsT0FBTztBQUN2QixhQUFPLENBQUMsRUFBRWlCLE1BQU0sT0FBZ0JQLEdBQUdNLElBQUlNLE1BQU1aLEVBQUUsQ0FBQztBQUFBLElBQ2xEO0FBQ0EsV0FBTyxDQUFDLEVBQUVPLE1BQU0sV0FBb0JNLEdBQUcsQ0FBQ1AsRUFBRSxFQUFFLENBQUM7QUFBQSxFQUMvQyxHQUFHLENBQUNoQixXQUFXUSxHQUFHRSxHQUFHWixPQUFPUSxJQUFJLENBQUM7QUFFakMsU0FDRSx1QkFBQyxTQUNDO0FBQUEsMkJBQUMsU0FDQztBQUFBO0FBQUEsUUFBQztBQUFBO0FBQUEsVUFDQyxPQUFNO0FBQUEsVUFDTixPQUFPTjtBQUFBQSxVQUNQLFVBQVUsQ0FBQ3dCLE1BQU1BLEtBQUt2QixhQUFhdUIsQ0FBcUI7QUFBQSxVQUN4RCxNQUFNLENBQUMsUUFBUSxPQUFPLFdBQVcsT0FBTyxRQUFRLE9BQU8sU0FBUztBQUFBLFVBQ2hFLEdBQUc7QUFBQTtBQUFBLFFBTEw7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLE1BS1M7QUFBQSxNQUVULHVCQUFDLFVBQU8sT0FBTSxPQUFNLE9BQU9oQixHQUFHLFVBQVUsQ0FBQ2dCLE1BQU1BLEtBQUtmLEtBQUtlLENBQUMsR0FBRyxNQUFNMUIsT0FBT0ssU0FBUyxHQUFHLE9BQXRGO0FBQUE7QUFBQTtBQUFBO0FBQUEsYUFBMEY7QUFBQSxNQUMxRix1QkFBQyxVQUFPLE9BQU0sT0FBTSxPQUFPTyxHQUFHLFVBQVUsQ0FBQ2MsTUFBTUEsS0FBS2IsS0FBS2EsQ0FBQyxHQUFHLE1BQU0xQixPQUFPSyxTQUFTLEdBQUcsT0FBdEY7QUFBQTtBQUFBO0FBQUE7QUFBQSxhQUEwRjtBQUFBLFNBVDVGO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FVQTtBQUFBLElBQ0E7QUFBQSxNQUFDO0FBQUE7QUFBQSxRQUNDO0FBQUEsUUFDQSxRQUFRLEVBQUVzQixVQUFVLE1BQU1DLFFBQVEsS0FBS0MsUUFBUSxFQUFFQyxHQUFHLElBQUl2RCxHQUFHLElBQUl3RCxHQUFHLElBQUlDLEdBQUcsR0FBRyxFQUFFO0FBQUEsUUFDOUUsT0FBTyxFQUFFQyxPQUFPLE9BQU87QUFBQTtBQUFBLE1BSHpCO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxJQUcyQjtBQUFBLE9BZjdCO0FBQUE7QUFBQTtBQUFBO0FBQUEsU0FpQkE7QUFFSjtBQUFDaEMsR0EzRFFGLGFBQVc7QUFBQSxLQUFYQTtBQXVFVCxTQUFTbUMsaUJBQWlCO0FBQUFDLE1BQUE7QUFDeEIsUUFBTSxDQUFDQyxNQUFNQyxPQUFPLElBQUl2RyxTQUFTLEtBQUs7QUFDdEMsUUFBTSxDQUFDd0csTUFBTUMsT0FBTyxJQUFJekcsU0FBOEIsSUFBSTtBQUMxRCxRQUFNLENBQUMwRyxPQUFPQyxRQUFRLElBQUkzRyxTQUF3QixJQUFJO0FBRXRELFFBQU00RyxVQUFVLE9BQU9DLFVBQTJCO0FBQ2hELFFBQUksQ0FBQ0EsU0FBUyxDQUFDQSxNQUFNQyxPQUFRO0FBQzdCSCxhQUFTLElBQUk7QUFDYkosWUFBUSxJQUFJO0FBQ1osVUFBTVEsT0FBTyxJQUFJQyxTQUFTO0FBQzFCRCxTQUFLRSxPQUFPLFVBQVVKLE1BQU0sQ0FBQyxDQUFDO0FBQzlCLFFBQUk7QUFDRixZQUFNcEUsSUFBSSxNQUFNRixNQUFNLHFCQUFxQixFQUFFUyxRQUFRLFFBQVFELE1BQU1nRSxLQUFLLENBQUM7QUFDekUsVUFBSSxDQUFDdEUsRUFBRVksSUFBSTtBQUNULGNBQU1OLE9BQU8sTUFBTU4sRUFBRUMsS0FBSyxFQUFFd0UsTUFBTSxPQUFPLENBQUMsRUFBRTtBQUM1QyxjQUFNLElBQUk1RCxNQUFNUCxLQUFLb0UsVUFBVSxHQUFHMUUsRUFBRWMsTUFBTSxJQUFJZCxFQUFFZSxVQUFVLEVBQUU7QUFBQSxNQUM5RDtBQUNBLFlBQU15QixPQUFRLE1BQU14QyxFQUFFQyxLQUFLO0FBQzNCK0QsY0FBUXhCLElBQUk7QUFBQSxJQUNkLFNBQVNtQyxHQUFHO0FBQ1ZULGVBQVVTLEVBQVlDLE9BQU87QUFBQSxJQUMvQixVQUFDO0FBQ0NkLGNBQVEsS0FBSztBQUFBLElBQ2Y7QUFBQSxFQUNGO0FBRUEsU0FDRSx1QkFBQyxRQUFLLFlBQVUsTUFBQyxTQUFRLE1BQUssUUFBTyxNQUNuQztBQUFBLDJCQUFDLFNBQU0sU0FBUSxpQkFBZ0IsT0FBTSxVQUNuQztBQUFBLDZCQUFDLFNBQ0M7QUFBQSwrQkFBQyxRQUFLLElBQUksS0FBSyx5QkFBZjtBQUFBO0FBQUE7QUFBQTtBQUFBLGVBQXdCO0FBQUEsUUFDeEIsdUJBQUMsUUFBSyxNQUFLLE1BQUssR0FBRSxVQUFRO0FBQUE7QUFBQSxVQUVaLHVCQUFDLFFBQUssK0JBQU47QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFBcUI7QUFBQSxVQUFPO0FBQUEsYUFGMUM7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQUdBO0FBQUEsV0FMRjtBQUFBO0FBQUE7QUFBQTtBQUFBLGFBTUE7QUFBQSxNQUNBO0FBQUEsUUFBQztBQUFBO0FBQUEsVUFDQyxXQUFVO0FBQUEsVUFDVixTQUFRO0FBQUEsVUFDUixTQUFTRDtBQUFBQSxVQUFLO0FBQUE7QUFBQSxZQUdkO0FBQUEsY0FBQztBQUFBO0FBQUEsZ0JBQ0MsTUFBSztBQUFBLGdCQUNMLE9BQU8sRUFBRWdCLFNBQVMsT0FBTztBQUFBLGdCQUN6QixRQUFPO0FBQUEsZ0JBQ1AsVUFBVSxDQUFDRixNQUFNUixRQUFRUSxFQUFFRyxjQUFjVixLQUFLO0FBQUE7QUFBQSxjQUpoRDtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsWUFJa0Q7QUFBQTtBQUFBO0FBQUEsUUFWcEQ7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLE1BWUE7QUFBQSxTQXBCRjtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBcUJBO0FBQUEsSUFDQ0gsU0FBUyx1QkFBQyxnQkFBYSxPQUFNLE9BQU0sT0FBTSxVQUFTLElBQUcsTUFBTUEsbUJBQWxEO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBd0Q7QUFBQSxJQUNqRUYsUUFDQyx1QkFBQyxTQUFNLEtBQUssR0FBRyxJQUFHLE1BQ2hCO0FBQUEsNkJBQUMsUUFBSyxNQUFLLE1BQUk7QUFBQTtBQUFBLFFBQ1gsdUJBQUMsWUFBUUEsZUFBS2dCLGFBQWQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQUF3QjtBQUFBLFFBQVM7QUFBQSxRQUFHQyxLQUFLQyxNQUFNbEIsS0FBS21CLGFBQWEsSUFBSTtBQUFBLFFBQUU7QUFBQSxXQUQzRTtBQUFBO0FBQUE7QUFBQTtBQUFBLGFBRUE7QUFBQSxNQUNBLHVCQUFDLFFBQUssTUFBSyxNQUFLLEdBQUUsVUFBUztBQUFBO0FBQUEsUUFBYyx1QkFBQyxRQUFNbkIsZUFBS29CLFFBQVo7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQUFpQjtBQUFBLFdBQTFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsYUFBaUU7QUFBQSxTQUpuRTtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBS0E7QUFBQSxPQTlCSjtBQUFBO0FBQUE7QUFBQTtBQUFBLFNBZ0NBO0FBRUo7QUFBQ3ZCLElBN0RRRCxnQkFBYztBQUFBLE1BQWRBO0FBK0RULFNBQVN5QixjQUFjO0FBQUFDLE1BQUE7QUFDckIsUUFBTUMsS0FBS3RHLGVBQWU7QUFDMUIsUUFBTXVHLFFBQVF4RyxTQUFTLEVBQUV5RyxVQUFVLENBQUMsT0FBTyxHQUFHQyxTQUFTN0YsSUFBSU0sWUFBWSxDQUFDO0FBQ3hFLFFBQU1MLEtBQUtkLFNBQVMsRUFBRXlHLFVBQVUsQ0FBQyxJQUFJLEdBQUdDLFNBQVM3RixJQUFJQyxHQUFHLENBQUM7QUFDekQsUUFBTTZGLE1BQU0zRyxTQUFTLEVBQUV5RyxVQUFVLENBQUMsS0FBSyxHQUFHQyxTQUFTN0YsSUFBSXFCLFVBQVUsQ0FBQztBQUVsRSxRQUFNLENBQUMwRSxRQUFRQyxTQUFTLElBQUlySSxTQUF3QixJQUFJO0FBQ3hELFFBQU0sQ0FBQ3NJLEtBQUtDLE1BQU0sSUFBSXZJLFNBQVMsRUFBRTtBQUVqQ0gsWUFBVSxNQUFNO0FBQ2QsUUFBSSxDQUFDdUksVUFBVUosTUFBTS9DLE1BQU02QixRQUFRO0FBQ2pDLFlBQU0wQixRQUFRUixNQUFNL0MsS0FBSyxDQUFDO0FBQzFCb0QsZ0JBQVVHLE1BQU1DLGFBQWE7QUFDN0JGLGFBQU8xRSxXQUFXMkUsTUFBTTlDLElBQUksS0FBSywrQkFBK0I7QUFBQSxJQUNsRTtBQUFBLEVBQ0YsR0FBRyxDQUFDc0MsTUFBTS9DLElBQUksQ0FBQztBQUVmLFFBQU1yQyxTQUFTcEIsU0FBUztBQUFBLElBQ3RCeUcsVUFBVSxDQUFDLFVBQVVHLE1BQU07QUFBQSxJQUMzQkYsU0FBU0EsTUFBTTdGLElBQUlPLE9BQU93RixNQUFPO0FBQUEsSUFDakNNLFNBQVMsQ0FBQyxDQUFDTjtBQUFBQSxFQUNiLENBQUM7QUFFRCxRQUFNTyxNQUFNcEgsWUFBWTtBQUFBLElBQ3RCcUgsWUFBWUEsTUFBTXZHLElBQUlTLFNBQVMsRUFBRTJGLGVBQWVMLFFBQVNFLElBQUksQ0FBQztBQUFBLEVBQ2hFLENBQUM7QUFFRCxRQUFNTyxPQUFPdEgsWUFBWTtBQUFBLElBQ3ZCcUgsWUFBWSxZQUFZO0FBQ3RCLFVBQUksQ0FBQ1QsSUFBSWxELE1BQU02QixVQUFVLENBQUN4RSxHQUFHMkMsS0FBTSxPQUFNLElBQUkzQixNQUFNLHdCQUF3QjtBQUMzRSxZQUFNd0YsVUFBVTtBQUFBLFFBQ2RDLE9BQU87QUFBQSxRQUNQQyxPQUFPO0FBQUEsVUFDTCxFQUFFQyxNQUFNLE9BQU9SLGVBQWVMLFFBQVFFLElBQUk7QUFBQSxVQUMxQ0ssSUFBSTFELE9BQU8sRUFBRWdFLE1BQU0sVUFBVUMsY0FBY1AsSUFBSTFELEtBQUtQLEtBQUt5RSxNQUFNLEdBQUcsQ0FBQyxFQUFFLElBQUk7QUFBQSxRQUFJLEVBQzdFM0UsT0FBTzRFLE9BQU87QUFBQSxRQUNoQkMsV0FBVSxvQkFBSUMsS0FBSyxHQUFFQyxZQUFZO0FBQUEsTUFDbkM7QUFDQSxhQUFPbEgsSUFBSXVCLGFBQWF1RSxJQUFJbEQsS0FBSyxDQUFDLEVBQUV1RSxhQUFhO0FBQUEsUUFDL0NWO0FBQUFBLFFBQ0FXLFVBQVVuSCxHQUFHMkMsS0FBS3lFO0FBQUFBLFFBQ2xCQyxnQkFBZ0I7QUFBQSxNQUNsQixDQUFDO0FBQUEsSUFDSDtBQUFBLElBQ0FDLFdBQVdBLE1BQU03QixHQUFHOEIsa0JBQWtCLEVBQUU1QixVQUFVLENBQUMsS0FBSyxFQUFFLENBQUM7QUFBQSxFQUM3RCxDQUFDO0FBRUQsTUFBSUQsTUFBTThCLFVBQVcsUUFBTyx1QkFBQyxZQUFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsU0FBTztBQUVuQyxTQUNFLHVCQUFDLFNBQU0sR0FBRSxNQUFLLEtBQUksTUFDaEI7QUFBQSwyQkFBQyxvQkFBRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQWU7QUFBQSxJQUNmLHVCQUFDLFNBQU0sT0FBTSxZQUNYO0FBQUE7QUFBQSxRQUFDO0FBQUE7QUFBQSxVQUNDLE9BQU07QUFBQSxVQUNOLE9BQU8xQjtBQUFBQSxVQUNQLFVBQVUsQ0FBQ3hDLE1BQU07QUFDZnlDLHNCQUFVekMsQ0FBQztBQUNYLGtCQUFNbkIsSUFBSXVELE1BQU0vQyxNQUFNOEUsS0FBSyxDQUFDbkYsTUFBTUEsRUFBRTZELGtCQUFrQjdDLENBQUM7QUFDdkQsZ0JBQUluQixFQUFHOEQsUUFBTzFFLFdBQVdZLEVBQUVpQixJQUFJLEtBQUs0QyxHQUFHO0FBQUEsVUFDekM7QUFBQSxVQUNBLE9BQU9OLE1BQU0vQyxRQUFRLElBQUlFLElBQUksQ0FBQ1YsT0FBTztBQUFBLFlBQ25DdUYsT0FBT3ZGLEVBQUVnRTtBQUFBQSxZQUNUd0IsT0FBTyxHQUFHeEYsRUFBRWlCLElBQUksS0FBS2pCLEVBQUV5RixNQUFNO0FBQUEsVUFDL0IsRUFBRTtBQUFBLFVBQ0YsR0FBRztBQUFBO0FBQUEsUUFaTDtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsTUFZUztBQUFBLE1BRVJ0SCxPQUFPcUMsUUFDTix1QkFBQyxTQUFNLEtBQUksTUFDUnJDLGlCQUFPcUMsS0FBS2tGLE9BQU9oRixJQUFJLENBQUNjLE1BQU07QUFDN0IsY0FBTW1FLFdBQVduRSxFQUFFMUIsUUFBUVksSUFBSSxDQUFDVixNQUFNQSxFQUFFaUIsSUFBSSxFQUFFeUQsTUFBTSxHQUFHLENBQUMsRUFBRWtCLEtBQUssSUFBSTtBQUNuRSxjQUFNQyxZQUFZckUsRUFBRXJELFNBQVMsR0FBR3FELEVBQUVyRCxNQUFNLElBQUlxRCxFQUFFUCxJQUFJLEtBQUtPLEVBQUVQO0FBQ3pELGVBQ0U7QUFBQSxVQUFDO0FBQUE7QUFBQSxZQUVDLFNBQVE7QUFBQSxZQUNSLE9BQU8sRUFBRTZFLFFBQVEsVUFBVTtBQUFBLFlBQzNCLFNBQVMsTUFBTWhDLE9BQU8sVUFBVTZCLFFBQVEsU0FBU0UsU0FBUyxXQUFXO0FBQUEsWUFDckUsT0FBT3JFLEVBQUUxQixRQUFRWSxJQUFJLENBQUNWLE1BQU0sR0FBR0EsRUFBRWlCLElBQUksS0FBS2pCLEVBQUVZLElBQUksR0FBR1osRUFBRStGLFdBQVcsV0FBVyxFQUFFLEVBQUUsRUFBRUgsS0FBSyxJQUFJO0FBQUEsWUFFekZDO0FBQUFBO0FBQUFBLGNBQVU7QUFBQSxjQUFHckUsRUFBRTFCLFFBQVF1QztBQUFBQSxjQUFPO0FBQUE7QUFBQTtBQUFBLFVBTjFCd0Q7QUFBQUEsVUFEUDtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLFFBUUE7QUFBQSxNQUVKLENBQUMsS0FmSDtBQUFBO0FBQUE7QUFBQTtBQUFBLGFBZ0JBO0FBQUEsU0FoQ0o7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQWtDQTtBQUFBLElBRUE7QUFBQSxNQUFDO0FBQUE7QUFBQSxRQUNDLE9BQU07QUFBQSxRQUNOO0FBQUEsUUFDQSxTQUFTO0FBQUEsUUFDVCxPQUFPaEM7QUFBQUEsUUFDUCxVQUFVLENBQUNsQixNQUFNbUIsT0FBT25CLEVBQUVHLGNBQWN5QyxLQUFLO0FBQUEsUUFDN0MsUUFBUSxFQUFFUyxPQUFPLEVBQUVDLFlBQVksYUFBYUMsVUFBVSxHQUFHLEVBQUU7QUFBQTtBQUFBLE1BTjdEO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxJQU0rRDtBQUFBLElBRy9ELHVCQUFDLFNBQ0M7QUFBQSw2QkFBQyxVQUFPLFNBQVNoQyxJQUFJaUMsV0FBVyxTQUFTLE1BQU1qQyxJQUFJa0MsT0FBTyxHQUFHLFVBQVUsQ0FBQ3pDLFVBQVUsQ0FBQ0UsS0FBSSxvQkFBdkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxhQUVBO0FBQUEsTUFDQTtBQUFBLFFBQUM7QUFBQTtBQUFBLFVBQ0MsU0FBUTtBQUFBLFVBQ1IsU0FBU08sS0FBSytCO0FBQUFBLFVBQ2QsU0FBUyxNQUFNL0IsS0FBS2dDLE9BQU87QUFBQSxVQUMzQixVQUFVLENBQUNsQyxJQUFJMUQsUUFBUSxDQUFDa0QsSUFBSWxELE1BQU02QjtBQUFBQSxVQUFPO0FBQUE7QUFBQSxRQUozQztBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsTUFPQTtBQUFBLE1BQ0MrQixLQUFLaUMsYUFDSix1QkFBQyxTQUFNLE9BQU0sUUFBTyxTQUFRLFVBQVE7QUFBQTtBQUFBLFFBQ25CQyxPQUFRbEMsS0FBSzVELEtBQWErRixVQUFVLEVBQUU3QixNQUFNLEdBQUcsQ0FBQztBQUFBLFFBQUU7QUFBQSxXQURuRTtBQUFBO0FBQUE7QUFBQTtBQUFBLGFBRUE7QUFBQSxTQWZKO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FpQkE7QUFBQSxJQUVDUixJQUFJakMsU0FBUyx1QkFBQyxnQkFBYSxPQUFNLE9BQU0sT0FBTSxNQUFPaUMsY0FBSWpDLE1BQWdCVyxXQUEzRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQW1FO0FBQUEsSUFFaEZzQixJQUFJMUQsUUFDSCx1QkFBQyxRQUFLLFNBQVEsTUFBSyxRQUFPLE1BQUssWUFBVSxNQUN2QyxpQ0FBQyxTQUFNLEtBQUksTUFDVDtBQUFBLDZCQUFDLFNBQU0sU0FBUSxpQkFDYjtBQUFBLCtCQUFDLFNBQU0sS0FBSSxNQUNUO0FBQUEsaUNBQUMsU0FBTSxPQUFNLFFBQVEwRCxjQUFJMUQsS0FBS2lGLFVBQTlCO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBQXFDO0FBQUEsVUFDckMsdUJBQUMsUUFBSyxNQUFLLE1BQUssR0FBRSxVQUFVdkI7QUFBQUEsZ0JBQUkxRCxLQUFLZ0c7QUFBQUEsWUFBVTtBQUFBLGVBQS9DO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBQWdEO0FBQUEsVUFDaEQsdUJBQUMsUUFBSyxNQUFLLE1BQUssR0FBRSxVQUFVdEMsY0FBSTFELEtBQUtpRyxlQUFyQztBQUFBO0FBQUE7QUFBQTtBQUFBLGlCQUFpRDtBQUFBLGFBSG5EO0FBQUE7QUFBQTtBQUFBO0FBQUEsZUFJQTtBQUFBLFFBQ0EsdUJBQUMsU0FBTSxLQUFLLEdBQ1Y7QUFBQSxpQ0FBQyxRQUFLLE1BQUssTUFBSyxHQUFFLFVBQVMsMEJBQTNCO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBQXFDO0FBQUEsVUFDcEN2QyxJQUFJMUQsS0FBS2tHLG9CQUFvQmhHO0FBQUFBLFlBQUksQ0FBQ2lHLE1BQ2pDLHVCQUFDLFNBQWMsT0FBTSxTQUFRLFNBQVEsU0FBU0EsZUFBbENBLEdBQVo7QUFBQTtBQUFBO0FBQUE7QUFBQSxtQkFBZ0Q7QUFBQSxVQUNqRDtBQUFBLGFBSkg7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQUtBO0FBQUEsV0FYRjtBQUFBO0FBQUE7QUFBQTtBQUFBLGFBWUE7QUFBQSxNQUVBLHVCQUFDLFFBQUssY0FBYSxTQUNqQjtBQUFBLCtCQUFDLEtBQUssTUFBTCxFQUNDO0FBQUEsaUNBQUMsS0FBSyxLQUFMLEVBQVMsT0FBTSxTQUFRLGlCQUF4QjtBQUFBO0FBQUE7QUFBQTtBQUFBLGlCQUF5QjtBQUFBLFVBQ3pCLHVCQUFDLEtBQUssS0FBTCxFQUFTLE9BQU0sU0FBUSxrQkFBeEI7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFBMEI7QUFBQSxhQUY1QjtBQUFBO0FBQUE7QUFBQTtBQUFBLGVBR0E7QUFBQSxRQUVBLHVCQUFDLEtBQUssT0FBTCxFQUFXLE9BQU0sU0FBUSxJQUFHLE1BQzNCLGlDQUFDLGNBQVcsR0FBRyxLQUNiLGlDQUFDLFNBQU0sU0FBTyxNQUFDLGlCQUFlLE1BQUMsbUJBQWlCLE1BQUMsSUFBRyxNQUNsRDtBQUFBLGlDQUFDLE1BQU0sT0FBTixFQUNDLGlDQUFDLE1BQU0sSUFBTixFQUNFekMsY0FBSTFELEtBQUtWLFFBQVFZO0FBQUFBLFlBQUksQ0FBQ1YsTUFDckIsdUJBQUMsTUFBTSxJQUFOLEVBQWtCQSxlQUFKQSxHQUFmO0FBQUE7QUFBQTtBQUFBO0FBQUEsbUJBQXFCO0FBQUEsVUFDdEIsS0FISDtBQUFBO0FBQUE7QUFBQTtBQUFBLGlCQUlBLEtBTEY7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFNQTtBQUFBLFVBQ0EsdUJBQUMsTUFBTSxPQUFOLEVBQ0VrRSxjQUFJMUQsS0FBS1AsS0FBS1M7QUFBQUEsWUFBSSxDQUFDa0csS0FBS0MsTUFDdkIsdUJBQUMsTUFBTSxJQUFOLEVBQ0UzQyxjQUFJMUQsS0FBTVYsUUFBUVk7QUFBQUEsY0FBSSxDQUFDVixNQUN0Qix1QkFBQyxNQUFNLElBQU4sRUFBaUIsaUNBQUMsUUFBTXNHLGlCQUFPTSxJQUFJNUcsQ0FBQyxLQUFLLEVBQUUsS0FBMUI7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBNEIsS0FBL0JBLEdBQWY7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBcUQ7QUFBQSxZQUN0RCxLQUhZNkcsR0FBZjtBQUFBO0FBQUE7QUFBQTtBQUFBLG1CQUlBO0FBQUEsVUFDRCxLQVBIO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBUUE7QUFBQSxhQWhCRjtBQUFBO0FBQUE7QUFBQTtBQUFBLGVBaUJBLEtBbEJGO0FBQUE7QUFBQTtBQUFBO0FBQUEsZUFtQkEsS0FwQkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQXFCQTtBQUFBLFFBRUEsdUJBQUMsS0FBSyxPQUFMLEVBQVcsT0FBTSxTQUFRLElBQUcsTUFDM0IsaUNBQUMsZUFBWSxRQUFRM0MsSUFBSTFELFFBQXpCO0FBQUE7QUFBQTtBQUFBO0FBQUEsZUFBOEIsS0FEaEM7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQUVBO0FBQUEsV0EvQkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxhQWdDQTtBQUFBLFNBL0NGO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FnREEsS0FqREY7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQWtEQTtBQUFBLE9BdkhKO0FBQUE7QUFBQTtBQUFBO0FBQUEsU0F5SEE7QUFFSjtBQUFDNkMsSUE3S1FELGFBQVc7QUFBQSxVQUNQcEcsZ0JBQ0dELFVBQ0hBLFVBQ0NBLFVBYUdBLFVBTUhELGFBSUNBLFdBQVc7QUFBQTtBQUFBLE1BM0JqQnNHO0FBK0tULFNBQVMwRCxlQUFlO0FBQUFDLE1BQUE7QUFDdEIsUUFBTXJELE1BQU0zRyxTQUFTLEVBQUV5RyxVQUFVLENBQUMsS0FBSyxHQUFHQyxTQUFTN0YsSUFBSXFCLFVBQVUsQ0FBQztBQUNsRSxTQUNFLHVCQUFDLFNBQU0sR0FBRSxNQUFLLEtBQUksTUFDaEI7QUFBQSwyQkFBQyxTQUFNLE9BQU8sR0FBRyxxQkFBakI7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUFzQjtBQUFBLElBQ3JCeUUsSUFBSTJCLGFBQWEsdUJBQUMsWUFBRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQU87QUFBQSxJQUN4QjNCLElBQUlsRCxRQUNILHVCQUFDLFNBQU0sU0FBTyxNQUFDLGlCQUFlLE1BQUMsbUJBQWlCLE1BQzlDO0FBQUEsNkJBQUMsTUFBTSxPQUFOLEVBQ0MsaUNBQUMsTUFBTSxJQUFOLEVBQ0M7QUFBQSwrQkFBQyxNQUFNLElBQU4sRUFBUyxrQkFBVjtBQUFBO0FBQUE7QUFBQTtBQUFBLGVBQVk7QUFBQSxRQUNaLHVCQUFDLE1BQU0sSUFBTixFQUFTLHFCQUFWO0FBQUE7QUFBQTtBQUFBO0FBQUEsZUFBZTtBQUFBLFFBQ2YsdUJBQUMsTUFBTSxJQUFOLEVBQVMsa0JBQVY7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQUFZO0FBQUEsUUFDWix1QkFBQyxNQUFNLElBQU4sRUFBUyxrQkFBVjtBQUFBO0FBQUE7QUFBQTtBQUFBLGVBQVk7QUFBQSxXQUpkO0FBQUE7QUFBQTtBQUFBO0FBQUEsYUFLQSxLQU5GO0FBQUE7QUFBQTtBQUFBO0FBQUEsYUFPQTtBQUFBLE1BQ0EsdUJBQUMsTUFBTSxPQUFOLEVBQ0VrRCxjQUFJbEQsS0FBS0U7QUFBQUEsUUFBSSxDQUFDc0csT0FDYix1QkFBQyxNQUFNLElBQU4sRUFDQztBQUFBLGlDQUFDLE1BQU0sSUFBTixFQUFVQSxhQUFHQyxRQUFkO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBQW1CO0FBQUEsVUFDbkIsdUJBQUMsTUFBTSxJQUFOLEVBQVVELGFBQUdFLGtCQUFrQixJQUFJckMsS0FBS21DLEdBQUdFLGVBQWUsRUFBRUMsZUFBZSxJQUFJLE9BQWhGO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBQW9GO0FBQUEsVUFDcEYsdUJBQUMsTUFBTSxJQUFOLEVBQVVILGFBQUdJLGdCQUFnQjFDLE1BQU0sR0FBRyxDQUFDLEtBQUssT0FBN0M7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFBaUQ7QUFBQSxVQUNqRCx1QkFBQyxNQUFNLElBQU4sRUFDQyxpQ0FBQyxVQUFPLE1BQUssTUFBSyxXQUFXdkgsTUFBTSxJQUFJLGNBQWM2SixHQUFHakMsV0FBVyxJQUFJLGtCQUF2RTtBQUFBO0FBQUE7QUFBQTtBQUFBLGlCQUF5RSxLQUQzRTtBQUFBO0FBQUE7QUFBQTtBQUFBLGlCQUVBO0FBQUEsYUFOYWlDLEdBQUdqQyxhQUFsQjtBQUFBO0FBQUE7QUFBQTtBQUFBLGVBT0E7QUFBQSxNQUNELEtBVkg7QUFBQTtBQUFBO0FBQUE7QUFBQSxhQVdBO0FBQUEsU0FwQkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQXFCQTtBQUFBLE9BekJKO0FBQUE7QUFBQTtBQUFBO0FBQUEsU0EyQkE7QUFFSjtBQUFDZ0MsSUFoQ1FELGNBQVk7QUFBQSxVQUNQL0osUUFBUTtBQUFBO0FBQUEsTUFEYitKO0FBa0NULFNBQVNPLGlCQUFpQjtBQUFBQyxNQUFBO0FBQ3hCLFFBQU0sRUFBRWxKLEdBQUcsSUFBSWIsVUFBVTtBQUN6QixRQUFNeUosS0FBS2pLLFNBQVM7QUFBQSxJQUNsQnlHLFVBQVUsQ0FBQyxNQUFNcEYsRUFBRTtBQUFBLElBQ25CcUYsU0FBU0EsTUFBTTdGLElBQUlzQixlQUFlZCxFQUFHO0FBQUEsSUFDckM2RixTQUFTLENBQUMsQ0FBQzdGO0FBQUFBLEVBQ2IsQ0FBQztBQUNELFNBQ0UsdUJBQUMsU0FBTSxHQUFFLE1BQUssS0FBSSxNQUNoQjtBQUFBLDJCQUFDLFNBQ0MsaUNBQUMsVUFBTyxXQUFXakIsTUFBTSxJQUFHLGNBQWEsU0FBUSxVQUFTLG9CQUExRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQThELEtBRGhFO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FFQTtBQUFBLElBQ0M2SixHQUFHM0IsYUFBYSx1QkFBQyxZQUFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBTztBQUFBLElBQ3ZCMkIsR0FBR3hHLFFBQ0YsdUJBQUMsUUFBSyxZQUFVLE1BQ2Q7QUFBQSw2QkFBQyxTQUFNLE9BQU8sR0FBSXdHLGFBQUd4RyxLQUFLeUcsUUFBMUI7QUFBQTtBQUFBO0FBQUE7QUFBQSxhQUErQjtBQUFBLE1BQy9CLHVCQUFDLFFBQUssTUFBSyxNQUFLLEdBQUUsVUFBUztBQUFBO0FBQUEsUUFBUUQsR0FBR3hHLEtBQUtvRSxZQUFZO0FBQUEsV0FBdkQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxhQUEyRDtBQUFBLE1BQzNELHVCQUFDLFFBQUssT0FBSyxNQUFDLE9BQU8sRUFBRTJDLFdBQVcsRUFBRSxHQUMvQjlJLGVBQUtDLFVBQVVzSSxHQUFHeEcsS0FBSzZELFNBQVMsTUFBTSxDQUFDLEtBRDFDO0FBQUE7QUFBQTtBQUFBO0FBQUEsYUFFQTtBQUFBLFNBTEY7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQU1BO0FBQUEsT0FaSjtBQUFBO0FBQUE7QUFBQTtBQUFBLFNBY0E7QUFFSjtBQUFDaUQsSUF4QlFELGdCQUFjO0FBQUEsVUFDTjlKLFdBQ0pSLFFBQVE7QUFBQTtBQUFBLE1BRlpzSztBQTBCVCxTQUFTRyxXQUFXLEVBQUVDLFlBQXFDLEdBQUc7QUFBQUMsTUFBQTtBQVU1RCxRQUFNLENBQUNDLFNBQVNDLFVBQVUsSUFBSXJNLFNBQVMsSUFBSTtBQUMzQ0gsWUFBVSxNQUFNO0FBQ2R3TSxlQUFXLElBQUk7QUFBQSxFQUNqQixHQUFHLENBQUNILFdBQVcsQ0FBQztBQUVoQixRQUFNSSxNQUFNLDhEQUE4REosV0FBVztBQUNyRixTQUNFO0FBQUEsSUFBQztBQUFBO0FBQUEsTUFFQztBQUFBLE1BQ0EsT0FBTTtBQUFBLE1BQ04sUUFBUSxNQUFNRyxXQUFXLEtBQUs7QUFBQSxNQUM5QixPQUFPO0FBQUEsUUFDTGxHLE9BQU87QUFBQSxRQUNQTCxRQUFRO0FBQUEsUUFDUnlHLFFBQVE7QUFBQSxRQUNSakYsU0FBUztBQUFBLFFBQ1RrRixZQUFZO0FBQUEsUUFDWkMsU0FBU0wsVUFBVSxPQUFPO0FBQUEsTUFDNUI7QUFBQSxNQUNBLE9BQU07QUFBQTtBQUFBLElBWkRGO0FBQUFBLElBRFA7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxFQWF5QztBQUc3QztBQUlBQyxJQXJDU0YsWUFBVTtBQUFBLE1BQVZBO0FBc0NULE1BQU1TLG1CQUFtQjtBQUN6QixNQUFNQyxnQkFBZ0I7QUFFdEIsZUFBZUMsNEJBQTRCQyxVQUE0QkMsUUFBK0I7QUFDcEcsUUFBTUMsTUFBTSx5QkFBeUJMLGdCQUFnQjtBQUNyRCxRQUFNekosVUFBdUI7QUFBQSxJQUMzQixnQkFBZ0I7QUFBQSxJQUNoQitKLGVBQWUsU0FBU0wsYUFBYTtBQUFBLEVBQ3ZDO0FBRUEsTUFBSU0sV0FBdUI7QUFDM0IsUUFBTUMsT0FBTyxNQUFNM0ssTUFBTXdLLEtBQUssRUFBRTlKLFNBQVNrSyxhQUFhLE9BQU8sQ0FBQztBQUM5RCxNQUFJRCxLQUFLN0osSUFBSTtBQUNYNEosZUFBVyxNQUFNQyxLQUFLeEssS0FBSztBQUFBLEVBQzdCO0FBQ0EsTUFBSSxDQUFDdUssVUFBVTtBQUNiQSxlQUFXO0FBQUEsTUFDVDVILE1BQU07QUFBQSxNQUNOeUQsU0FBUztBQUFBLFFBQ1BFLE9BQU87QUFBQSxRQUNQb0UsVUFBVSxFQUFFQyxZQUFZLEVBQUUzSCxNQUFNLFdBQVc0SCxjQUFjLFdBQVcsRUFBRTtBQUFBLFFBQ3RFQyxVQUFVO0FBQUEsUUFDVkMsZ0JBQWdCO0FBQUEsTUFDbEI7QUFBQSxNQUNBQyxRQUFRO0FBQUEsTUFDUi9ILE1BQU1nSDtBQUFBQSxNQUNOaEIsTUFBTWdCO0FBQUFBLElBQ1I7QUFBQSxFQUNGO0FBQ0EsUUFBTWdCLE9BQU87QUFBQSxJQUNYQyxXQUFXO0FBQUEsSUFDWFAsVUFBVSxFQUFFUSxtQkFBbUIsTUFBTWYsU0FBUztBQUFBLElBQzlDQyxRQUFRRCxhQUFhLFFBQVE7QUFBQSxFQUFVQyxNQUFNLEtBQUtBO0FBQUFBLElBQ2xEZSxTQUFTO0FBQUEsSUFDVEMsaUJBQWlCO0FBQUEsRUFDbkI7QUFDQWIsV0FBU25FLFFBQVFFLE1BQU0rRSxLQUFLTCxJQUFJO0FBQ2hDVCxXQUFTNUgsT0FBTztBQUNoQjRILFdBQVNRLFNBQVM7QUFDbEJSLFdBQVN2SCxPQUFPZ0g7QUFDaEJPLFdBQVN2QixPQUFPZ0I7QUFFaEIsUUFBTXNCLE1BQU0sTUFBTXpMLE1BQU13SyxLQUFLO0FBQUEsSUFDM0IvSixRQUFRO0FBQUEsSUFDUkM7QUFBQUEsSUFDQWtLLGFBQWE7QUFBQSxJQUNicEssTUFBTUcsS0FBS0MsVUFBVTtBQUFBLE1BQ25Ca0MsTUFBTTtBQUFBLE1BQ05vSSxRQUFRO0FBQUEsTUFDUjNFLFNBQVNtRSxTQUFTbkU7QUFBQUEsSUFDcEIsQ0FBQztBQUFBLEVBQ0gsQ0FBQztBQUNELE1BQUksQ0FBQ2tGLElBQUkzSyxJQUFJO0FBQ1gsVUFBTSxJQUFJQyxNQUFNLHVCQUF1QjBLLElBQUl6SyxNQUFNLEVBQUU7QUFBQSxFQUNyRDtBQUNGO0FBUUEsU0FBUzBLLHdCQUF3QkMsTUFBbUU7QUFHbEcsUUFBTUMsU0FBNkI7QUFDbkMsUUFBTUMsS0FBSztBQUNYLE1BQUlDO0FBQ0osVUFBUUEsSUFBSUQsR0FBR0UsS0FBS0osSUFBSSxPQUFPLE1BQU07QUFDbkNDLFdBQU9KLEtBQUssRUFBRWxCLFVBQVV3QixFQUFFLENBQUMsRUFBRUUsWUFBWSxHQUF1QnpCLFFBQVF1QixFQUFFLENBQUMsRUFBRUcsS0FBSyxFQUFFLENBQUM7QUFBQSxFQUN2RjtBQUNBLFNBQU8sQ0FBQyxFQUFFTixNQUFNQyxPQUFPLENBQUM7QUFDMUI7QUFJQSxTQUFTTSxnQkFBZ0JQLE1BQXNCO0FBQzdDLFNBQU9BLEtBQ0pRLFFBQVEsa0NBQWtDLEVBQUUsRUFDNUNBLFFBQVEsV0FBVyxNQUFNLEVBQ3pCRixLQUFLO0FBQ1Y7QUFLQSxlQUFlRyx1QkFHWjtBQUdELFFBQU1DLE9BQU8sSUFBSUMsZ0JBQWdCO0FBQ2pDLFFBQU1DLFFBQVFDLE9BQU9DLFdBQVcsTUFBTUosS0FBS0ssTUFBTSxHQUFHLEdBQUk7QUFDeEQsTUFBSTtBQUNGLFVBQU14TSxJQUFJLE1BQU1GLE1BQU0seUJBQXlCbUssZ0JBQWdCLElBQUk7QUFBQSxNQUNqRXpKLFNBQVMsRUFBRStKLGVBQWUsU0FBU0wsYUFBYSxHQUFHO0FBQUEsTUFDbkR1QyxRQUFRTixLQUFLTTtBQUFBQSxJQUNmLENBQUM7QUFDRCxRQUFJLENBQUN6TSxFQUFFWSxHQUFJLFFBQU8sRUFBRThMLFFBQVEsSUFBSUMsV0FBVyxFQUFFO0FBQzdDLFVBQU0zRCxLQUFLLE1BQU1oSixFQUFFQyxLQUFLO0FBQ3hCLFVBQU1zRyxRQUFleUMsSUFBSTNDLFNBQVNFLFNBQVM7QUFDM0MsVUFBTXFHLFlBQVlyRyxNQUNmeEUsT0FBTyxDQUFDQyxNQUFNQSxFQUFFa0osY0FBYyxNQUFNLEVBQ3BDeEksSUFBSSxDQUFDVixNQUFPNkssTUFBTUMsUUFBUTlLLEVBQUVxSSxNQUFNLElBQUlySSxFQUFFcUksT0FBT3pDLEtBQUssRUFBRSxJQUFJNUYsRUFBRXFJLFVBQVUsRUFBRyxFQUN6RTNILElBQUksQ0FBQ3FLLE1BQWNBLEVBQUVoQixLQUFLLENBQUMsRUFDM0JoSyxPQUFPLENBQUNnTCxNQUFNQSxFQUFFMUksU0FBUyxDQUFDO0FBQzdCLFFBQUl1SSxVQUFVdkksV0FBVyxFQUFHLFFBQU8sRUFBRXFJLFFBQVEsSUFBSUMsV0FBVyxFQUFFO0FBQzlELFVBQU1yTSxPQUFPc00sVUFDVmxLLElBQUksQ0FBQ3FLLEdBQUdsRSxNQUFNLGFBQWFBLElBQUksQ0FBQztBQUFBLEVBQVNrRSxDQUFDLEVBQUUsRUFDNUNuRixLQUFLLE1BQU07QUFDZCxVQUFNOEUsU0FDSixNQUFNekMsZ0JBQWdCO0FBQUE7QUFBQSxJQUd0QjNKO0FBQ0YsV0FBTyxFQUFFb00sUUFBUUMsV0FBV0MsVUFBVXZJLE9BQU87QUFBQSxFQUMvQyxRQUFRO0FBQ04sV0FBTyxFQUFFcUksUUFBUSxJQUFJQyxXQUFXLEVBQUU7QUFBQSxFQUNwQyxVQUFDO0FBQ0NMLFdBQU9VLGFBQWFYLEtBQUs7QUFBQSxFQUMzQjtBQUNGO0FBRUEsU0FBU1ksYUFBYTtBQUFBLEVBQ3BCQztBQUFBQSxFQUNBQztBQUlGLEdBQUc7QUFBQUMsTUFBQTtBQUNELFFBQU0sQ0FBQ0MsU0FBU0MsVUFBVSxJQUFJL1AsU0FBdUIsRUFBRTtBQUN2RCxRQUFNLENBQUN5SyxPQUFPdUYsUUFBUSxJQUFJaFEsU0FBUyxFQUFFO0FBQ3JDLFFBQU0sQ0FBQ2lRLFNBQVNDLFVBQVUsSUFBSWxRLFNBQWlCLEVBQUU7QUFDakQsUUFBTSxDQUFDc0csTUFBTUMsT0FBTyxJQUFJdkcsU0FBUyxLQUFLO0FBQ3RDLFFBQU0sQ0FBQzBHLE9BQU9DLFFBQVEsSUFBSTNHLFNBQXdCLElBQUk7QUFDdEQsUUFBTSxDQUFDbVEsY0FBY0MsZUFBZSxJQUFJcFEsU0FBaUIsRUFBRTtBQUMzRCxRQUFNLENBQUNxUSxZQUFZQyxhQUFhLElBQUl0USxTQUF3QixJQUFJO0FBR2hFLFFBQU11USxjQUFjeFEsT0FBb0Isb0JBQUl5USxJQUFJLENBQUM7QUFJakQsUUFBTUMsVUFBVTFRLE9BQThCLElBQUk7QUFDbEQsUUFBTSxDQUFDMlEsWUFBWUMsYUFBYSxJQUFJM1EsU0FBUyxJQUFJO0FBRWpESCxZQUFVLE1BQU07QUFDZDBDLFVBQU0sdUJBQXVCLEVBQzFCQyxLQUFLLENBQUNDLE1BQU9BLEVBQUVZLEtBQUtaLEVBQUVDLEtBQUssSUFBSSxJQUFLLEVBQ3BDRixLQUFLLENBQUNvTyxNQUFNQSxLQUFLUixnQkFBZ0JRLEVBQUVDLFFBQVEsQ0FBQyxFQUM1QzNKLE1BQU0sTUFBTTtBQUFBLElBQUMsQ0FBQztBQUFBLEVBQ25CLEdBQUcsRUFBRTtBQUVMckgsWUFBVSxNQUFNO0FBQ2QsUUFBSSxDQUFDNlEsV0FBWTtBQUNqQixVQUFNSSxLQUFLTCxRQUFRTTtBQUNuQixRQUFJRCxHQUFJQSxJQUFHRSxZQUFZRixHQUFHRztBQUFBQSxFQUM1QixHQUFHLENBQUNuQixTQUFTRyxTQUFTUyxVQUFVLENBQUM7QUFFakMsUUFBTVEsZUFBZUEsTUFBTTtBQUN6QixVQUFNSixLQUFLTCxRQUFRTTtBQUNuQixRQUFJLENBQUNELEdBQUk7QUFFVCxVQUFNSyxXQUFXTCxHQUFHRyxlQUFlSCxHQUFHRSxZQUFZRixHQUFHTSxlQUFlO0FBQ3BFVCxrQkFBY1EsUUFBUTtBQUFBLEVBQ3hCO0FBRUEsUUFBTUUsaUJBQWlCQSxNQUFNO0FBQzNCLFVBQU1QLEtBQUtMLFFBQVFNO0FBQ25CLFFBQUksQ0FBQ0QsR0FBSTtBQUNUQSxPQUFHRSxZQUFZRixHQUFHRztBQUNsQk4sa0JBQWMsSUFBSTtBQUFBLEVBQ3BCO0FBRUEsUUFBTVcsT0FBTyxZQUFZO0FBQ3ZCLFFBQUksQ0FBQzdHLE1BQU0rRCxLQUFLLEtBQUtsSSxLQUFNO0FBQzNCSyxhQUFTLElBQUk7QUFDYixVQUFNNEssV0FBVzlHLE1BQU0rRCxLQUFLO0FBQzVCd0IsYUFBUyxFQUFFO0FBQ1h6SixZQUFRLElBQUk7QUFHWm9LLGtCQUFjLElBQUk7QUFDbEJaLGVBQVcsQ0FBQ3lCLE1BQU0sQ0FBQyxHQUFHQSxHQUFHLEVBQUVDLE1BQU0sUUFBUTNJLFNBQVN5SSxTQUFTLENBQUMsQ0FBQztBQUM3RHJCLGVBQVcsRUFBRTtBQUViLFFBQUk7QUFLRixZQUFNLEVBQUVmLFFBQVF1QyxTQUFTLElBQUksTUFBTS9DLHFCQUFxQjtBQUN4RCxZQUFNZ0Qsb0JBQW9CRCxXQUN0QixHQUFHQSxRQUFRO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxFQUF1QkgsUUFBUSxLQUMxQ0E7QUFFSixZQUFNSyxNQUFNLE1BQU1yUCxNQUFNLHFCQUFxQjtBQUFBLFFBQzNDUyxRQUFRO0FBQUEsUUFDUkMsU0FBUyxFQUFFLGdCQUFnQixtQkFBbUI7QUFBQSxRQUM5Q0YsTUFBTUcsS0FBS0MsVUFBVTtBQUFBLFVBQ25Cb08sVUFBVUk7QUFBQUEsVUFDVjdCO0FBQUFBLFVBQ0FySCxlQUFla0g7QUFBQUEsUUFDakIsQ0FBQztBQUFBLE1BQ0gsQ0FBQztBQUNELFVBQUksQ0FBQ2lDLElBQUl2TyxNQUFNLENBQUN1TyxJQUFJN08sTUFBTTtBQUN4QixjQUFNQSxPQUFPLE1BQU02TyxJQUFJbFAsS0FBSyxFQUFFd0UsTUFBTSxPQUFPLENBQUMsRUFBRTtBQUM5QyxjQUFNLElBQUk1RCxNQUFNUCxLQUFLb0UsVUFBVSxHQUFHeUssSUFBSXJPLE1BQU0sSUFBSXFPLElBQUlwTyxVQUFVLEVBQUU7QUFBQSxNQUNsRTtBQUNBLFlBQU1xTyxTQUFTRCxJQUFJN08sS0FBSytPLFVBQVU7QUFDbEMsWUFBTUMsTUFBTSxJQUFJQyxZQUFZO0FBQzVCLFVBQUlDLE1BQU07QUFDVixVQUFJQyxZQUFZO0FBQ2hCLGFBQU8sTUFBTTtBQUNYLGNBQU0sRUFBRWxJLE9BQU9tSSxLQUFLLElBQUksTUFBTU4sT0FBT08sS0FBSztBQUMxQyxZQUFJRCxLQUFNO0FBQ1ZGLGVBQU9GLElBQUlNLE9BQU9ySSxPQUFPLEVBQUVzSSxRQUFRLEtBQUssQ0FBQztBQUN6QyxZQUFJQztBQUNKLGdCQUFRQSxLQUFLTixJQUFJTyxRQUFRLElBQUksTUFBTSxHQUFHO0FBQ3BDLGdCQUFNQyxPQUFPUixJQUFJOUksTUFBTSxHQUFHb0osRUFBRSxFQUFFL0QsS0FBSztBQUNuQ3lELGdCQUFNQSxJQUFJOUksTUFBTW9KLEtBQUssQ0FBQztBQUN0QixjQUFJLENBQUNFLEtBQU07QUFDWCxjQUFJO0FBQ0Ysa0JBQU1DLE1BQU14UCxLQUFLeVAsTUFBTUYsSUFBSTtBQUMzQixnQkFBSUMsSUFBSWhNLE9BQU87QUFDYixvQkFBTSxJQUFJcEQsTUFBTW9QLElBQUloTSxLQUFLO0FBQUEsWUFDM0I7QUFDQSxnQkFBSWdNLElBQUlFLE9BQU87QUFDYlYsMkJBQWFRLElBQUlFO0FBQ2pCMUMseUJBQVdnQyxTQUFTO0FBQUEsWUFDdEI7QUFBQSxVQUNGLFNBQVM5SyxHQUFHO0FBRVYsZ0JBQUtBLEVBQVlDLFlBQVksYUFBYyxPQUFNRDtBQUFBQSxVQUNuRDtBQUFBLFFBQ0Y7QUFBQSxNQUNGO0FBSUEsVUFBSXlMLGVBQWU7QUFDbkI5QyxpQkFBVyxDQUFDeUIsTUFBTTtBQUNoQnFCLHVCQUFlckIsRUFBRTFLO0FBQ2pCLGVBQU8sQ0FBQyxHQUFHMEssR0FBRyxFQUFFQyxNQUFNLGFBQWEzSSxTQUFTb0osVUFBVSxDQUFDO0FBQUEsTUFDekQsQ0FBQztBQUNEaEMsaUJBQVcsRUFBRTtBQUNiLFlBQU0vQixTQUFTRix3QkFBd0JpRSxTQUFTLEVBQUUsQ0FBQyxFQUFFL0Q7QUFDckQsZUFBUzJFLElBQUksR0FBR0EsSUFBSTNFLE9BQU9ySCxRQUFRZ00sS0FBSztBQUN0QyxjQUFNQyxNQUFNLEdBQUdGLFlBQVksSUFBSUMsQ0FBQztBQUNoQyxZQUFJdkMsWUFBWVEsUUFBUWlDLElBQUlELEdBQUcsRUFBRztBQUNsQ3hDLG9CQUFZUSxRQUFRa0MsSUFBSUYsR0FBRztBQUczQixZQUFJO0FBQ0YsZ0JBQU1HLFNBQVMvRSxPQUFPMkUsQ0FBQyxDQUFDO0FBQUEsUUFDMUIsUUFBUTtBQUFBLFFBQ047QUFBQSxNQUVKO0FBQUEsSUFDRixTQUFTMUwsR0FBRztBQUNWVCxlQUFVUyxFQUFZQyxPQUFPO0FBQUEsSUFDL0IsVUFBQztBQUNDZCxjQUFRLEtBQUs7QUFBQSxJQUNmO0FBQUEsRUFDRjtBQUVBLFFBQU0yTSxXQUFXLE9BQU9DLFVBQTRCO0FBQ2xEeE0sYUFBUyxJQUFJO0FBQ2IsUUFBSTtBQUNGLFlBQU1pRyw0QkFBNEJ1RyxNQUFNdEcsVUFBVXNHLE1BQU1yRyxNQUFNO0FBRzlELFVBQUk7QUFDRixjQUFNdkssTUFBTSw4QkFBOEI7QUFBQSxVQUN4Q1MsUUFBUTtBQUFBLFVBQ1JDLFNBQVMsRUFBRSxnQkFBZ0IsbUJBQW1CO0FBQUEsVUFDOUNGLE1BQU1HLEtBQUtDLFVBQVU7QUFBQSxZQUNuQmlRLGVBQWUxRztBQUFBQSxZQUNmRyxVQUFVc0csTUFBTXRHO0FBQUFBLFlBQ2hCd0csZUFBZUYsTUFBTXJHLE9BQU9oRztBQUFBQSxZQUM1QjJCLGVBQWVrSDtBQUFBQSxVQUNqQixDQUFDO0FBQUEsUUFDSCxDQUFDO0FBQUEsTUFDSCxRQUFRO0FBQUEsTUFFTjtBQUVGVyxvQkFBYyxHQUFHNkMsTUFBTXRHLFNBQVN5RyxZQUFZLENBQUMseUJBQXlCO0FBQ3RFdkUsYUFBT0MsV0FBVyxNQUFNc0IsY0FBYyxJQUFJLEdBQUcsR0FBSTtBQUdqRFYsdUJBQWlCO0FBQUEsSUFDbkIsU0FBU3hJLEdBQUc7QUFDVlQsZUFBUyxZQUFhUyxFQUFZQyxPQUFPLEVBQUU7QUFBQSxJQUM3QztBQUFBLEVBQ0Y7QUFFQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxJQU1FO0FBQUEsTUFBQztBQUFBO0FBQUEsUUFDQyxHQUFFO0FBQUEsUUFDRixLQUFJO0FBQUEsUUFDSixPQUFPLEVBQUV2QixRQUFRLHNCQUFzQnlOLFVBQVUsU0FBUztBQUFBLFFBRTFEO0FBQUEsaUNBQUMsU0FBTSxTQUFRLGlCQUNiO0FBQUEsbUNBQUMsU0FBTSxPQUFPLEdBQUcsMEJBQWpCO0FBQUE7QUFBQTtBQUFBO0FBQUEsbUJBQTJCO0FBQUEsWUFDMUJwRCxnQkFBZ0IsdUJBQUMsU0FBTSxTQUFRLFNBQVNBLDBCQUF4QjtBQUFBO0FBQUE7QUFBQTtBQUFBLG1CQUFxQztBQUFBLGVBRnhEO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBR0E7QUFBQSxVQUVBO0FBQUEsWUFBQztBQUFBO0FBQUEsY0FDQyxLQUFLTTtBQUFBQSxjQUNMLFVBQVVTO0FBQUFBLGNBQ1YsZUFBWTtBQUFBLGNBQ1osT0FBTztBQUFBLGdCQUNMc0MsTUFBTTtBQUFBLGdCQUNOQyxXQUFXO0FBQUEsZ0JBQ1hDLFdBQVc7QUFBQSxnQkFDWEMsY0FBYztBQUFBLGdCQUNkck0sU0FBUztBQUFBLGdCQUNUc00sZUFBZTtBQUFBLGdCQUNmQyxLQUFLO0FBQUEsZ0JBQ0xDLFVBQVU7QUFBQSxjQUNaO0FBQUEsY0FFQ2hFO0FBQUFBLHdCQUFRaEosV0FBVyxLQUFLLENBQUNtSixXQUN4Qix1QkFBQyxRQUFLLE1BQUssTUFBSyxHQUFFLFVBQVE7QUFBQTtBQUFBLGtCQUVNdkQ7QUFBQUEsa0JBQWlCO0FBQUEscUJBRmpEO0FBQUE7QUFBQTtBQUFBO0FBQUEsdUJBR0E7QUFBQSxnQkFHRG9ELFFBQVEzSyxJQUFJLENBQUNrSixHQUFHL0MsTUFBTTtBQUNyQix3QkFBTTZDLFNBQ0pFLEVBQUVvRCxTQUFTLGNBQWN4RCx3QkFBd0JJLEVBQUV2RixPQUFPLEVBQUUsQ0FBQyxFQUFFcUYsU0FBUztBQUMxRSx3QkFBTTRGLFlBQ0oxRixFQUFFb0QsU0FBUyxlQUFldEQsT0FBT3JILFNBQVMsSUFDdEMySCxnQkFBZ0JKLEVBQUV2RixPQUFPLElBQ3pCdUYsRUFBRXZGO0FBQ1IseUJBQ0UsdUJBQUMsUUFBYSxZQUFVLE1BQUMsU0FBUSxNQUFLLFFBQU8sTUFDM0M7QUFBQSwyQ0FBQyxTQUFNLEtBQUksTUFBSyxJQUFJLEdBQ2xCLGlDQUFDLFNBQU0sTUFBSyxNQUFLLE9BQU91RixFQUFFb0QsU0FBUyxTQUFTLFNBQVMsU0FDbERwRCxZQUFFb0QsU0FBUyxTQUFTLE1BQU0sVUFEN0I7QUFBQTtBQUFBO0FBQUE7QUFBQSwyQkFFQSxLQUhGO0FBQUE7QUFBQTtBQUFBO0FBQUEsMkJBSUE7QUFBQSxvQkFJQ3NDLGFBQ0MsdUJBQUMsUUFBSyxNQUFLLE1BQUssT0FBTyxFQUFFQyxZQUFZLFdBQVcsR0FDN0NELHVCQURIO0FBQUE7QUFBQTtBQUFBO0FBQUEsMkJBRUE7QUFBQSxvQkFFRDFGLEVBQUVvRCxTQUFTLGVBQWV0RCxPQUFPckgsU0FBUyxLQUN6Qyx1QkFBQyxTQUFNLElBQUksR0FBRyxLQUFJLE1BQ2hCO0FBQUEsNkNBQUMsU0FBTSxTQUFRLFdBQVUsT0FBTSxTQUFRLE1BQUssTUFBSTtBQUFBO0FBQUEsd0JBQzNDcUgsT0FBT3JIO0FBQUFBLHdCQUFPO0FBQUEsd0JBQU00RjtBQUFBQSx3QkFBaUI7QUFBQSwyQkFEMUM7QUFBQTtBQUFBO0FBQUE7QUFBQSw2QkFFQTtBQUFBLHNCQUNDeUIsT0FBT2hKO0FBQUFBLHdCQUFJLENBQUNlLEdBQUc0TSxNQUNkO0FBQUEsMEJBQUM7QUFBQTtBQUFBLDRCQUVDLFNBQVE7QUFBQSw0QkFDUixPQUFPNU0sRUFBRTJHLGFBQWEsUUFBUSxTQUFTO0FBQUEsNEJBQ3ZDLE1BQUs7QUFBQSw0QkFFSjNHO0FBQUFBLGdDQUFFMkcsU0FBU3lHLFlBQVk7QUFBQSw4QkFBRTtBQUFBLDhCQUFHUixJQUFJO0FBQUE7QUFBQTtBQUFBLDBCQUw1QkE7QUFBQUEsMEJBRFA7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSx3QkFPQTtBQUFBLHNCQUNEO0FBQUEsc0JBQ0Q7QUFBQSx3QkFBQztBQUFBO0FBQUEsMEJBQ0MsTUFBSztBQUFBLDBCQUNMLFNBQVE7QUFBQSwwQkFDUixTQUFTLE1BQU0zRSxPQUFPOEYsUUFBUSxDQUFDL04sTUFBTWdOLFNBQVNoTixDQUFDLENBQUM7QUFBQSwwQkFBRTtBQUFBO0FBQUEsd0JBSHBEO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxzQkFNQTtBQUFBLHlCQXBCRjtBQUFBO0FBQUE7QUFBQTtBQUFBLDJCQXFCQTtBQUFBLHVCQXBDT29GLEdBQVg7QUFBQTtBQUFBO0FBQUE7QUFBQSx5QkFzQ0E7QUFBQSxnQkFFSixDQUFDO0FBQUEsZ0JBRUEyRSxXQUNDLHVCQUFDLFFBQUssWUFBVSxNQUFDLFNBQVEsTUFBSyxRQUFPLE1BQUssSUFBRyxVQUMzQztBQUFBLHlDQUFDLFNBQU0sS0FBSSxNQUFLLElBQUksR0FDbEI7QUFBQSwyQ0FBQyxVQUFPLE1BQUssUUFBYjtBQUFBO0FBQUE7QUFBQTtBQUFBLDJCQUFpQjtBQUFBLG9CQUNqQix1QkFBQyxTQUFNLE1BQUssTUFBSyxPQUFNLFNBQVEsb0JBQS9CO0FBQUE7QUFBQTtBQUFBO0FBQUEsMkJBQW1DO0FBQUEsdUJBRnJDO0FBQUE7QUFBQTtBQUFBO0FBQUEseUJBR0E7QUFBQSxrQkFDQSx1QkFBQyxRQUFLLE1BQUssTUFBSyxPQUFPLEVBQUUrRCxZQUFZLFdBQVcsR0FBSS9ELHFCQUFwRDtBQUFBO0FBQUE7QUFBQTtBQUFBLHlCQUE0RDtBQUFBLHFCQUw5RDtBQUFBO0FBQUE7QUFBQTtBQUFBLHVCQU1BO0FBQUE7QUFBQTtBQUFBLFlBL0VKO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxVQWlGQTtBQUFBLFVBRUMsQ0FBQ1MsY0FDQSx1QkFBQyxTQUFNLFNBQVEsVUFDYixpQ0FBQyxVQUFPLE1BQUssTUFBSyxTQUFRLFNBQVEsU0FBU1csZ0JBQWUseUJBQTFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsaUJBRUEsS0FIRjtBQUFBO0FBQUE7QUFBQTtBQUFBLGlCQUlBO0FBQUEsVUFFRDNLLFNBQVMsdUJBQUMsZ0JBQWEsT0FBTSxPQUFNLE9BQU0sTUFBSyxTQUFTLE1BQU1DLFNBQVMsSUFBSSxHQUFJRCxtQkFBckU7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFBMkU7QUFBQSxVQUNwRjJKLGNBQWMsdUJBQUMsZ0JBQWEsT0FBTSxTQUFRLE9BQU0sU0FBUSxTQUFTLE1BQU1DLGNBQWMsSUFBSSxHQUFJRCx3QkFBL0U7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFBMEY7QUFBQSxVQUV6Ryx1QkFBQyxTQUFNLEtBQUssR0FDVjtBQUFBO0FBQUEsY0FBQztBQUFBO0FBQUEsZ0JBQ0MsYUFBWTtBQUFBLGdCQUNaLE9BQU81RjtBQUFBQSxnQkFDUCxVQUFVLENBQUNyRCxNQUFNNEksU0FBUzVJLEVBQUVHLGNBQWN5QyxLQUFLO0FBQUEsZ0JBQy9DLFdBQVcsQ0FBQzVDLE1BQU07QUFDaEIsc0JBQUlBLEVBQUUyTCxRQUFRLFlBQVkzTCxFQUFFOE0sV0FBVzlNLEVBQUUrTSxTQUFVN0MsTUFBSztBQUFBLGdCQUMxRDtBQUFBLGdCQUNBO0FBQUEsZ0JBQ0EsU0FBUztBQUFBLGdCQUNULFNBQVM7QUFBQSxnQkFDVCxPQUFPLEVBQUVrQyxNQUFNLEVBQUU7QUFBQTtBQUFBLGNBVm5CO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxZQVVxQjtBQUFBLFlBRXJCLHVCQUFDLFVBQU8sU0FBU2xDLE1BQU0sU0FBU2hMLE1BQU0sVUFBVSxDQUFDbUUsTUFBTStELEtBQUssR0FBRSxxQkFBOUQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxtQkFFQTtBQUFBLGVBZkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFnQkE7QUFBQSxVQUNBLHVCQUFDLFFBQUssTUFBSyxNQUFLLEdBQUUsVUFBUyxrREFBM0I7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFBNkQ7QUFBQTtBQUFBO0FBQUEsTUF4SC9EO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxJQXlIQTtBQUFBO0FBRUo7QUFBQ3FCLElBL1NRSCxjQUFZO0FBQUEsTUFBWkE7QUFpVFQsU0FBUzBFLHFCQUFxQjtBQUFBQyxNQUFBO0FBRTVCLFFBQU1yTSxRQUFReEcsU0FBUyxFQUFFeUcsVUFBVSxDQUFDLE9BQU8sR0FBR0MsU0FBUzdGLElBQUlNLFlBQVksQ0FBQztBQUN4RSxRQUFNMlIsY0FBY3RNLE1BQU0vQyxNQUFNOEUsS0FBSyxDQUFDdEYsTUFBTUEsRUFBRXlGLFdBQVcsTUFBTSxHQUFHekIsaUJBQWlCO0FBQ25GLFFBQU0sQ0FBQ0wsUUFBUUMsU0FBUyxJQUFJckksU0FBd0IsSUFBSTtBQUN4RCxRQUFNdVUsYUFBYW5NLFVBQVVrTTtBQUM3QixRQUFNLENBQUNFLGdCQUFnQkMsaUJBQWlCLElBQUl6VSxTQUFTLENBQUM7QUFFdEQsU0FDRSx1QkFBQyxTQUFJLE9BQU8sRUFBRXNILFNBQVMsUUFBUXhCLFFBQVEsUUFBUUssT0FBTyxPQUFPLEdBQzNEO0FBQUEsMkJBQUMsU0FBSSxPQUFPLEVBQUVxTixNQUFNLFdBQVdrQixVQUFVLEtBQUs1TyxRQUFRLE9BQU8sR0FDM0QsaUNBQUMsY0FBVyxhQUFhME8sa0JBQXpCO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBd0MsS0FEMUM7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUVBO0FBQUEsSUFDQSx1QkFBQyxTQUFJLE9BQU8sRUFBRWhCLE1BQU0sV0FBV2tCLFVBQVUsS0FBS0MsVUFBVSxLQUFLN08sUUFBUSxRQUFROE8sWUFBWSxxQkFBcUJDLFlBQVksVUFBVSxHQUNsSSxpQ0FBQyxTQUFNLEdBQUcsR0FBRyxLQUFLLEdBQUcsT0FBTyxFQUFFL08sUUFBUSxPQUFPLEdBQzNDO0FBQUEsNkJBQUMsU0FBTSxHQUFFLE1BQUssS0FBSSxNQUFLLE9BQU0sVUFBUyxPQUFPLEVBQUVnUCxjQUFjLG9CQUFvQixHQUMvRTtBQUFBLCtCQUFDLFFBQUssTUFBSyxNQUFLLEdBQUUsVUFBUyx3QkFBM0I7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQUFtQztBQUFBLFFBQ25DO0FBQUEsVUFBQztBQUFBO0FBQUEsWUFDQyxNQUFLO0FBQUEsWUFDTCxPQUFPUDtBQUFBQSxZQUNQLE9BQU92TSxNQUFNL0MsUUFBUSxJQUFJRSxJQUFJLENBQUNWLE9BQU8sRUFBRXVGLE9BQU92RixFQUFFZ0UsZUFBZXdCLE9BQU94RixFQUFFaUIsS0FBSyxFQUFFO0FBQUEsWUFDL0UsVUFBVTJDO0FBQUFBLFlBQ1YsYUFBWTtBQUFBLFlBQ1osT0FBTyxFQUFFbUwsTUFBTSxFQUFFO0FBQUE7QUFBQSxVQU5uQjtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsUUFNcUI7QUFBQSxXQVJ2QjtBQUFBO0FBQUE7QUFBQTtBQUFBLGFBVUE7QUFBQSxNQUNBLHVCQUFDLFNBQUksT0FBTyxFQUFFQSxNQUFNLEdBQUdDLFdBQVcsRUFBRSxHQUNsQztBQUFBLFFBQUM7QUFBQTtBQUFBLFVBQ0MsY0FBY2M7QUFBQUEsVUFDZCxnQkFBZ0IsTUFBTUUsa0JBQWtCLENBQUNNLE1BQU1BLElBQUksQ0FBQztBQUFBO0FBQUEsUUFGdEQ7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLE1BRXdELEtBSDFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsYUFLQTtBQUFBLFNBakJGO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FrQkEsS0FuQkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQW9CQTtBQUFBLE9BeEJGO0FBQUE7QUFBQTtBQUFBO0FBQUEsU0F5QkE7QUFFSjtBQUFDVixJQXBDUUQsb0JBQWtCO0FBQUEsVUFFWDVTLFFBQVE7QUFBQTtBQUFBLE1BRmY0UztBQXNDVCxTQUFTWSxRQUFRO0FBQUFDLE1BQUE7QUFDZixRQUFNM1MsS0FBS2QsU0FBUyxFQUFFeUcsVUFBVSxDQUFDLElBQUksR0FBR0MsU0FBUzdGLElBQUlDLEdBQUcsQ0FBQztBQUN6RCxRQUFNNFMsTUFBTW5ULFlBQVk7QUFHeEIsUUFBTW9ULFlBQVlELElBQUlFLGFBQWEsT0FBT0YsSUFBSUUsYUFBYTtBQUMzRCxRQUFNLENBQUNDLFNBQVNDLFVBQVUsSUFBSXRWLFNBQVMsS0FBSztBQUM1QyxRQUFNdVYsZUFBZUosYUFBYSxDQUFDRTtBQUVuQyxTQUNFO0FBQUEsSUFBQztBQUFBO0FBQUEsTUFDQyxRQUFRLEVBQUV2UCxRQUFRLEdBQUc7QUFBQSxNQUNyQixRQUFRO0FBQUEsUUFDTkssT0FBTztBQUFBLFFBQ1BxUCxZQUFZO0FBQUEsUUFDWkMsV0FBVyxFQUFFQyxTQUFTSCxjQUFjSSxRQUFRSixhQUFhO0FBQUEsTUFDM0Q7QUFBQSxNQUNBLFNBQVM7QUFBQSxNQUVUO0FBQUEsK0JBQUMsU0FBUyxRQUFULEVBQ0MsaUNBQUMsU0FBTSxHQUFFLFFBQU8sSUFBRyxNQUFLLFNBQVEsaUJBQzlCO0FBQUEsaUNBQUMsU0FBTSxLQUFJLE1BQ1Q7QUFBQTtBQUFBLGNBQUM7QUFBQTtBQUFBLGdCQUNDLFFBQVEsQ0FBQ0E7QUFBQUEsZ0JBQ1QsU0FBUyxNQUFNRCxXQUFXLENBQUNNLE1BQU0sQ0FBQ0EsQ0FBQztBQUFBLGdCQUNuQyxNQUFLO0FBQUEsZ0JBQ0wsY0FBVztBQUFBO0FBQUEsY0FKYjtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsWUFJc0I7QUFBQSxZQUV0Qix1QkFBQyxTQUFNLE9BQU8sR0FBRyxvQ0FBakI7QUFBQTtBQUFBO0FBQUE7QUFBQSxtQkFBcUM7QUFBQSxlQVB2QztBQUFBO0FBQUE7QUFBQTtBQUFBLGlCQVFBO0FBQUEsVUFDQ3RULEdBQUcyQyxRQUNGLHVCQUFDLFNBQU0sS0FBSSxNQUNUO0FBQUEsbUNBQUMsUUFBSyxNQUFLLE1BQUssR0FBRSxVQUFVM0MsYUFBRzJDLEtBQUtxSSxnQkFBZ0JoTCxHQUFHMkMsS0FBSzRRLFNBQTVEO0FBQUE7QUFBQTtBQUFBO0FBQUEsbUJBQWtFO0FBQUEsWUFDakV2VCxHQUFHMkMsS0FBSzZRLE1BQU0zUTtBQUFBQSxjQUFJLENBQUMxQyxNQUNsQix1QkFBQyxTQUFjLFNBQVEsU0FBU0EsZUFBcEJBLEdBQVo7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBa0M7QUFBQSxZQUNuQztBQUFBLGVBSkg7QUFBQTtBQUFBO0FBQUE7QUFBQSxpQkFLQTtBQUFBLGFBaEJKO0FBQUE7QUFBQTtBQUFBO0FBQUEsZUFrQkEsS0FuQkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxlQW9CQTtBQUFBLFFBQ0EsdUJBQUMsU0FBUyxRQUFULEVBQWdCLEdBQUUsTUFDakI7QUFBQTtBQUFBLFlBQUM7QUFBQTtBQUFBLGNBQ0MsV0FBV2I7QUFBQUEsY0FDWCxJQUFHO0FBQUEsY0FDSCxPQUFNO0FBQUEsY0FDTixTQUFTLE1BQU0wVCxXQUFXLEtBQUs7QUFBQTtBQUFBLFlBSmpDO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxVQUltQztBQUFBLFVBRW5DO0FBQUEsWUFBQztBQUFBO0FBQUEsY0FDQyxXQUFXMVQ7QUFBQUEsY0FDWCxJQUFHO0FBQUEsY0FDSCxPQUFNO0FBQUEsY0FDTixTQUFTLE1BQU0wVCxXQUFXLElBQUk7QUFBQTtBQUFBLFlBSmhDO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxVQUlrQztBQUFBLFVBRWxDO0FBQUEsWUFBQztBQUFBO0FBQUEsY0FDQyxXQUFXMVQ7QUFBQUEsY0FDWCxJQUFHO0FBQUEsY0FDSCxPQUFNO0FBQUEsY0FDTixTQUFTLE1BQU0wVCxXQUFXLElBQUk7QUFBQTtBQUFBLFlBSmhDO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQSxVQUlrQztBQUFBLGFBakJwQztBQUFBO0FBQUE7QUFBQTtBQUFBLGVBbUJBO0FBQUEsUUFDQTtBQUFBLFVBQUMsU0FBUztBQUFBLFVBQVQ7QUFBQSxZQUNDLE9BQU87QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLGNBS0xTLFNBQVNaLFlBQVksZUFBZTtBQUFBLGNBQ3BDclAsUUFBUTtBQUFBLGNBQ1JrUSxXQUFXO0FBQUEsY0FDWHpDLFVBQVU0QixZQUFZLFdBQVc7QUFBQSxZQUNuQztBQUFBLFlBRUEsaUNBQUMsVUFDQztBQUFBLHFDQUFDLFNBQU0sTUFBSyxLQUFJLFNBQVMsdUJBQUMsd0JBQUQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBbUIsS0FBNUM7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBZ0Q7QUFBQSxjQUNoRCx1QkFBQyxTQUFNLE1BQUssUUFBTyxTQUFTLHVCQUFDLGlCQUFEO0FBQUE7QUFBQTtBQUFBO0FBQUEscUJBQVksS0FBeEM7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBNEM7QUFBQSxjQUM1Qyx1QkFBQyxTQUFNLE1BQUssY0FBYSxTQUFTLHVCQUFDLGtCQUFEO0FBQUE7QUFBQTtBQUFBO0FBQUEscUJBQWEsS0FBL0M7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBbUQ7QUFBQSxjQUNuRCx1QkFBQyxTQUFNLE1BQUssa0JBQWlCLFNBQVMsdUJBQUMsb0JBQUQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxxQkFBZSxLQUFyRDtBQUFBO0FBQUE7QUFBQTtBQUFBLHFCQUF5RDtBQUFBLGlCQUozRDtBQUFBO0FBQUE7QUFBQTtBQUFBLG1CQUtBO0FBQUE7QUFBQSxVQWpCRjtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUEsUUFrQkE7QUFBQTtBQUFBO0FBQUEsSUFwRUY7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBO0FBQUE7QUFBQTtBQUFBLEVBcUVBO0FBRUo7QUFBQ0YsSUFqRlFELE9BQUs7QUFBQSxVQUNEeFQsVUFDQ08sV0FBVztBQUFBO0FBQUEsTUFGaEJpVDtBQW1GVC9VLFNBQVNnVyxXQUFXQyxTQUFTQyxlQUFlLE1BQU0sQ0FBRSxFQUFFQztBQUFBQSxFQUNwRCx1QkFBQyxtQkFDQyxpQ0FBQyx1QkFBb0IsUUFBUW5VLGFBQzNCLGlDQUFDLGlCQUFjLFVBQVMsWUFDdEIsaUNBQUMsV0FBRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFNBQU0sS0FEUjtBQUFBO0FBQUE7QUFBQTtBQUFBLFNBRUEsS0FIRjtBQUFBO0FBQUE7QUFBQTtBQUFBLFNBSUEsS0FMRjtBQUFBO0FBQUE7QUFBQTtBQUFBLFNBTUE7QUFDRjtBQUFFLElBQUFvVSxJQUFBQyxLQUFBQyxLQUFBQyxLQUFBQyxLQUFBQyxLQUFBQyxLQUFBQyxLQUFBQztBQUFBLGFBQUFSLElBQUE7QUFBQSxhQUFBQyxLQUFBO0FBQUEsYUFBQUMsS0FBQTtBQUFBLGFBQUFDLEtBQUE7QUFBQSxhQUFBQyxLQUFBO0FBQUEsYUFBQUMsS0FBQTtBQUFBLGFBQUFDLEtBQUE7QUFBQSxhQUFBQyxLQUFBO0FBQUEsYUFBQUMsS0FBQSIsIm5hbWVzIjpbInVzZUVmZmVjdCIsInVzZU1lbW8iLCJ1c2VSZWYiLCJ1c2VTdGF0ZSIsIlJlYWN0RE9NIiwiQXBwU2hlbGwiLCJCYWRnZSIsIkJ1cmdlciIsIkJ1dHRvbiIsIkNhcmQiLCJDb2RlIiwiR3JvdXAiLCJMb2FkZXIiLCJNYW50aW5lUHJvdmlkZXIiLCJOYXZMaW5rIiwiTm90aWZpY2F0aW9uIiwiU2Nyb2xsQXJlYSIsIlNlbGVjdCIsIlN0YWNrIiwiVGFibGUiLCJUYWJzIiwiVGV4dCIsIlRleHRhcmVhIiwiVGl0bGUiLCJRdWVyeUNsaWVudCIsIlF1ZXJ5Q2xpZW50UHJvdmlkZXIiLCJ1c2VNdXRhdGlvbiIsInVzZVF1ZXJ5IiwidXNlUXVlcnlDbGllbnQiLCJQbG90IiwiQnJvd3NlclJvdXRlciIsIkxpbmsiLCJSb3V0ZSIsIlJvdXRlcyIsInVzZUxvY2F0aW9uIiwidXNlUGFyYW1zIiwicXVlcnlDbGllbnQiLCJkZWZhdWx0T3B0aW9ucyIsInF1ZXJpZXMiLCJyZWZldGNoT25XaW5kb3dGb2N1cyIsImFwaSIsIm1lIiwiZmV0Y2giLCJ0aGVuIiwiciIsImpzb24iLCJjb25uZWN0aW9ucyIsInNjaGVtYSIsImlkIiwicnVuUXVlcnkiLCJib2R5IiwibWV0aG9kIiwiaGVhZGVycyIsIkpTT04iLCJzdHJpbmdpZnkiLCJwYXJhbXMiLCJvayIsIkVycm9yIiwic3RhdHVzIiwic3RhdHVzVGV4dCIsIndvcmtzcGFjZXMiLCJub3RlYm9va3MiLCJsYXRlc3ROb3RlYm9vayIsInNhdmVOb3RlYm9vayIsIlNBTVBMRV9TUUwiLCJzYWxlc19kYiIsImNybV9teXNxbCIsIndhcmVob3VzZV9oaXZlIiwiQ2hhcnRQaWNrZXIiLCJyZXN1bHQiLCJfcyIsImNoYXJ0VHlwZSIsInNldENoYXJ0VHlwZSIsIm51bWVyaWNDb2xzIiwiY29sdW1ucyIsImZpbHRlciIsImMiLCJyb3dzIiwiZXZlcnkiLCJ4Iiwic2V0WCIsInkiLCJzZXRZIiwiaW5jbHVkZXMiLCJkYXRhIiwieHMiLCJtYXAiLCJ5cyIsInR5cGUiLCJsYWJlbHMiLCJ2YWx1ZXMiLCJtb2RlIiwiZmlsbCIsIm5hbWUiLCJ6IiwidiIsImF1dG9zaXplIiwiaGVpZ2h0IiwibWFyZ2luIiwibCIsInQiLCJiIiwid2lkdGgiLCJGaWxlVXBsb2FkQ2FyZCIsIl9zMiIsImJ1c3kiLCJzZXRCdXN5IiwibGFzdCIsInNldExhc3QiLCJlcnJvciIsInNldEVycm9yIiwib25GaWxlcyIsImZpbGVzIiwibGVuZ3RoIiwiZm9ybSIsIkZvcm1EYXRhIiwiYXBwZW5kIiwiY2F0Y2giLCJkZXRhaWwiLCJlIiwibWVzc2FnZSIsImRpc3BsYXkiLCJjdXJyZW50VGFyZ2V0Iiwic2FmZV9uYW1lIiwiTWF0aCIsInJvdW5kIiwic2l6ZV9ieXRlcyIsImhpbnQiLCJRdWVyeUVkaXRvciIsIl9zMyIsInFjIiwiY29ubnMiLCJxdWVyeUtleSIsInF1ZXJ5Rm4iLCJuYnMiLCJjb25uSWQiLCJzZXRDb25uSWQiLCJzcWwiLCJzZXRTcWwiLCJmaXJzdCIsImNvbm5lY3Rpb25faWQiLCJlbmFibGVkIiwicnVuIiwibXV0YXRpb25GbiIsInNhdmUiLCJjb250ZW50IiwidGl0bGUiLCJjZWxscyIsImtpbmQiLCJwcmV2aWV3X3Jvd3MiLCJzbGljZSIsIkJvb2xlYW4iLCJzYXZlZF9hdCIsIkRhdGUiLCJ0b0lTT1N0cmluZyIsIm5vdGVib29rX2lkIiwic2F2ZWRfYnkiLCJ1c2VyX2lkIiwiY29tbWl0X21lc3NhZ2UiLCJvblN1Y2Nlc3MiLCJpbnZhbGlkYXRlUXVlcmllcyIsImlzTG9hZGluZyIsImZpbmQiLCJ2YWx1ZSIsImxhYmVsIiwiZW5naW5lIiwidGFibGVzIiwiY29sTmFtZXMiLCJqb2luIiwicXVhbGlmaWVkIiwiY3Vyc29yIiwicGlpX2tpbmQiLCJpbnB1dCIsImZvbnRGYW1pbHkiLCJmb250U2l6ZSIsImlzUGVuZGluZyIsIm11dGF0ZSIsImlzU3VjY2VzcyIsIlN0cmluZyIsInZlcnNpb25faWQiLCJyb3dfY291bnQiLCJleGVjdXRlZF9hdCIsImFjdGl2ZV9waWlfcGF0dGVybnMiLCJwIiwicm93IiwiaSIsIk5vdGVib29rTGlzdCIsIl9zNCIsIm5iIiwicGF0aCIsImxhdGVzdF9zYXZlZF9hdCIsInRvTG9jYWxlU3RyaW5nIiwibGF0ZXN0X3ZlcnNpb24iLCJOb3RlYm9va0RldGFpbCIsIl9zNSIsIm1hcmdpblRvcCIsIkp1cHl0ZXJMYWIiLCJyZWxvYWRUb2tlbiIsIl9zNiIsImxvYWRpbmciLCJzZXRMb2FkaW5nIiwic3JjIiwiYm9yZGVyIiwidHJhbnNpdGlvbiIsIm9wYWNpdHkiLCJDT1BJTE9UX05PVEVCT09LIiwiSlVQWVRFUl9UT0tFTiIsImFwcGVuZENlbGxUb0NvcGlsb3ROb3RlYm9vayIsImxhbmd1YWdlIiwic291cmNlIiwidXJsIiwiQXV0aG9yaXphdGlvbiIsIm5vdGVib29rIiwiaGVhZCIsImNyZWRlbnRpYWxzIiwibWV0YWRhdGEiLCJrZXJuZWxzcGVjIiwiZGlzcGxheV9uYW1lIiwibmJmb3JtYXQiLCJuYmZvcm1hdF9taW5vciIsImZvcm1hdCIsImNlbGwiLCJjZWxsX3R5cGUiLCJjb3BpbG90X2dlbmVyYXRlZCIsIm91dHB1dHMiLCJleGVjdXRpb25fY291bnQiLCJwdXNoIiwicHV0Iiwic3BsaXRNYXJrZG93bkNvZGVCbG9ja3MiLCJ0ZXh0IiwiYmxvY2tzIiwicmUiLCJtIiwiZXhlYyIsInRvTG93ZXJDYXNlIiwidHJpbSIsInN0cmlwQ29kZUZlbmNlcyIsInJlcGxhY2UiLCJmZXRjaE5vdGVib29rQ29udGV4dCIsImN0cmwiLCJBYm9ydENvbnRyb2xsZXIiLCJ0aW1lciIsIndpbmRvdyIsInNldFRpbWVvdXQiLCJhYm9ydCIsInNpZ25hbCIsInByb21wdCIsImNlbGxDb3VudCIsImNvZGVDZWxscyIsIkFycmF5IiwiaXNBcnJheSIsInMiLCJjbGVhclRpbWVvdXQiLCJDb3BpbG90UGFuZWwiLCJjb25uZWN0aW9uSWQiLCJvbkNlbGxJbnNlcnRlZCIsIl9zNyIsImhpc3RvcnkiLCJzZXRIaXN0b3J5Iiwic2V0SW5wdXQiLCJwZW5kaW5nIiwic2V0UGVuZGluZyIsInByb3ZpZGVyTmFtZSIsInNldFByb3ZpZGVyTmFtZSIsImxhc3RJbnNlcnQiLCJzZXRMYXN0SW5zZXJ0IiwiaW5zZXJ0ZWRSZWYiLCJTZXQiLCJjaGF0UmVmIiwiYXV0b0ZvbGxvdyIsInNldEF1dG9Gb2xsb3ciLCJqIiwicHJvdmlkZXIiLCJlbCIsImN1cnJlbnQiLCJzY3JvbGxUb3AiLCJzY3JvbGxIZWlnaHQiLCJvbkNoYXRTY3JvbGwiLCJhdEJvdHRvbSIsImNsaWVudEhlaWdodCIsInNjcm9sbFRvTGF0ZXN0Iiwic2VuZCIsInF1ZXN0aW9uIiwiaCIsInJvbGUiLCJuYlByb21wdCIsImF1Z21lbnRlZFF1ZXN0aW9uIiwicmVzIiwicmVhZGVyIiwiZ2V0UmVhZGVyIiwiZGVjIiwiVGV4dERlY29kZXIiLCJidWYiLCJhc3NlbWJsZWQiLCJkb25lIiwicmVhZCIsImRlY29kZSIsInN0cmVhbSIsIm5sIiwiaW5kZXhPZiIsImxpbmUiLCJvYmoiLCJwYXJzZSIsImNodW5rIiwiYXNzaXN0YW50SWR4IiwiayIsImtleSIsImhhcyIsImFkZCIsIm9uSW5zZXJ0IiwiYmxvY2siLCJub3RlYm9va19wYXRoIiwic291cmNlX2xlbmd0aCIsInRvVXBwZXJDYXNlIiwib3ZlcmZsb3ciLCJmbGV4IiwibWluSGVpZ2h0Iiwib3ZlcmZsb3dZIiwicGFkZGluZ1JpZ2h0IiwiZmxleERpcmVjdGlvbiIsImdhcCIsInBvc2l0aW9uIiwibmFycmF0aW9uIiwid2hpdGVTcGFjZSIsImZvckVhY2giLCJjdHJsS2V5IiwibWV0YUtleSIsIkp1cHl0ZXJXaXRoQ29waWxvdCIsIl9zOCIsImRlZmF1bHRDb25uIiwiYWN0aXZlQ29ubiIsImxhYlJlbG9hZFRva2VuIiwic2V0TGFiUmVsb2FkVG9rZW4iLCJtaW5XaWR0aCIsIm1heFdpZHRoIiwiYm9yZGVyTGVmdCIsImJhY2tncm91bmQiLCJib3JkZXJCb3R0b20iLCJuIiwiU2hlbGwiLCJfczkiLCJsb2MiLCJpc0p1cHl0ZXIiLCJwYXRobmFtZSIsIm5hdk9wZW4iLCJzZXROYXZPcGVuIiwibmF2Q29sbGFwc2VkIiwiYnJlYWtwb2ludCIsImNvbGxhcHNlZCIsImRlc2t0b3AiLCJtb2JpbGUiLCJvIiwiZW1haWwiLCJyb2xlcyIsInBhZGRpbmciLCJib3hTaXppbmciLCJjcmVhdGVSb290IiwiZG9jdW1lbnQiLCJnZXRFbGVtZW50QnlJZCIsInJlbmRlciIsIl9jIiwiX2MyIiwiX2MzIiwiX2M0IiwiX2M1IiwiX2M2IiwiX2M3IiwiX2M4IiwiX2M5Il0sImlnbm9yZUxpc3QiOltdLCJzb3VyY2VzIjpbIm1haW4udHN4Il0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IHVzZUVmZmVjdCwgdXNlTWVtbywgdXNlUmVmLCB1c2VTdGF0ZSB9IGZyb20gJ3JlYWN0JztcbmltcG9ydCBSZWFjdERPTSBmcm9tICdyZWFjdC1kb20vY2xpZW50JztcbmltcG9ydCB7XG4gIEFwcFNoZWxsLFxuICBCYWRnZSxcbiAgQnVyZ2VyLFxuICBCdXR0b24sXG4gIENhcmQsXG4gIENvZGUsXG4gIEdyb3VwLFxuICBMb2FkZXIsXG4gIE1hbnRpbmVQcm92aWRlcixcbiAgTmF2TGluayxcbiAgTm90aWZpY2F0aW9uLFxuICBTY3JvbGxBcmVhLFxuICBTZWxlY3QsXG4gIFN0YWNrLFxuICBUYWJsZSxcbiAgVGFicyxcbiAgVGV4dCxcbiAgVGV4dElucHV0LFxuICBUZXh0YXJlYSxcbiAgVGl0bGUsXG59IGZyb20gJ0BtYW50aW5lL2NvcmUnO1xuaW1wb3J0IHsgUXVlcnlDbGllbnQsIFF1ZXJ5Q2xpZW50UHJvdmlkZXIsIHVzZU11dGF0aW9uLCB1c2VRdWVyeSwgdXNlUXVlcnlDbGllbnQgfSBmcm9tICdAdGFuc3RhY2svcmVhY3QtcXVlcnknO1xuaW1wb3J0IFBsb3QgZnJvbSAncmVhY3QtcGxvdGx5LmpzJztcbmltcG9ydCB7XG4gIEJyb3dzZXJSb3V0ZXIsXG4gIExpbmssXG4gIFJvdXRlLFxuICBSb3V0ZXMsXG4gIHVzZUxvY2F0aW9uLFxuICB1c2VOYXZpZ2F0ZSxcbiAgdXNlUGFyYW1zLFxufSBmcm9tICdyZWFjdC1yb3V0ZXItZG9tJztcbmltcG9ydCAnQG1hbnRpbmUvY29yZS9zdHlsZXMuY3NzJztcblxuY29uc3QgcXVlcnlDbGllbnQgPSBuZXcgUXVlcnlDbGllbnQoe1xuICBkZWZhdWx0T3B0aW9uczogeyBxdWVyaWVzOiB7IHJlZmV0Y2hPbldpbmRvd0ZvY3VzOiBmYWxzZSB9IH0sXG59KTtcblxudHlwZSBDb25uZWN0aW9uID0ge1xuICBjb25uZWN0aW9uX2lkOiBzdHJpbmc7XG4gIG5hbWU6IHN0cmluZztcbiAgZW5naW5lOiBzdHJpbmc7XG4gIGhvc3Q6IHN0cmluZztcbiAgcG9ydDogbnVtYmVyO1xuICBkYXRhYmFzZTogc3RyaW5nIHwgbnVsbDtcbn07XG5cbnR5cGUgU2NoZW1hQ29sdW1uID0geyBuYW1lOiBzdHJpbmc7IHR5cGU6IHN0cmluZzsgcGlpX2tpbmQ6IHN0cmluZyB8IG51bGwgfTtcbnR5cGUgU2NoZW1hID0ge1xuICBjb25uZWN0aW9uX2lkOiBzdHJpbmc7XG4gIG5hbWU6IHN0cmluZztcbiAgdGFibGVzOiB7IHNjaGVtYT86IHN0cmluZzsgbmFtZTogc3RyaW5nOyBjb2x1bW5zOiBTY2hlbWFDb2x1bW5bXSB9W107XG59O1xuXG50eXBlIFJvdyA9IFJlY29yZDxzdHJpbmcsIHVua25vd24+O1xudHlwZSBRdWVyeVJlc3VsdCA9IHtcbiAgY29ubmVjdGlvbjogc3RyaW5nO1xuICBlbmdpbmU6IHN0cmluZztcbiAgc3FsOiBzdHJpbmc7XG4gIGNvbHVtbnM6IHN0cmluZ1tdO1xuICByb3dzOiBSb3dbXTtcbiAgcm93X2NvdW50OiBudW1iZXI7XG4gIGFjdGl2ZV9waWlfcGF0dGVybnM6IHN0cmluZ1tdO1xuICBleGVjdXRlZF9hdDogc3RyaW5nO1xufTtcblxudHlwZSBOb3RlYm9vayA9IHtcbiAgbm90ZWJvb2tfaWQ6IHN0cmluZztcbiAgd29ya3NwYWNlX2lkOiBzdHJpbmc7XG4gIHBhdGg6IHN0cmluZztcbiAgbGF0ZXN0X3ZlcnNpb246IHN0cmluZyB8IG51bGw7XG4gIGxhdGVzdF9zYXZlZF9hdDogc3RyaW5nIHwgbnVsbDtcbn07XG5cbnR5cGUgV29ya3NwYWNlID0ge1xuICB3b3Jrc3BhY2VfaWQ6IHN0cmluZztcbiAgbmFtZTogc3RyaW5nO1xuICBraW5kOiBzdHJpbmc7XG4gIGdpdF9yZXBvX3VybDogc3RyaW5nO1xuICBnaXRfYnJhbmNoOiBzdHJpbmc7XG59O1xuXG50eXBlIE1lID0ge1xuICB1c2VyX2lkOiBzdHJpbmc7XG4gIGVtYWlsOiBzdHJpbmc7XG4gIGRpc3BsYXlfbmFtZTogc3RyaW5nIHwgbnVsbDtcbiAgcm9sZXM6IHN0cmluZ1tdO1xufTtcblxuY29uc3QgYXBpID0ge1xuICBtZTogKCkgPT4gZmV0Y2goJy9hcGkvYXV0aC9tZScpLnRoZW4oKHIpID0+IHIuanNvbigpIGFzIFByb21pc2U8TWU+KSxcbiAgY29ubmVjdGlvbnM6ICgpID0+IGZldGNoKCcvYXBpL2Nvbm5lY3Rpb25zJykudGhlbigocikgPT4gci5qc29uKCkgYXMgUHJvbWlzZTxDb25uZWN0aW9uW10+KSxcbiAgc2NoZW1hOiAoaWQ6IHN0cmluZykgPT5cbiAgICBmZXRjaChgL2FwaS9jb25uZWN0aW9ucy8ke2lkfS9zY2hlbWFgKS50aGVuKChyKSA9PiByLmpzb24oKSBhcyBQcm9taXNlPFNjaGVtYT4pLFxuICBydW5RdWVyeTogKGJvZHk6IHsgY29ubmVjdGlvbl9pZDogc3RyaW5nOyBzcWw6IHN0cmluZyB9KSA9PlxuICAgIGZldGNoKCcvYXBpL3F1ZXJpZXMvZXhlY3V0ZScsIHtcbiAgICAgIG1ldGhvZDogJ1BPU1QnLFxuICAgICAgaGVhZGVyczogeyAnQ29udGVudC1UeXBlJzogJ2FwcGxpY2F0aW9uL2pzb24nIH0sXG4gICAgICBib2R5OiBKU09OLnN0cmluZ2lmeSh7IC4uLmJvZHksIHBhcmFtczoge30gfSksXG4gICAgfSkudGhlbihhc3luYyAocikgPT4ge1xuICAgICAgaWYgKCFyLm9rKSB0aHJvdyBuZXcgRXJyb3IoYCR7ci5zdGF0dXN9ICR7ci5zdGF0dXNUZXh0fWApO1xuICAgICAgcmV0dXJuIHIuanNvbigpIGFzIFByb21pc2U8UXVlcnlSZXN1bHQ+O1xuICAgIH0pLFxuICB3b3Jrc3BhY2VzOiAoKSA9PiBmZXRjaCgnL2FwaS93b3Jrc3BhY2VzJykudGhlbigocikgPT4gci5qc29uKCkgYXMgUHJvbWlzZTxXb3Jrc3BhY2VbXT4pLFxuICBub3RlYm9va3M6ICgpID0+IGZldGNoKCcvYXBpL25vdGVib29rcycpLnRoZW4oKHIpID0+IHIuanNvbigpIGFzIFByb21pc2U8Tm90ZWJvb2tbXT4pLFxuICBsYXRlc3ROb3RlYm9vazogKGlkOiBzdHJpbmcpID0+XG4gICAgZmV0Y2goYC9hcGkvbm90ZWJvb2tzLyR7aWR9L2xhdGVzdGApLnRoZW4oKHIpID0+IHIuanNvbigpKSxcbiAgc2F2ZU5vdGVib29rOiAoaWQ6IHN0cmluZywgYm9keTogeyBjb250ZW50OiB1bmtub3duOyBzYXZlZF9ieTogc3RyaW5nOyBjb21taXRfbWVzc2FnZTogc3RyaW5nIH0pID0+XG4gICAgZmV0Y2goYC9hcGkvbm90ZWJvb2tzLyR7aWR9L3ZlcnNpb25zYCwge1xuICAgICAgbWV0aG9kOiAnUE9TVCcsXG4gICAgICBoZWFkZXJzOiB7ICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbicgfSxcbiAgICAgIGJvZHk6IEpTT04uc3RyaW5naWZ5KGJvZHkpLFxuICAgIH0pLnRoZW4oYXN5bmMgKHIpID0+IHtcbiAgICAgIGlmICghci5vaykgdGhyb3cgbmV3IEVycm9yKGAke3Iuc3RhdHVzfSAke3Iuc3RhdHVzVGV4dH1gKTtcbiAgICAgIHJldHVybiByLmpzb24oKTtcbiAgICB9KSxcbn07XG5cbmNvbnN0IFNBTVBMRV9TUUw6IFJlY29yZDxzdHJpbmcsIHN0cmluZz4gPSB7XG4gIHNhbGVzX2RiOiAnU0VMRUNUIG5hbWUsIGVtYWlsLCBwaG9uZSwgcnJuLCBjaXR5IEZST00gc2FsZXMuY3VzdG9tZXJzIExJTUlUIDI1JyxcbiAgY3JtX215c3FsOiAnU0VMRUNUIGxlYWRfbmFtZSwgZW1haWwsIHN0YWdlIEZST00gbGVhZHMgTElNSVQgMjUnLFxuICB3YXJlaG91c2VfaGl2ZTogJ1NFTEVDVCBldmVudF9kYXRlLCBjaGFubmVsLCByZXZlbnVlIEZST00gZXZlbnRzX2RhaWx5IExJTUlUIDMwJyxcbn07XG5cbmZ1bmN0aW9uIENoYXJ0UGlja2VyKHsgcmVzdWx0IH06IHsgcmVzdWx0OiBRdWVyeVJlc3VsdCB9KSB7XG4gIGNvbnN0IFtjaGFydFR5cGUsIHNldENoYXJ0VHlwZV0gPSB1c2VTdGF0ZTwnbGluZScgfCAnYmFyJyB8ICdzY2F0dGVyJyB8ICdwaWUnIHwgJ2FyZWEnIHwgJ2JveCcgfCAnaGVhdG1hcCc+KCdiYXInKTtcbiAgY29uc3QgbnVtZXJpY0NvbHMgPSByZXN1bHQuY29sdW1ucy5maWx0ZXIoKGMpID0+XG4gICAgcmVzdWx0LnJvd3MuZXZlcnkoKHIpID0+IHR5cGVvZiByW2NdID09PSAnbnVtYmVyJylcbiAgKTtcbiAgY29uc3QgW3gsIHNldFhdID0gdXNlU3RhdGU8c3RyaW5nPihyZXN1bHQuY29sdW1uc1swXSk7XG4gIGNvbnN0IFt5LCBzZXRZXSA9IHVzZVN0YXRlPHN0cmluZz4obnVtZXJpY0NvbHNbMF0gPz8gcmVzdWx0LmNvbHVtbnNbMV0gPz8gcmVzdWx0LmNvbHVtbnNbMF0pO1xuXG4gIHVzZUVmZmVjdCgoKSA9PiB7XG4gICAgaWYgKCFyZXN1bHQuY29sdW1ucy5pbmNsdWRlcyh4KSkgc2V0WChyZXN1bHQuY29sdW1uc1swXSk7XG4gICAgaWYgKCFyZXN1bHQuY29sdW1ucy5pbmNsdWRlcyh5KSkgc2V0WShudW1lcmljQ29sc1swXSA/PyByZXN1bHQuY29sdW1uc1sxXSA/PyByZXN1bHQuY29sdW1uc1swXSk7XG4gIH0sIFtyZXN1bHQuY29sdW1uc10pO1xuXG4gIGNvbnN0IGRhdGEgPSB1c2VNZW1vKCgpID0+IHtcbiAgICBjb25zdCB4cyA9IHJlc3VsdC5yb3dzLm1hcCgocikgPT4gclt4XSBhcyBzdHJpbmcgfCBudW1iZXIpO1xuICAgIGNvbnN0IHlzID0gcmVzdWx0LnJvd3MubWFwKChyKSA9PiByW3ldIGFzIG51bWJlcik7XG4gICAgaWYgKGNoYXJ0VHlwZSA9PT0gJ3BpZScpIHtcbiAgICAgIHJldHVybiBbeyB0eXBlOiAncGllJyBhcyBjb25zdCwgbGFiZWxzOiB4cywgdmFsdWVzOiB5cyB9XTtcbiAgICB9XG4gICAgaWYgKGNoYXJ0VHlwZSA9PT0gJ2xpbmUnIHx8IGNoYXJ0VHlwZSA9PT0gJ3NjYXR0ZXInIHx8IGNoYXJ0VHlwZSA9PT0gJ2FyZWEnKSB7XG4gICAgICByZXR1cm4gW1xuICAgICAgICB7XG4gICAgICAgICAgdHlwZTogJ3NjYXR0ZXInIGFzIGNvbnN0LFxuICAgICAgICAgIG1vZGU6IGNoYXJ0VHlwZSA9PT0gJ3NjYXR0ZXInID8gJ21hcmtlcnMnIDogJ2xpbmVzJyxcbiAgICAgICAgICBmaWxsOiBjaGFydFR5cGUgPT09ICdhcmVhJyA/ICd0b3plcm95JyA6ICdub25lJyxcbiAgICAgICAgICB4OiB4cyxcbiAgICAgICAgICB5OiB5cyxcbiAgICAgICAgfSxcbiAgICAgIF07XG4gICAgfVxuICAgIGlmIChjaGFydFR5cGUgPT09ICdiYXInKSB7XG4gICAgICByZXR1cm4gW3sgdHlwZTogJ2JhcicgYXMgY29uc3QsIHg6IHhzLCB5OiB5cyB9XTtcbiAgICB9XG4gICAgaWYgKGNoYXJ0VHlwZSA9PT0gJ2JveCcpIHtcbiAgICAgIHJldHVybiBbeyB0eXBlOiAnYm94JyBhcyBjb25zdCwgeTogeXMsIG5hbWU6IHkgfV07XG4gICAgfVxuICAgIHJldHVybiBbeyB0eXBlOiAnaGVhdG1hcCcgYXMgY29uc3QsIHo6IFt5c10gfV07XG4gIH0sIFtjaGFydFR5cGUsIHgsIHksIHJlc3VsdC5yb3dzXSk7XG5cbiAgcmV0dXJuIChcbiAgICA8U3RhY2s+XG4gICAgICA8R3JvdXA+XG4gICAgICAgIDxTZWxlY3RcbiAgICAgICAgICBsYWJlbD1cIuywqO2KuCDsooXrpZhcIlxuICAgICAgICAgIHZhbHVlPXtjaGFydFR5cGV9XG4gICAgICAgICAgb25DaGFuZ2U9eyh2KSA9PiB2ICYmIHNldENoYXJ0VHlwZSh2IGFzIHR5cGVvZiBjaGFydFR5cGUpfVxuICAgICAgICAgIGRhdGE9e1snbGluZScsICdiYXInLCAnc2NhdHRlcicsICdwaWUnLCAnYXJlYScsICdib3gnLCAnaGVhdG1hcCddfVxuICAgICAgICAgIHc9ezE0MH1cbiAgICAgICAgLz5cbiAgICAgICAgPFNlbGVjdCBsYWJlbD1cIlgg7LaVXCIgdmFsdWU9e3h9IG9uQ2hhbmdlPXsodikgPT4gdiAmJiBzZXRYKHYpfSBkYXRhPXtyZXN1bHQuY29sdW1uc30gdz17MTgwfSAvPlxuICAgICAgICA8U2VsZWN0IGxhYmVsPVwiWSDstpVcIiB2YWx1ZT17eX0gb25DaGFuZ2U9eyh2KSA9PiB2ICYmIHNldFkodil9IGRhdGE9e3Jlc3VsdC5jb2x1bW5zfSB3PXsxODB9IC8+XG4gICAgICA8L0dyb3VwPlxuICAgICAgPFBsb3RcbiAgICAgICAgZGF0YT17ZGF0YSBhcyBhbnl9XG4gICAgICAgIGxheW91dD17eyBhdXRvc2l6ZTogdHJ1ZSwgaGVpZ2h0OiAzNjAsIG1hcmdpbjogeyBsOiA1MCwgcjogMjAsIHQ6IDMwLCBiOiA2MCB9IH19XG4gICAgICAgIHN0eWxlPXt7IHdpZHRoOiAnMTAwJScgfX1cbiAgICAgIC8+XG4gICAgPC9TdGFjaz5cbiAgKTtcbn1cblxudHlwZSBVcGxvYWRSZXN1bHQgPSB7XG4gIGZpbGVfaWQ6IHN0cmluZztcbiAgc2FmZV9uYW1lOiBzdHJpbmc7XG4gIHNpemVfYnl0ZXM6IG51bWJlcjtcbiAga2luZDogc3RyaW5nO1xuICBtaW1lOiBzdHJpbmc7XG4gIGp1cHl0ZXJfcGF0aDogc3RyaW5nO1xuICBoaW50OiBzdHJpbmc7XG59O1xuXG5mdW5jdGlvbiBGaWxlVXBsb2FkQ2FyZCgpIHtcbiAgY29uc3QgW2J1c3ksIHNldEJ1c3ldID0gdXNlU3RhdGUoZmFsc2UpO1xuICBjb25zdCBbbGFzdCwgc2V0TGFzdF0gPSB1c2VTdGF0ZTxVcGxvYWRSZXN1bHQgfCBudWxsPihudWxsKTtcbiAgY29uc3QgW2Vycm9yLCBzZXRFcnJvcl0gPSB1c2VTdGF0ZTxzdHJpbmcgfCBudWxsPihudWxsKTtcblxuICBjb25zdCBvbkZpbGVzID0gYXN5bmMgKGZpbGVzOiBGaWxlTGlzdCB8IG51bGwpID0+IHtcbiAgICBpZiAoIWZpbGVzIHx8ICFmaWxlcy5sZW5ndGgpIHJldHVybjtcbiAgICBzZXRFcnJvcihudWxsKTtcbiAgICBzZXRCdXN5KHRydWUpO1xuICAgIGNvbnN0IGZvcm0gPSBuZXcgRm9ybURhdGEoKTtcbiAgICBmb3JtLmFwcGVuZCgndXBsb2FkJywgZmlsZXNbMF0pO1xuICAgIHRyeSB7XG4gICAgICBjb25zdCByID0gYXdhaXQgZmV0Y2goJy9hcGkvZmlsZXMvdXBsb2FkJywgeyBtZXRob2Q6ICdQT1NUJywgYm9keTogZm9ybSB9KTtcbiAgICAgIGlmICghci5vaykge1xuICAgICAgICBjb25zdCBib2R5ID0gYXdhaXQgci5qc29uKCkuY2F0Y2goKCkgPT4gKHt9KSk7XG4gICAgICAgIHRocm93IG5ldyBFcnJvcihib2R5LmRldGFpbCA/PyBgJHtyLnN0YXR1c30gJHtyLnN0YXR1c1RleHR9YCk7XG4gICAgICB9XG4gICAgICBjb25zdCBkYXRhID0gKGF3YWl0IHIuanNvbigpKSBhcyBVcGxvYWRSZXN1bHQ7XG4gICAgICBzZXRMYXN0KGRhdGEpO1xuICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgIHNldEVycm9yKChlIGFzIEVycm9yKS5tZXNzYWdlKTtcbiAgICB9IGZpbmFsbHkge1xuICAgICAgc2V0QnVzeShmYWxzZSk7XG4gICAgfVxuICB9O1xuXG4gIHJldHVybiAoXG4gICAgPENhcmQgd2l0aEJvcmRlciBwYWRkaW5nPVwic21cIiByYWRpdXM9XCJtZFwiPlxuICAgICAgPEdyb3VwIGp1c3RpZnk9XCJzcGFjZS1iZXR3ZWVuXCIgYWxpZ249XCJjZW50ZXJcIj5cbiAgICAgICAgPGRpdj5cbiAgICAgICAgICA8VGV4dCBmdz17NjAwfT7wn5OCIO2MjOydvCDsl4XroZzrk5w8L1RleHQ+XG4gICAgICAgICAgPFRleHQgc2l6ZT1cInhzXCIgYz1cImRpbW1lZFwiPlxuICAgICAgICAgICAgQ1NWIC8gVFNWIC8gSlNPTiAvIFBhcnF1ZXQgLyBFeGNlbCAvIEZlYXRoZXIg4oCUIOy1nOuMgCAxIEdpQi4g7JeF66Gc65Oc65CcIO2MjOydvOydgFxuICAgICAgICAgICAgSnVweXRlckxhYuydmCA8Q29kZT5+L3dvcmsvdXBsb2Fkcy88L0NvZGU+IOyXkOyEnCDrsJTroZwg7J297J2EIOyImCDsnojslrTsmpQuXG4gICAgICAgICAgPC9UZXh0PlxuICAgICAgICA8L2Rpdj5cbiAgICAgICAgPEJ1dHRvblxuICAgICAgICAgIGNvbXBvbmVudD1cImxhYmVsXCJcbiAgICAgICAgICB2YXJpYW50PVwibGlnaHRcIlxuICAgICAgICAgIGxvYWRpbmc9e2J1c3l9XG4gICAgICAgID5cbiAgICAgICAgICDtjIzsnbwg7ISg7YOdXG4gICAgICAgICAgPGlucHV0XG4gICAgICAgICAgICB0eXBlPVwiZmlsZVwiXG4gICAgICAgICAgICBzdHlsZT17eyBkaXNwbGF5OiAnbm9uZScgfX1cbiAgICAgICAgICAgIGFjY2VwdD1cIi5jc3YsLnRzdiwuanNvbiwuanNvbmwsLm5kanNvbiwucGFycXVldCwueGxzeCwuZmVhdGhlciwuYXJyb3dcIlxuICAgICAgICAgICAgb25DaGFuZ2U9eyhlKSA9PiBvbkZpbGVzKGUuY3VycmVudFRhcmdldC5maWxlcyl9XG4gICAgICAgICAgLz5cbiAgICAgICAgPC9CdXR0b24+XG4gICAgICA8L0dyb3VwPlxuICAgICAge2Vycm9yICYmIDxOb3RpZmljYXRpb24gY29sb3I9XCJyZWRcIiB0aXRsZT1cIuyXheuhnOuTnCDsi6TtjKhcIiBtdD1cInNtXCI+e2Vycm9yfTwvTm90aWZpY2F0aW9uPn1cbiAgICAgIHtsYXN0ICYmIChcbiAgICAgICAgPFN0YWNrIGdhcD17NH0gbXQ9XCJzbVwiPlxuICAgICAgICAgIDxUZXh0IHNpemU9XCJzbVwiPlxuICAgICAgICAgICAg4pyTIDxzdHJvbmc+e2xhc3Quc2FmZV9uYW1lfTwvc3Ryb25nPiAoe01hdGgucm91bmQobGFzdC5zaXplX2J5dGVzIC8gMTAyNCl9IEtpQilcbiAgICAgICAgICA8L1RleHQ+XG4gICAgICAgICAgPFRleHQgc2l6ZT1cInhzXCIgYz1cImRpbW1lZFwiPkp1cHl0ZXJMYWLsl5DshJw6IDxDb2RlPntsYXN0LmhpbnR9PC9Db2RlPjwvVGV4dD5cbiAgICAgICAgPC9TdGFjaz5cbiAgICAgICl9XG4gICAgPC9DYXJkPlxuICApO1xufVxuXG5mdW5jdGlvbiBRdWVyeUVkaXRvcigpIHtcbiAgY29uc3QgcWMgPSB1c2VRdWVyeUNsaWVudCgpO1xuICBjb25zdCBjb25ucyA9IHVzZVF1ZXJ5KHsgcXVlcnlLZXk6IFsnY29ubnMnXSwgcXVlcnlGbjogYXBpLmNvbm5lY3Rpb25zIH0pO1xuICBjb25zdCBtZSA9IHVzZVF1ZXJ5KHsgcXVlcnlLZXk6IFsnbWUnXSwgcXVlcnlGbjogYXBpLm1lIH0pO1xuICBjb25zdCBuYnMgPSB1c2VRdWVyeSh7IHF1ZXJ5S2V5OiBbJ25icyddLCBxdWVyeUZuOiBhcGkubm90ZWJvb2tzIH0pO1xuXG4gIGNvbnN0IFtjb25uSWQsIHNldENvbm5JZF0gPSB1c2VTdGF0ZTxzdHJpbmcgfCBudWxsPihudWxsKTtcbiAgY29uc3QgW3NxbCwgc2V0U3FsXSA9IHVzZVN0YXRlKCcnKTtcblxuICB1c2VFZmZlY3QoKCkgPT4ge1xuICAgIGlmICghY29ubklkICYmIGNvbm5zLmRhdGE/Lmxlbmd0aCkge1xuICAgICAgY29uc3QgZmlyc3QgPSBjb25ucy5kYXRhWzBdO1xuICAgICAgc2V0Q29ubklkKGZpcnN0LmNvbm5lY3Rpb25faWQpO1xuICAgICAgc2V0U3FsKFNBTVBMRV9TUUxbZmlyc3QubmFtZV0gPz8gYFNFTEVDVCAqIEZST00gc2FtcGxlIExJTUlUIDEwYCk7XG4gICAgfVxuICB9LCBbY29ubnMuZGF0YV0pO1xuXG4gIGNvbnN0IHNjaGVtYSA9IHVzZVF1ZXJ5KHtcbiAgICBxdWVyeUtleTogWydzY2hlbWEnLCBjb25uSWRdLFxuICAgIHF1ZXJ5Rm46ICgpID0+IGFwaS5zY2hlbWEoY29ubklkISksXG4gICAgZW5hYmxlZDogISFjb25uSWQsXG4gIH0pO1xuXG4gIGNvbnN0IHJ1biA9IHVzZU11dGF0aW9uKHtcbiAgICBtdXRhdGlvbkZuOiAoKSA9PiBhcGkucnVuUXVlcnkoeyBjb25uZWN0aW9uX2lkOiBjb25uSWQhLCBzcWwgfSksXG4gIH0pO1xuXG4gIGNvbnN0IHNhdmUgPSB1c2VNdXRhdGlvbih7XG4gICAgbXV0YXRpb25GbjogYXN5bmMgKCkgPT4ge1xuICAgICAgaWYgKCFuYnMuZGF0YT8ubGVuZ3RoIHx8ICFtZS5kYXRhKSB0aHJvdyBuZXcgRXJyb3IoJ25vIG5vdGVib29rIHRvIHNhdmUgdG8nKTtcbiAgICAgIGNvbnN0IGNvbnRlbnQgPSB7XG4gICAgICAgIHRpdGxlOiAnQWQtaG9jIHF1ZXJ5IHJlc3VsdCcsXG4gICAgICAgIGNlbGxzOiBbXG4gICAgICAgICAgeyBraW5kOiAnc3FsJywgY29ubmVjdGlvbl9pZDogY29ubklkLCBzcWwgfSxcbiAgICAgICAgICBydW4uZGF0YSA/IHsga2luZDogJ3Jlc3VsdCcsIHByZXZpZXdfcm93czogcnVuLmRhdGEucm93cy5zbGljZSgwLCA1KSB9IDogbnVsbCxcbiAgICAgICAgXS5maWx0ZXIoQm9vbGVhbiksXG4gICAgICAgIHNhdmVkX2F0OiBuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCksXG4gICAgICB9O1xuICAgICAgcmV0dXJuIGFwaS5zYXZlTm90ZWJvb2sobmJzLmRhdGFbMF0ubm90ZWJvb2tfaWQsIHtcbiAgICAgICAgY29udGVudCxcbiAgICAgICAgc2F2ZWRfYnk6IG1lLmRhdGEudXNlcl9pZCxcbiAgICAgICAgY29tbWl0X21lc3NhZ2U6ICdhbmFseXN0IFNQQSBzYXZlJyxcbiAgICAgIH0pO1xuICAgIH0sXG4gICAgb25TdWNjZXNzOiAoKSA9PiBxYy5pbnZhbGlkYXRlUXVlcmllcyh7IHF1ZXJ5S2V5OiBbJ25icyddIH0pLFxuICB9KTtcblxuICBpZiAoY29ubnMuaXNMb2FkaW5nKSByZXR1cm4gPExvYWRlciAvPjtcblxuICByZXR1cm4gKFxuICAgIDxTdGFjayBwPVwibWRcIiBnYXA9XCJtZFwiPlxuICAgICAgPEZpbGVVcGxvYWRDYXJkIC8+XG4gICAgICA8R3JvdXAgYWxpZ249XCJmbGV4LWVuZFwiPlxuICAgICAgICA8U2VsZWN0XG4gICAgICAgICAgbGFiZWw9XCLsu6TrhKXshZhcIlxuICAgICAgICAgIHZhbHVlPXtjb25uSWR9XG4gICAgICAgICAgb25DaGFuZ2U9eyh2KSA9PiB7XG4gICAgICAgICAgICBzZXRDb25uSWQodik7XG4gICAgICAgICAgICBjb25zdCBjID0gY29ubnMuZGF0YT8uZmluZCgoeCkgPT4geC5jb25uZWN0aW9uX2lkID09PSB2KTtcbiAgICAgICAgICAgIGlmIChjKSBzZXRTcWwoU0FNUExFX1NRTFtjLm5hbWVdID8/IHNxbCk7XG4gICAgICAgICAgfX1cbiAgICAgICAgICBkYXRhPXsoY29ubnMuZGF0YSA/PyBbXSkubWFwKChjKSA9PiAoe1xuICAgICAgICAgICAgdmFsdWU6IGMuY29ubmVjdGlvbl9pZCxcbiAgICAgICAgICAgIGxhYmVsOiBgJHtjLm5hbWV9ICgke2MuZW5naW5lfSlgLFxuICAgICAgICAgIH0pKX1cbiAgICAgICAgICB3PXsyODB9XG4gICAgICAgIC8+XG4gICAgICAgIHtzY2hlbWEuZGF0YSAmJiAoXG4gICAgICAgICAgPEdyb3VwIGdhcD1cInhzXCI+XG4gICAgICAgICAgICB7c2NoZW1hLmRhdGEudGFibGVzLm1hcCgodCkgPT4ge1xuICAgICAgICAgICAgICBjb25zdCBjb2xOYW1lcyA9IHQuY29sdW1ucy5tYXAoKGMpID0+IGMubmFtZSkuc2xpY2UoMCwgNCkuam9pbignLCAnKTtcbiAgICAgICAgICAgICAgY29uc3QgcXVhbGlmaWVkID0gdC5zY2hlbWEgPyBgJHt0LnNjaGVtYX0uJHt0Lm5hbWV9YCA6IHQubmFtZTtcbiAgICAgICAgICAgICAgcmV0dXJuIChcbiAgICAgICAgICAgICAgICA8QmFkZ2VcbiAgICAgICAgICAgICAgICAgIGtleT17cXVhbGlmaWVkfVxuICAgICAgICAgICAgICAgICAgdmFyaWFudD1cImxpZ2h0XCJcbiAgICAgICAgICAgICAgICAgIHN0eWxlPXt7IGN1cnNvcjogJ3BvaW50ZXInIH19XG4gICAgICAgICAgICAgICAgICBvbkNsaWNrPXsoKSA9PiBzZXRTcWwoYFNFTEVDVCAke2NvbE5hbWVzfSBGUk9NICR7cXVhbGlmaWVkfSBMSU1JVCAyNWApfVxuICAgICAgICAgICAgICAgICAgdGl0bGU9e3QuY29sdW1ucy5tYXAoKGMpID0+IGAke2MubmFtZX06ICR7Yy50eXBlfSR7Yy5waWlfa2luZCA/ICcgW1BJSV0nIDogJyd9YCkuam9pbignXFxuJyl9XG4gICAgICAgICAgICAgICAgPlxuICAgICAgICAgICAgICAgICAge3F1YWxpZmllZH0gKHt0LmNvbHVtbnMubGVuZ3RofSlcbiAgICAgICAgICAgICAgICA8L0JhZGdlPlxuICAgICAgICAgICAgICApO1xuICAgICAgICAgICAgfSl9XG4gICAgICAgICAgPC9Hcm91cD5cbiAgICAgICAgKX1cbiAgICAgIDwvR3JvdXA+XG5cbiAgICAgIDxUZXh0YXJlYVxuICAgICAgICBsYWJlbD1cIlNRTFwiXG4gICAgICAgIGF1dG9zaXplXG4gICAgICAgIG1pblJvd3M9ezR9XG4gICAgICAgIHZhbHVlPXtzcWx9XG4gICAgICAgIG9uQ2hhbmdlPXsoZSkgPT4gc2V0U3FsKGUuY3VycmVudFRhcmdldC52YWx1ZSl9XG4gICAgICAgIHN0eWxlcz17eyBpbnB1dDogeyBmb250RmFtaWx5OiAnbW9ub3NwYWNlJywgZm9udFNpemU6IDEzIH0gfX1cbiAgICAgIC8+XG5cbiAgICAgIDxHcm91cD5cbiAgICAgICAgPEJ1dHRvbiBsb2FkaW5nPXtydW4uaXNQZW5kaW5nfSBvbkNsaWNrPXsoKSA9PiBydW4ubXV0YXRlKCl9IGRpc2FibGVkPXshY29ubklkIHx8ICFzcWx9PlxuICAgICAgICAgIOKWtiDsi6TtlolcbiAgICAgICAgPC9CdXR0b24+XG4gICAgICAgIDxCdXR0b25cbiAgICAgICAgICB2YXJpYW50PVwibGlnaHRcIlxuICAgICAgICAgIGxvYWRpbmc9e3NhdmUuaXNQZW5kaW5nfVxuICAgICAgICAgIG9uQ2xpY2s9eygpID0+IHNhdmUubXV0YXRlKCl9XG4gICAgICAgICAgZGlzYWJsZWQ9eyFydW4uZGF0YSB8fCAhbmJzLmRhdGE/Lmxlbmd0aH1cbiAgICAgICAgPlxuICAgICAgICAgIPCfkr4g64W47Yq467aB7JeQIOyggOyepSAoR2l0IOyekOuPmSDsu6TrsIspXG4gICAgICAgIDwvQnV0dG9uPlxuICAgICAgICB7c2F2ZS5pc1N1Y2Nlc3MgJiYgKFxuICAgICAgICAgIDxCYWRnZSBjb2xvcj1cInRlYWxcIiB2YXJpYW50PVwiZmlsbGVkXCI+XG4gICAgICAgICAgICDsoIDsnqXrkKgg4oCUIHZlcnNpb24ge1N0cmluZygoc2F2ZS5kYXRhIGFzIGFueSkudmVyc2lvbl9pZCkuc2xpY2UoMCwgOCl94oCmXG4gICAgICAgICAgPC9CYWRnZT5cbiAgICAgICAgKX1cbiAgICAgIDwvR3JvdXA+XG5cbiAgICAgIHtydW4uZXJyb3IgJiYgPE5vdGlmaWNhdGlvbiBjb2xvcj1cInJlZFwiIHRpdGxlPVwi7JeQ65+sXCI+eyhydW4uZXJyb3IgYXMgRXJyb3IpLm1lc3NhZ2V9PC9Ob3RpZmljYXRpb24+fVxuXG4gICAgICB7cnVuLmRhdGEgJiYgKFxuICAgICAgICA8Q2FyZCBwYWRkaW5nPVwibWRcIiByYWRpdXM9XCJtZFwiIHdpdGhCb3JkZXI+XG4gICAgICAgICAgPFN0YWNrIGdhcD1cInNtXCI+XG4gICAgICAgICAgICA8R3JvdXAganVzdGlmeT1cInNwYWNlLWJldHdlZW5cIj5cbiAgICAgICAgICAgICAgPEdyb3VwIGdhcD1cInhzXCI+XG4gICAgICAgICAgICAgICAgPEJhZGdlIGNvbG9yPVwiYmx1ZVwiPntydW4uZGF0YS5lbmdpbmV9PC9CYWRnZT5cbiAgICAgICAgICAgICAgICA8VGV4dCBzaXplPVwic21cIiBjPVwiZGltbWVkXCI+e3J1bi5kYXRhLnJvd19jb3VudH3qsbQ8L1RleHQ+XG4gICAgICAgICAgICAgICAgPFRleHQgc2l6ZT1cInhzXCIgYz1cImRpbW1lZFwiPntydW4uZGF0YS5leGVjdXRlZF9hdH08L1RleHQ+XG4gICAgICAgICAgICAgIDwvR3JvdXA+XG4gICAgICAgICAgICAgIDxHcm91cCBnYXA9ezR9PlxuICAgICAgICAgICAgICAgIDxUZXh0IHNpemU9XCJ4c1wiIGM9XCJkaW1tZWRcIj7tmZzshLEgUElJIO2MqO2EtDo8L1RleHQ+XG4gICAgICAgICAgICAgICAge3J1bi5kYXRhLmFjdGl2ZV9waWlfcGF0dGVybnMubWFwKChwKSA9PiAoXG4gICAgICAgICAgICAgICAgICA8QmFkZ2Uga2V5PXtwfSBjb2xvcj1cImdyYXBlXCIgdmFyaWFudD1cImxpZ2h0XCI+e3B9PC9CYWRnZT5cbiAgICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgICAgPC9Hcm91cD5cbiAgICAgICAgICAgIDwvR3JvdXA+XG5cbiAgICAgICAgICAgIDxUYWJzIGRlZmF1bHRWYWx1ZT1cInRhYmxlXCI+XG4gICAgICAgICAgICAgIDxUYWJzLkxpc3Q+XG4gICAgICAgICAgICAgICAgPFRhYnMuVGFiIHZhbHVlPVwidGFibGVcIj7tkZw8L1RhYnMuVGFiPlxuICAgICAgICAgICAgICAgIDxUYWJzLlRhYiB2YWx1ZT1cImNoYXJ0XCI+7LCo7Yq4PC9UYWJzLlRhYj5cbiAgICAgICAgICAgICAgPC9UYWJzLkxpc3Q+XG5cbiAgICAgICAgICAgICAgPFRhYnMuUGFuZWwgdmFsdWU9XCJ0YWJsZVwiIHB0PVwic21cIj5cbiAgICAgICAgICAgICAgICA8U2Nyb2xsQXJlYSBoPXszNjB9PlxuICAgICAgICAgICAgICAgICAgPFRhYmxlIHN0cmlwZWQgd2l0aFRhYmxlQm9yZGVyIHdpdGhDb2x1bW5Cb3JkZXJzIGZ6PVwic21cIj5cbiAgICAgICAgICAgICAgICAgICAgPFRhYmxlLlRoZWFkPlxuICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZS5Ucj5cbiAgICAgICAgICAgICAgICAgICAgICAgIHtydW4uZGF0YS5jb2x1bW5zLm1hcCgoYykgPT4gKFxuICAgICAgICAgICAgICAgICAgICAgICAgICA8VGFibGUuVGgga2V5PXtjfT57Y308L1RhYmxlLlRoPlxuICAgICAgICAgICAgICAgICAgICAgICAgKSl9XG4gICAgICAgICAgICAgICAgICAgICAgPC9UYWJsZS5Ucj5cbiAgICAgICAgICAgICAgICAgICAgPC9UYWJsZS5UaGVhZD5cbiAgICAgICAgICAgICAgICAgICAgPFRhYmxlLlRib2R5PlxuICAgICAgICAgICAgICAgICAgICAgIHtydW4uZGF0YS5yb3dzLm1hcCgocm93LCBpKSA9PiAoXG4gICAgICAgICAgICAgICAgICAgICAgICA8VGFibGUuVHIga2V5PXtpfT5cbiAgICAgICAgICAgICAgICAgICAgICAgICAge3J1bi5kYXRhIS5jb2x1bW5zLm1hcCgoYykgPT4gKFxuICAgICAgICAgICAgICAgICAgICAgICAgICAgIDxUYWJsZS5UZCBrZXk9e2N9PjxDb2RlPntTdHJpbmcocm93W2NdID8/ICcnKX08L0NvZGU+PC9UYWJsZS5UZD5cbiAgICAgICAgICAgICAgICAgICAgICAgICAgKSl9XG4gICAgICAgICAgICAgICAgICAgICAgICA8L1RhYmxlLlRyPlxuICAgICAgICAgICAgICAgICAgICAgICkpfVxuICAgICAgICAgICAgICAgICAgICA8L1RhYmxlLlRib2R5PlxuICAgICAgICAgICAgICAgICAgPC9UYWJsZT5cbiAgICAgICAgICAgICAgICA8L1Njcm9sbEFyZWE+XG4gICAgICAgICAgICAgIDwvVGFicy5QYW5lbD5cblxuICAgICAgICAgICAgICA8VGFicy5QYW5lbCB2YWx1ZT1cImNoYXJ0XCIgcHQ9XCJzbVwiPlxuICAgICAgICAgICAgICAgIDxDaGFydFBpY2tlciByZXN1bHQ9e3J1bi5kYXRhfSAvPlxuICAgICAgICAgICAgICA8L1RhYnMuUGFuZWw+XG4gICAgICAgICAgICA8L1RhYnM+XG4gICAgICAgICAgPC9TdGFjaz5cbiAgICAgICAgPC9DYXJkPlxuICAgICAgKX1cbiAgICA8L1N0YWNrPlxuICApO1xufVxuXG5mdW5jdGlvbiBOb3RlYm9va0xpc3QoKSB7XG4gIGNvbnN0IG5icyA9IHVzZVF1ZXJ5KHsgcXVlcnlLZXk6IFsnbmJzJ10sIHF1ZXJ5Rm46IGFwaS5ub3RlYm9va3MgfSk7XG4gIHJldHVybiAoXG4gICAgPFN0YWNrIHA9XCJtZFwiIGdhcD1cIm1kXCI+XG4gICAgICA8VGl0bGUgb3JkZXI9ezN9PuuCtCDrhbjtirjrtoE8L1RpdGxlPlxuICAgICAge25icy5pc0xvYWRpbmcgJiYgPExvYWRlciAvPn1cbiAgICAgIHtuYnMuZGF0YSAmJiAoXG4gICAgICAgIDxUYWJsZSBzdHJpcGVkIHdpdGhUYWJsZUJvcmRlciB3aXRoQ29sdW1uQm9yZGVycz5cbiAgICAgICAgICA8VGFibGUuVGhlYWQ+XG4gICAgICAgICAgICA8VGFibGUuVHI+XG4gICAgICAgICAgICAgIDxUYWJsZS5UaD7qsr3roZw8L1RhYmxlLlRoPlxuICAgICAgICAgICAgICA8VGFibGUuVGg+7LWc6re8IOyggOyepTwvVGFibGUuVGg+XG4gICAgICAgICAgICAgIDxUYWJsZS5UaD7rsoTsoIQ8L1RhYmxlLlRoPlxuICAgICAgICAgICAgICA8VGFibGUuVGg+7JWh7IWYPC9UYWJsZS5UaD5cbiAgICAgICAgICAgIDwvVGFibGUuVHI+XG4gICAgICAgICAgPC9UYWJsZS5UaGVhZD5cbiAgICAgICAgICA8VGFibGUuVGJvZHk+XG4gICAgICAgICAgICB7bmJzLmRhdGEubWFwKChuYikgPT4gKFxuICAgICAgICAgICAgICA8VGFibGUuVHIga2V5PXtuYi5ub3RlYm9va19pZH0+XG4gICAgICAgICAgICAgICAgPFRhYmxlLlRkPntuYi5wYXRofTwvVGFibGUuVGQ+XG4gICAgICAgICAgICAgICAgPFRhYmxlLlRkPntuYi5sYXRlc3Rfc2F2ZWRfYXQgPyBuZXcgRGF0ZShuYi5sYXRlc3Rfc2F2ZWRfYXQpLnRvTG9jYWxlU3RyaW5nKCkgOiAn4oCUJ308L1RhYmxlLlRkPlxuICAgICAgICAgICAgICAgIDxUYWJsZS5UZD57bmIubGF0ZXN0X3ZlcnNpb24/LnNsaWNlKDAsIDgpID8/ICfigJQnfTwvVGFibGUuVGQ+XG4gICAgICAgICAgICAgICAgPFRhYmxlLlRkPlxuICAgICAgICAgICAgICAgICAgPEJ1dHRvbiBzaXplPVwieHNcIiBjb21wb25lbnQ9e0xpbmt9IHRvPXtgL25vdGVib29rcy8ke25iLm5vdGVib29rX2lkfWB9PuyXtOq4sDwvQnV0dG9uPlxuICAgICAgICAgICAgICAgIDwvVGFibGUuVGQ+XG4gICAgICAgICAgICAgIDwvVGFibGUuVHI+XG4gICAgICAgICAgICApKX1cbiAgICAgICAgICA8L1RhYmxlLlRib2R5PlxuICAgICAgICA8L1RhYmxlPlxuICAgICAgKX1cbiAgICA8L1N0YWNrPlxuICApO1xufVxuXG5mdW5jdGlvbiBOb3RlYm9va0RldGFpbCgpIHtcbiAgY29uc3QgeyBpZCB9ID0gdXNlUGFyYW1zKCk7XG4gIGNvbnN0IG5iID0gdXNlUXVlcnkoe1xuICAgIHF1ZXJ5S2V5OiBbJ25iJywgaWRdLFxuICAgIHF1ZXJ5Rm46ICgpID0+IGFwaS5sYXRlc3ROb3RlYm9vayhpZCEpLFxuICAgIGVuYWJsZWQ6ICEhaWQsXG4gIH0pO1xuICByZXR1cm4gKFxuICAgIDxTdGFjayBwPVwibWRcIiBnYXA9XCJtZFwiPlxuICAgICAgPEdyb3VwPlxuICAgICAgICA8QnV0dG9uIGNvbXBvbmVudD17TGlua30gdG89XCIvbm90ZWJvb2tzXCIgdmFyaWFudD1cInN1YnRsZVwiPuKGkCDrqqnroZ08L0J1dHRvbj5cbiAgICAgIDwvR3JvdXA+XG4gICAgICB7bmIuaXNMb2FkaW5nICYmIDxMb2FkZXIgLz59XG4gICAgICB7bmIuZGF0YSAmJiAoXG4gICAgICAgIDxDYXJkIHdpdGhCb3JkZXI+XG4gICAgICAgICAgPFRpdGxlIG9yZGVyPXszfT57bmIuZGF0YS5wYXRofTwvVGl0bGU+XG4gICAgICAgICAgPFRleHQgc2l6ZT1cInNtXCIgYz1cImRpbW1lZFwiPuy1nOq3vCDsoIDsnqU6IHtuYi5kYXRhLnNhdmVkX2F0ID8/ICfigJQnfTwvVGV4dD5cbiAgICAgICAgICA8Q29kZSBibG9jayBzdHlsZT17eyBtYXJnaW5Ub3A6IDggfX0+XG4gICAgICAgICAgICB7SlNPTi5zdHJpbmdpZnkobmIuZGF0YS5jb250ZW50LCBudWxsLCAyKX1cbiAgICAgICAgICA8L0NvZGU+XG4gICAgICAgIDwvQ2FyZD5cbiAgICAgICl9XG4gICAgPC9TdGFjaz5cbiAgKTtcbn1cblxuZnVuY3Rpb24gSnVweXRlckxhYih7IHJlbG9hZFRva2VuIH06IHsgcmVsb2FkVG9rZW46IG51bWJlciB9KSB7XG4gIC8vIExhbmQgZGlyZWN0bHkgb24gY29waWxvdC5pcHluYiBzbyB0aGUgdXNlciBzZWVzIGZyZXNobHktaW5zZXJ0ZWQgY2VsbHNcbiAgLy8gd2l0aG91dCBoYXZpbmcgdG8gbmF2aWdhdGUgdGhlIGZpbGUgYnJvd3Nlci4gVGhlIGByZWxvYWRUb2tlbmAgaXMgYnVtcGVkXG4gIC8vIGJ5IHRoZSBwYXJlbnQgYWZ0ZXIgZXZlcnkgUFVUIHNvIHdlIHJlLW1vdW50IHRoZSBpZnJhbWUgYW5kIHJlLXJlYWQgdGhlXG4gIC8vIG5vdGVib29rIGZyb20gZGlzayAoSnVweXRlckxhYiBpdHNlbGYgZG9lcyBub3QgYXV0by1yZWZyZXNoIG9uIGV4dGVybmFsXG4gIC8vIGZpbGUgY2hhbmdlcyDigJQgaXQgb25seSBzaG93cyBhIFwiY2hhbmdlZCBvbiBkaXNrXCIgbW9kYWwgdGhhdCB0aGUgdXNlclxuICAvLyB3b3VsZCBoYXZlIHRvIGNsaWNrIGV2ZXJ5IHNpbmdsZSB0aW1lKS5cbiAgLy9cbiAgLy8gV2hpbGUgdGhlIG5ldyBpZnJhbWUgaXMgbG9hZGluZyB3ZSBmYWRlIHRoZSBjb250ZW50cyBzbyB0aGUgdXNlciBzZWVzIGFcbiAgLy8gc21vb3RoIHRyYW5zaXRpb24gaW5zdGVhZCBvZiBhIGhhcmQgd2hpdGUgZmxhc2guXG4gIGNvbnN0IFtsb2FkaW5nLCBzZXRMb2FkaW5nXSA9IHVzZVN0YXRlKHRydWUpO1xuICB1c2VFZmZlY3QoKCkgPT4ge1xuICAgIHNldExvYWRpbmcodHJ1ZSk7XG4gIH0sIFtyZWxvYWRUb2tlbl0pO1xuXG4gIGNvbnN0IHNyYyA9IGAvanVweXRlci9sYWIvdHJlZS9jb3BpbG90LmlweW5iP3Rva2VuPWRhdGFwbGF0Zm9ybSZyZXNldCZ0PSR7cmVsb2FkVG9rZW59YDtcbiAgcmV0dXJuIChcbiAgICA8aWZyYW1lXG4gICAgICBrZXk9e3JlbG9hZFRva2VufVxuICAgICAgc3JjPXtzcmN9XG4gICAgICB0aXRsZT1cIkp1cHl0ZXJMYWJcIlxuICAgICAgb25Mb2FkPXsoKSA9PiBzZXRMb2FkaW5nKGZhbHNlKX1cbiAgICAgIHN0eWxlPXt7XG4gICAgICAgIHdpZHRoOiAnMTAwJScsXG4gICAgICAgIGhlaWdodDogJzEwMCUnLFxuICAgICAgICBib3JkZXI6ICdub25lJyxcbiAgICAgICAgZGlzcGxheTogJ2Jsb2NrJyxcbiAgICAgICAgdHJhbnNpdGlvbjogJ29wYWNpdHkgMjUwbXMgZWFzZS1pbicsXG4gICAgICAgIG9wYWNpdHk6IGxvYWRpbmcgPyAwLjQ1IDogMSxcbiAgICAgIH19XG4gICAgICBhbGxvdz1cImNsaXBib2FyZC1yZWFkOyBjbGlwYm9hcmQtd3JpdGVcIlxuICAgIC8+XG4gICk7XG59XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gSnVweXRlciBjZWxsIGluamVjdGlvbiDigJQgYXBwZW5kIGEgY29kZSBjZWxsIHRvIHRoZSBzaGFyZWQgY29waWxvdC5pcHluYlxuLy8gLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tXG5jb25zdCBDT1BJTE9UX05PVEVCT09LID0gJ2NvcGlsb3QuaXB5bmInO1xuY29uc3QgSlVQWVRFUl9UT0tFTiA9ICdkYXRhcGxhdGZvcm0nO1xuXG5hc3luYyBmdW5jdGlvbiBhcHBlbmRDZWxsVG9Db3BpbG90Tm90ZWJvb2sobGFuZ3VhZ2U6ICdzcWwnIHwgJ3B5dGhvbicsIHNvdXJjZTogc3RyaW5nKTogUHJvbWlzZTx2b2lkPiB7XG4gIGNvbnN0IHVybCA9IGAvanVweXRlci9hcGkvY29udGVudHMvJHtDT1BJTE9UX05PVEVCT09LfWA7XG4gIGNvbnN0IGhlYWRlcnM6IEhlYWRlcnNJbml0ID0ge1xuICAgICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbicsXG4gICAgQXV0aG9yaXphdGlvbjogYHRva2VuICR7SlVQWVRFUl9UT0tFTn1gLFxuICB9O1xuXG4gIGxldCBub3RlYm9vazogYW55IHwgbnVsbCA9IG51bGw7XG4gIGNvbnN0IGhlYWQgPSBhd2FpdCBmZXRjaCh1cmwsIHsgaGVhZGVycywgY3JlZGVudGlhbHM6ICdvbWl0JyB9KTtcbiAgaWYgKGhlYWQub2spIHtcbiAgICBub3RlYm9vayA9IGF3YWl0IGhlYWQuanNvbigpO1xuICB9XG4gIGlmICghbm90ZWJvb2spIHtcbiAgICBub3RlYm9vayA9IHtcbiAgICAgIHR5cGU6ICdub3RlYm9vaycsXG4gICAgICBjb250ZW50OiB7XG4gICAgICAgIGNlbGxzOiBbXSxcbiAgICAgICAgbWV0YWRhdGE6IHsga2VybmVsc3BlYzogeyBuYW1lOiAncHl0aG9uMycsIGRpc3BsYXlfbmFtZTogJ1B5dGhvbiAzJyB9IH0sXG4gICAgICAgIG5iZm9ybWF0OiA0LFxuICAgICAgICBuYmZvcm1hdF9taW5vcjogNSxcbiAgICAgIH0sXG4gICAgICBmb3JtYXQ6ICdqc29uJyxcbiAgICAgIG5hbWU6IENPUElMT1RfTk9URUJPT0ssXG4gICAgICBwYXRoOiBDT1BJTE9UX05PVEVCT09LLFxuICAgIH07XG4gIH1cbiAgY29uc3QgY2VsbCA9IHtcbiAgICBjZWxsX3R5cGU6ICdjb2RlJyxcbiAgICBtZXRhZGF0YTogeyBjb3BpbG90X2dlbmVyYXRlZDogdHJ1ZSwgbGFuZ3VhZ2UgfSxcbiAgICBzb3VyY2U6IGxhbmd1YWdlID09PSAnc3FsJyA/IGAlJXNxbFxcbiR7c291cmNlfWAgOiBzb3VyY2UsXG4gICAgb3V0cHV0czogW10sXG4gICAgZXhlY3V0aW9uX2NvdW50OiBudWxsLFxuICB9O1xuICBub3RlYm9vay5jb250ZW50LmNlbGxzLnB1c2goY2VsbCk7XG4gIG5vdGVib29rLnR5cGUgPSAnbm90ZWJvb2snO1xuICBub3RlYm9vay5mb3JtYXQgPSAnanNvbic7XG4gIG5vdGVib29rLm5hbWUgPSBDT1BJTE9UX05PVEVCT09LO1xuICBub3RlYm9vay5wYXRoID0gQ09QSUxPVF9OT1RFQk9PSztcblxuICBjb25zdCBwdXQgPSBhd2FpdCBmZXRjaCh1cmwsIHtcbiAgICBtZXRob2Q6ICdQVVQnLFxuICAgIGhlYWRlcnMsXG4gICAgY3JlZGVudGlhbHM6ICdvbWl0JyxcbiAgICBib2R5OiBKU09OLnN0cmluZ2lmeSh7XG4gICAgICB0eXBlOiAnbm90ZWJvb2snLFxuICAgICAgZm9ybWF0OiAnanNvbicsXG4gICAgICBjb250ZW50OiBub3RlYm9vay5jb250ZW50LFxuICAgIH0pLFxuICB9KTtcbiAgaWYgKCFwdXQub2spIHtcbiAgICB0aHJvdyBuZXcgRXJyb3IoYEp1cHl0ZXIgUFVUIGZhaWxlZDogJHtwdXQuc3RhdHVzfWApO1xuICB9XG59XG5cbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxuLy8gQ29waWxvdFBhbmVsIOKAlCBjaGF0IHdpdGggdGhlIExMTSwgcmVuZGVyIGNvZGUgYmxvY2tzIHdpdGggaW5zZXJ0IGJ1dHRvbnNcbi8vIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLVxudHlwZSBDb3BpbG90TXNnID0geyByb2xlOiAndXNlcicgfCAnYXNzaXN0YW50JzsgY29udGVudDogc3RyaW5nIH07XG50eXBlIENvcGlsb3RDb2RlQmxvY2sgPSB7IGxhbmd1YWdlOiAnc3FsJyB8ICdweXRob24nOyBzb3VyY2U6IHN0cmluZyB9O1xuXG5mdW5jdGlvbiBzcGxpdE1hcmtkb3duQ29kZUJsb2Nrcyh0ZXh0OiBzdHJpbmcpOiBBcnJheTx7IHRleHQ6IHN0cmluZzsgYmxvY2tzOiBDb3BpbG90Q29kZUJsb2NrW10gfT4ge1xuICAvLyBXZSBrZWVwIG9uZSBcInNlZ21lbnRcIiB3aXRoIHRoZSBmdWxsIHRleHQgcGx1cyBhIGxpc3Qgb2YgZGV0ZWN0ZWQgYmxvY2tzLlxuICAvLyBUaGUgYmxvY2sgbGlzdCBsZXRzIHVzIHJlbmRlciBcIkluc2VydCBhcyBjZWxsXCIgYnV0dG9ucyB1bmRlciB0aGUgbWVzc2FnZS5cbiAgY29uc3QgYmxvY2tzOiBDb3BpbG90Q29kZUJsb2NrW10gPSBbXTtcbiAgY29uc3QgcmUgPSAvYGBgKHNxbHxweXRob24pXFxuKFtcXHNcXFNdKj8pYGBgL2dpO1xuICBsZXQgbTogUmVnRXhwRXhlY0FycmF5IHwgbnVsbDtcbiAgd2hpbGUgKChtID0gcmUuZXhlYyh0ZXh0KSkgIT09IG51bGwpIHtcbiAgICBibG9ja3MucHVzaCh7IGxhbmd1YWdlOiBtWzFdLnRvTG93ZXJDYXNlKCkgYXMgJ3NxbCcgfCAncHl0aG9uJywgc291cmNlOiBtWzJdLnRyaW0oKSB9KTtcbiAgfVxuICByZXR1cm4gW3sgdGV4dCwgYmxvY2tzIH1dO1xufVxuXG4vLyBUaGUgY2hhdCBzaG93cyB0aGUgcHJvc2UgQVJPVU5EIHRoZSBjb2RlIGJsb2Nrcywgbm90IHRoZSBjb2RlIGl0c2VsZiDigJRcbi8vIHRoZSBjb2RlIGxpdmVzIGluIGNvcGlsb3QuaXB5bmIuIFN0cmlwIGZlbmNlZCBibG9ja3MgKyBjb2xsYXBzZSB3aGl0ZXNwYWNlLlxuZnVuY3Rpb24gc3RyaXBDb2RlRmVuY2VzKHRleHQ6IHN0cmluZyk6IHN0cmluZyB7XG4gIHJldHVybiB0ZXh0XG4gICAgLnJlcGxhY2UoL2BgYChzcWx8cHl0aG9uKVxcbltcXHNcXFNdKj9gYGAvZ2ksICcnKVxuICAgIC5yZXBsYWNlKC9cXG57Myx9L2csICdcXG5cXG4nKVxuICAgIC50cmltKCk7XG59XG5cbi8vIFB1bGwgdGhlIGN1cnJlbnQgY29waWxvdC5pcHluYiBjZWxscyBzbyB0aGUgbW9kZWwgY2FuIHJlZmVyIHRvIC8gcmVmYWN0b3Jcbi8vIHRoZW0gaW4gdGhlIG5leHQgdHVybi4gV2UgcmV0dXJuIGJvdGggYSBtb2RlbC1mYWNpbmcgcHJvbXB0IGZyYWdtZW50IGFuZFxuLy8gdGhlIHJhdyBjZWxsIHNvdXJjZXMgKGZvciBmdXR1cmUgVVggbGlrZSBcInNlbGVjdCBjZWxsIHRvIGVkaXRcIikuXG5hc3luYyBmdW5jdGlvbiBmZXRjaE5vdGVib29rQ29udGV4dCgpOiBQcm9taXNlPHtcbiAgcHJvbXB0OiBzdHJpbmc7XG4gIGNlbGxDb3VudDogbnVtYmVyO1xufT4ge1xuICAvLyBIYXJkIDQgcyBjZWlsaW5nIOKAlCBpZiBKdXB5dGVyIGlzIHJlc3RhcnRpbmcgLyBzbG93LCBzaGlwIHRoZSBxdWVzdGlvblxuICAvLyB3aXRob3V0IGNvbnRleHQgcmF0aGVyIHRoYW4gYmxvY2tpbmcgdGhlIGNoYXQgaW5kZWZpbml0ZWx5LlxuICBjb25zdCBjdHJsID0gbmV3IEFib3J0Q29udHJvbGxlcigpO1xuICBjb25zdCB0aW1lciA9IHdpbmRvdy5zZXRUaW1lb3V0KCgpID0+IGN0cmwuYWJvcnQoKSwgNDAwMCk7XG4gIHRyeSB7XG4gICAgY29uc3QgciA9IGF3YWl0IGZldGNoKGAvanVweXRlci9hcGkvY29udGVudHMvJHtDT1BJTE9UX05PVEVCT09LfWAsIHtcbiAgICAgIGhlYWRlcnM6IHsgQXV0aG9yaXphdGlvbjogYHRva2VuICR7SlVQWVRFUl9UT0tFTn1gIH0sXG4gICAgICBzaWduYWw6IGN0cmwuc2lnbmFsLFxuICAgIH0pO1xuICAgIGlmICghci5vaykgcmV0dXJuIHsgcHJvbXB0OiAnJywgY2VsbENvdW50OiAwIH07XG4gICAgY29uc3QgbmIgPSBhd2FpdCByLmpzb24oKTtcbiAgICBjb25zdCBjZWxsczogYW55W10gPSBuYj8uY29udGVudD8uY2VsbHMgPz8gW107XG4gICAgY29uc3QgY29kZUNlbGxzID0gY2VsbHNcbiAgICAgIC5maWx0ZXIoKGMpID0+IGMuY2VsbF90eXBlID09PSAnY29kZScpXG4gICAgICAubWFwKChjKSA9PiAoQXJyYXkuaXNBcnJheShjLnNvdXJjZSkgPyBjLnNvdXJjZS5qb2luKCcnKSA6IGMuc291cmNlID8/ICcnKSlcbiAgICAgIC5tYXAoKHM6IHN0cmluZykgPT4gcy50cmltKCkpXG4gICAgICAuZmlsdGVyKChzKSA9PiBzLmxlbmd0aCA+IDApO1xuICAgIGlmIChjb2RlQ2VsbHMubGVuZ3RoID09PSAwKSByZXR1cm4geyBwcm9tcHQ6ICcnLCBjZWxsQ291bnQ6IDAgfTtcbiAgICBjb25zdCBib2R5ID0gY29kZUNlbGxzXG4gICAgICAubWFwKChzLCBpKSA9PiBgLS0tIENlbGwgIyR7aSArIDF9IC0tLVxcbiR7c31gKVxuICAgICAgLmpvaW4oJ1xcblxcbicpO1xuICAgIGNvbnN0IHByb21wdCA9XG4gICAgICBg7ZiE7J6sICR7Q09QSUxPVF9OT1RFQk9PS30g7JeQIOuTpOyWtOyeiOuKlCDsvZTrk5wg7IWA7J6F64uI64ukLiBgICtcbiAgICAgIGDsgqzsmqnsnpDsnZgg7IOIIOyalOyyreydtCBcIuydtCDsvZTrk5wg7IiY7KCVL+umrO2Mqe2GoOungS/snbTslrTshJxcIiDqsJnsnYAg7J2Y64+E66m0IGAgK1xuICAgICAgYOydtCDshYDrk6TsnYQg6riw7KSA7Jy866GcIOuLte2VmOyEuOyalC4g7IOIIOyFgOydtCDtlYTsmpTtlZjrqbQg7IOIIOy9lOuTnCDruJTroZ3snYQg7LaU6rCA7ZWY7IS47JqULlxcblxcbmAgK1xuICAgICAgYm9keTtcbiAgICByZXR1cm4geyBwcm9tcHQsIGNlbGxDb3VudDogY29kZUNlbGxzLmxlbmd0aCB9O1xuICB9IGNhdGNoIHtcbiAgICByZXR1cm4geyBwcm9tcHQ6ICcnLCBjZWxsQ291bnQ6IDAgfTtcbiAgfSBmaW5hbGx5IHtcbiAgICB3aW5kb3cuY2xlYXJUaW1lb3V0KHRpbWVyKTtcbiAgfVxufVxuXG5mdW5jdGlvbiBDb3BpbG90UGFuZWwoe1xuICBjb25uZWN0aW9uSWQsXG4gIG9uQ2VsbEluc2VydGVkLFxufToge1xuICBjb25uZWN0aW9uSWQ6IHN0cmluZyB8IG51bGw7XG4gIG9uQ2VsbEluc2VydGVkPzogKCkgPT4gdm9pZDtcbn0pIHtcbiAgY29uc3QgW2hpc3RvcnksIHNldEhpc3RvcnldID0gdXNlU3RhdGU8Q29waWxvdE1zZ1tdPihbXSk7XG4gIGNvbnN0IFtpbnB1dCwgc2V0SW5wdXRdID0gdXNlU3RhdGUoJycpO1xuICBjb25zdCBbcGVuZGluZywgc2V0UGVuZGluZ10gPSB1c2VTdGF0ZTxzdHJpbmc+KCcnKTtcbiAgY29uc3QgW2J1c3ksIHNldEJ1c3ldID0gdXNlU3RhdGUoZmFsc2UpO1xuICBjb25zdCBbZXJyb3IsIHNldEVycm9yXSA9IHVzZVN0YXRlPHN0cmluZyB8IG51bGw+KG51bGwpO1xuICBjb25zdCBbcHJvdmlkZXJOYW1lLCBzZXRQcm92aWRlck5hbWVdID0gdXNlU3RhdGU8c3RyaW5nPignJyk7XG4gIGNvbnN0IFtsYXN0SW5zZXJ0LCBzZXRMYXN0SW5zZXJ0XSA9IHVzZVN0YXRlPHN0cmluZyB8IG51bGw+KG51bGwpO1xuICAvLyBUcmFjayB3aGljaCAobWVzc2FnZUlkeCwgYmxvY2tJZHgpIHBhaXJzIGhhdmUgYWxyZWFkeSBhdXRvLWluc2VydGVkIHNvXG4gIC8vIHJlLXJlbmRlcnMgZG9uJ3QgZmlyZSBkdXBsaWNhdGUgUFVUL2F1ZGl0IHJvdW5kLXRyaXBzIGZvciB0aGUgc2FtZSBibG9jay5cbiAgY29uc3QgaW5zZXJ0ZWRSZWYgPSB1c2VSZWY8U2V0PHN0cmluZz4+KG5ldyBTZXQoKSk7XG4gIC8vIFRoZSBzY3JvbGxpbmcgY2hhdCBjb250YWluZXIuIFdlIGZvbGxvdyB0aGUgc3RyZWFtIG9ubHkgd2hpbGUgdGhlIHVzZXIgaXNcbiAgLy8gYWxyZWFkeSBwaW5uZWQgdG8gdGhlIGJvdHRvbSDigJQgaWYgdGhleSBzY3JvbGwgdXAgdG8gcmUtcmVhZCBhIHBhc3RcbiAgLy8gcXVlc3Rpb24sIHN0cmVhbWluZyBjaHVua3MgbXVzdCBOT1QgeWFuayB0aGUgdmlldyBiYWNrIGRvd24uXG4gIGNvbnN0IGNoYXRSZWYgPSB1c2VSZWY8SFRNTERpdkVsZW1lbnQgfCBudWxsPihudWxsKTtcbiAgY29uc3QgW2F1dG9Gb2xsb3csIHNldEF1dG9Gb2xsb3ddID0gdXNlU3RhdGUodHJ1ZSk7XG5cbiAgdXNlRWZmZWN0KCgpID0+IHtcbiAgICBmZXRjaCgnL2FwaS9jb3BpbG90L3Byb3ZpZGVyJylcbiAgICAgIC50aGVuKChyKSA9PiAoci5vayA/IHIuanNvbigpIDogbnVsbCkpXG4gICAgICAudGhlbigoaikgPT4gaiAmJiBzZXRQcm92aWRlck5hbWUoai5wcm92aWRlcikpXG4gICAgICAuY2F0Y2goKCkgPT4ge30pO1xuICB9LCBbXSk7XG5cbiAgdXNlRWZmZWN0KCgpID0+IHtcbiAgICBpZiAoIWF1dG9Gb2xsb3cpIHJldHVybjtcbiAgICBjb25zdCBlbCA9IGNoYXRSZWYuY3VycmVudDtcbiAgICBpZiAoZWwpIGVsLnNjcm9sbFRvcCA9IGVsLnNjcm9sbEhlaWdodDtcbiAgfSwgW2hpc3RvcnksIHBlbmRpbmcsIGF1dG9Gb2xsb3ddKTtcblxuICBjb25zdCBvbkNoYXRTY3JvbGwgPSAoKSA9PiB7XG4gICAgY29uc3QgZWwgPSBjaGF0UmVmLmN1cnJlbnQ7XG4gICAgaWYgKCFlbCkgcmV0dXJuO1xuICAgIC8vIDI0IHB4IHRvbGVyYW5jZSBzbyBhIHRpbnkgcm91bmRpbmcgZ2FwIHN0aWxsIGNvdW50cyBhcyBcImF0IHRoZSBib3R0b21cIi5cbiAgICBjb25zdCBhdEJvdHRvbSA9IGVsLnNjcm9sbEhlaWdodCAtIGVsLnNjcm9sbFRvcCAtIGVsLmNsaWVudEhlaWdodCA8IDI0O1xuICAgIHNldEF1dG9Gb2xsb3coYXRCb3R0b20pO1xuICB9O1xuXG4gIGNvbnN0IHNjcm9sbFRvTGF0ZXN0ID0gKCkgPT4ge1xuICAgIGNvbnN0IGVsID0gY2hhdFJlZi5jdXJyZW50O1xuICAgIGlmICghZWwpIHJldHVybjtcbiAgICBlbC5zY3JvbGxUb3AgPSBlbC5zY3JvbGxIZWlnaHQ7XG4gICAgc2V0QXV0b0ZvbGxvdyh0cnVlKTtcbiAgfTtcblxuICBjb25zdCBzZW5kID0gYXN5bmMgKCkgPT4ge1xuICAgIGlmICghaW5wdXQudHJpbSgpIHx8IGJ1c3kpIHJldHVybjtcbiAgICBzZXRFcnJvcihudWxsKTtcbiAgICBjb25zdCBxdWVzdGlvbiA9IGlucHV0LnRyaW0oKTtcbiAgICBzZXRJbnB1dCgnJyk7XG4gICAgc2V0QnVzeSh0cnVlKTtcbiAgICAvLyBTZW5kaW5nIGEgbmV3IHF1ZXN0aW9uIGlzIGFuIGV4cGxpY2l0IFwiZm9sbG93IHRoZSBzdHJlYW1cIiBpbnRlbnQg4oCUIHJlLWFybVxuICAgIC8vIGF1dG8tc2Nyb2xsIGV2ZW4gaWYgdGhlIHVzZXIgaGFkIHNjcm9sbGVkIHVwIHRvIHJlYWQgdGhlIHByZXZpb3VzIGFuc3dlci5cbiAgICBzZXRBdXRvRm9sbG93KHRydWUpO1xuICAgIHNldEhpc3RvcnkoKGgpID0+IFsuLi5oLCB7IHJvbGU6ICd1c2VyJywgY29udGVudDogcXVlc3Rpb24gfV0pO1xuICAgIHNldFBlbmRpbmcoJycpO1xuXG4gICAgdHJ5IHtcbiAgICAgIC8vIFB1bGwgdGhlIGxpdmUgbm90ZWJvb2sgY29udGVudHMgc28gZm9sbG93LXVwIHJlcXVlc3RzIGxpa2UgXCLsnbQg7L2U65OcXG4gICAgICAvLyDrpqztjKnthqDrp4Eg7ZW07KSYXCIgY2FycnkgdGhlIGFjdHVhbCBjZWxscyB0aGUgdXNlciBpcyBsb29raW5nIGF0LiBUaGVcbiAgICAgIC8vIGNoYXQgVUkgc3RpbGwgc2hvd3MgdGhlIHVzZXIncyBvcmlnaW5hbCBxdWVzdGlvbiDigJQgb25seSB0aGUgQVBJXG4gICAgICAvLyBwYXlsb2FkIGlzIGF1Z21lbnRlZC5cbiAgICAgIGNvbnN0IHsgcHJvbXB0OiBuYlByb21wdCB9ID0gYXdhaXQgZmV0Y2hOb3RlYm9va0NvbnRleHQoKTtcbiAgICAgIGNvbnN0IGF1Z21lbnRlZFF1ZXN0aW9uID0gbmJQcm9tcHRcbiAgICAgICAgPyBgJHtuYlByb21wdH1cXG5cXG4tLS1cXG5cXG7sgqzsmqnsnpAg7JqU7LKtOlxcbiR7cXVlc3Rpb259YFxuICAgICAgICA6IHF1ZXN0aW9uO1xuXG4gICAgICBjb25zdCByZXMgPSBhd2FpdCBmZXRjaCgnL2FwaS9jb3BpbG90L2NoYXQnLCB7XG4gICAgICAgIG1ldGhvZDogJ1BPU1QnLFxuICAgICAgICBoZWFkZXJzOiB7ICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbicgfSxcbiAgICAgICAgYm9keTogSlNPTi5zdHJpbmdpZnkoe1xuICAgICAgICAgIHF1ZXN0aW9uOiBhdWdtZW50ZWRRdWVzdGlvbixcbiAgICAgICAgICBoaXN0b3J5LFxuICAgICAgICAgIGNvbm5lY3Rpb25faWQ6IGNvbm5lY3Rpb25JZCxcbiAgICAgICAgfSksXG4gICAgICB9KTtcbiAgICAgIGlmICghcmVzLm9rIHx8ICFyZXMuYm9keSkge1xuICAgICAgICBjb25zdCBib2R5ID0gYXdhaXQgcmVzLmpzb24oKS5jYXRjaCgoKSA9PiAoe30pKTtcbiAgICAgICAgdGhyb3cgbmV3IEVycm9yKGJvZHkuZGV0YWlsID8/IGAke3Jlcy5zdGF0dXN9ICR7cmVzLnN0YXR1c1RleHR9YCk7XG4gICAgICB9XG4gICAgICBjb25zdCByZWFkZXIgPSByZXMuYm9keS5nZXRSZWFkZXIoKTtcbiAgICAgIGNvbnN0IGRlYyA9IG5ldyBUZXh0RGVjb2RlcigpO1xuICAgICAgbGV0IGJ1ZiA9ICcnO1xuICAgICAgbGV0IGFzc2VtYmxlZCA9ICcnO1xuICAgICAgd2hpbGUgKHRydWUpIHtcbiAgICAgICAgY29uc3QgeyB2YWx1ZSwgZG9uZSB9ID0gYXdhaXQgcmVhZGVyLnJlYWQoKTtcbiAgICAgICAgaWYgKGRvbmUpIGJyZWFrO1xuICAgICAgICBidWYgKz0gZGVjLmRlY29kZSh2YWx1ZSwgeyBzdHJlYW06IHRydWUgfSk7XG4gICAgICAgIGxldCBubDogbnVtYmVyO1xuICAgICAgICB3aGlsZSAoKG5sID0gYnVmLmluZGV4T2YoJ1xcbicpKSA+PSAwKSB7XG4gICAgICAgICAgY29uc3QgbGluZSA9IGJ1Zi5zbGljZSgwLCBubCkudHJpbSgpO1xuICAgICAgICAgIGJ1ZiA9IGJ1Zi5zbGljZShubCArIDEpO1xuICAgICAgICAgIGlmICghbGluZSkgY29udGludWU7XG4gICAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgIGNvbnN0IG9iaiA9IEpTT04ucGFyc2UobGluZSk7XG4gICAgICAgICAgICBpZiAob2JqLmVycm9yKSB7XG4gICAgICAgICAgICAgIHRocm93IG5ldyBFcnJvcihvYmouZXJyb3IpO1xuICAgICAgICAgICAgfVxuICAgICAgICAgICAgaWYgKG9iai5jaHVuaykge1xuICAgICAgICAgICAgICBhc3NlbWJsZWQgKz0gb2JqLmNodW5rO1xuICAgICAgICAgICAgICBzZXRQZW5kaW5nKGFzc2VtYmxlZCk7XG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSBjYXRjaCAoZSkge1xuICAgICAgICAgICAgLy8gUGFzcyB0aHJvdWdoIHRvIHRoZSBjYXRjaCBiZWxvdyBpZiBpdCdzIGEgcmVhbCBlcnJvci5cbiAgICAgICAgICAgIGlmICgoZSBhcyBFcnJvcikubWVzc2FnZSAhPT0gJ0pTT04ucGFyc2UnKSB0aHJvdyBlO1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuICAgICAgLy8gQ29tbWl0IHRoZSBhc3NlbWJsZWQgYW5zd2VyIHRvIGhpc3RvcnksIHRoZW4gYXV0by1pbnNlcnQgZXZlcnkgY29kZVxuICAgICAgLy8gYmxvY2sgd2UgZGV0ZWN0LiBUaGUgdXNlciBleHBsaWNpdGx5IGFza2VkIGZvciBcIm1ha2UgdGhlIGNvZGVcIiDihpIgdGhlXG4gICAgICAvLyBjb2RlIGxhbmRzIGluIGNvcGlsb3QuaXB5bmIgd2l0aG91dCBhbiBleHRyYSBjbGljay5cbiAgICAgIGxldCBhc3Npc3RhbnRJZHggPSAtMTtcbiAgICAgIHNldEhpc3RvcnkoKGgpID0+IHtcbiAgICAgICAgYXNzaXN0YW50SWR4ID0gaC5sZW5ndGg7XG4gICAgICAgIHJldHVybiBbLi4uaCwgeyByb2xlOiAnYXNzaXN0YW50JywgY29udGVudDogYXNzZW1ibGVkIH1dO1xuICAgICAgfSk7XG4gICAgICBzZXRQZW5kaW5nKCcnKTtcbiAgICAgIGNvbnN0IGJsb2NrcyA9IHNwbGl0TWFya2Rvd25Db2RlQmxvY2tzKGFzc2VtYmxlZClbMF0uYmxvY2tzO1xuICAgICAgZm9yIChsZXQgayA9IDA7IGsgPCBibG9ja3MubGVuZ3RoOyBrKyspIHtcbiAgICAgICAgY29uc3Qga2V5ID0gYCR7YXNzaXN0YW50SWR4fToke2t9YDtcbiAgICAgICAgaWYgKGluc2VydGVkUmVmLmN1cnJlbnQuaGFzKGtleSkpIGNvbnRpbnVlO1xuICAgICAgICBpbnNlcnRlZFJlZi5jdXJyZW50LmFkZChrZXkpO1xuICAgICAgICAvLyBEb24ndCBmYWlsIHRoZSB3aG9sZSByZXBseSBpZiBhbnkgb25lIGluc2VydCBibG93cyB1cCDigJQgdGhlIG1hbnVhbFxuICAgICAgICAvLyBcIuuLpOyLnCDsgr3snoVcIiBidXR0b24gaXMgc3RpbGwgcmVuZGVyZWQgYXMgYSBmYWxsYmFjay5cbiAgICAgICAgdHJ5IHtcbiAgICAgICAgICBhd2FpdCBvbkluc2VydChibG9ja3Nba10pO1xuICAgICAgICB9IGNhdGNoIHtcbiAgICAgICAgICAvKiBzdXJmYWNlZCBpbmxpbmUgdmlhIHNldEVycm9yIGFscmVhZHkgKi9cbiAgICAgICAgfVxuICAgICAgfVxuICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgIHNldEVycm9yKChlIGFzIEVycm9yKS5tZXNzYWdlKTtcbiAgICB9IGZpbmFsbHkge1xuICAgICAgc2V0QnVzeShmYWxzZSk7XG4gICAgfVxuICB9O1xuXG4gIGNvbnN0IG9uSW5zZXJ0ID0gYXN5bmMgKGJsb2NrOiBDb3BpbG90Q29kZUJsb2NrKSA9PiB7XG4gICAgc2V0RXJyb3IobnVsbCk7XG4gICAgdHJ5IHtcbiAgICAgIGF3YWl0IGFwcGVuZENlbGxUb0NvcGlsb3ROb3RlYm9vayhibG9jay5sYW5ndWFnZSwgYmxvY2suc291cmNlKTtcbiAgICAgIC8vIFJlY29yZCB0aGUgY2VsbCBpbnNlcnRpb24gaW4gdGhlIGF1ZGl0IHRyYWlsIHNvIHRoZSBBdWRpdG9yIGNhbiBzZWVcbiAgICAgIC8vIGV4YWN0bHkgd2hpY2ggZ2VuZXJhdGVkIGNvZGUgbGFuZGVkIGluIHdoaWNoIG5vdGVib29rLlxuICAgICAgdHJ5IHtcbiAgICAgICAgYXdhaXQgZmV0Y2goJy9hcGkvY29waWxvdC9jZWxsLWluc2VydGVkJywge1xuICAgICAgICAgIG1ldGhvZDogJ1BPU1QnLFxuICAgICAgICAgIGhlYWRlcnM6IHsgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyB9LFxuICAgICAgICAgIGJvZHk6IEpTT04uc3RyaW5naWZ5KHtcbiAgICAgICAgICAgIG5vdGVib29rX3BhdGg6IENPUElMT1RfTk9URUJPT0ssXG4gICAgICAgICAgICBsYW5ndWFnZTogYmxvY2subGFuZ3VhZ2UsXG4gICAgICAgICAgICBzb3VyY2VfbGVuZ3RoOiBibG9jay5zb3VyY2UubGVuZ3RoLFxuICAgICAgICAgICAgY29ubmVjdGlvbl9pZDogY29ubmVjdGlvbklkLFxuICAgICAgICAgIH0pLFxuICAgICAgICB9KTtcbiAgICAgIH0gY2F0Y2gge1xuICAgICAgICAvLyBBdWRpdCBmYWlsdXJlIG11c3Qgbm90IGJyZWFrIHRoZSB1c2VyLXZpc2libGUgYWN0aW9uOyB0aGUgdXNlclxuICAgICAgICAvLyBzZWVzIHRoZSBzdWNjZXNzIHRvYXN0LCB0aGUgYmFja2VuZCBsb2dzIHRoZSBhdWRpdCBmYWlsdXJlLlxuICAgICAgfVxuICAgICAgc2V0TGFzdEluc2VydChgJHtibG9jay5sYW5ndWFnZS50b1VwcGVyQ2FzZSgpfSDshYDsnbQgY29waWxvdC5pcHluYiDsl5Ag7LaU6rCA65CoYCk7XG4gICAgICB3aW5kb3cuc2V0VGltZW91dCgoKSA9PiBzZXRMYXN0SW5zZXJ0KG51bGwpLCA0MDAwKTtcbiAgICAgIC8vIFRlbGwgdGhlIHBhcmVudCB0byBidW1wIHRoZSBpZnJhbWUgcmVsb2FkIHRva2VuIHNvIEp1cHl0ZXJMYWIgcmUtcmVhZHNcbiAgICAgIC8vIGNvcGlsb3QuaXB5bmIgZnJvbSBkaXNrIGFuZCB0aGUgbmV3IGNlbGwgYmVjb21lcyB2aXNpYmxlIGltbWVkaWF0ZWx5LlxuICAgICAgb25DZWxsSW5zZXJ0ZWQ/LigpO1xuICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgIHNldEVycm9yKGDshYAg7IK97J6FIOyLpO2MqDogJHsoZSBhcyBFcnJvcikubWVzc2FnZX1gKTtcbiAgICB9XG4gIH07XG5cbiAgcmV0dXJuIChcbiAgICAvLyBUaGUgQ29waWxvdFBhbmVsIGxpdmVzIGluc2lkZSBBcHBTaGVsbC5NYWluLCB3aGljaCBNYW50aW5lIHNpemVzIHZpYVxuICAgIC8vIGEgbGF5ZXJlZCBsYXlvdXQgdGhhdCBicmVha3MgbmHDr3ZlIGhlaWdodDoxMDAlIGNoYWlucy4gUGluIHRoZSBwYW5lbFxuICAgIC8vIGl0c2VsZiB0byBhIHZpZXdwb3J0LXJlbGF0aXZlIGhlaWdodCBzbyB0aGUgY2hhdCBsaXN0IGFsd2F5cyBnZXRzIGFcbiAgICAvLyBib3VuZGVkIGJveCB0byBzY3JvbGwgaW5zaWRlLlxuICAgIC8vICAgODggcHgg4omIIFNQQSBoZWFkZXIgKDQ0KSArIHBhbmVsLWhlYWRlciAofjQ0KSBhYm92ZSB1cy5cbiAgICA8U3RhY2tcbiAgICAgIHA9XCJzbVwiXG4gICAgICBnYXA9XCJzbVwiXG4gICAgICBzdHlsZT17eyBoZWlnaHQ6ICdjYWxjKDEwMHZoIC0gODhweCknLCBvdmVyZmxvdzogJ2hpZGRlbicgfX1cbiAgICA+XG4gICAgICA8R3JvdXAganVzdGlmeT1cInNwYWNlLWJldHdlZW5cIj5cbiAgICAgICAgPFRpdGxlIG9yZGVyPXs1fT7wn6SWIOu2hOyEnSDsvZTtjIzsnbzrn788L1RpdGxlPlxuICAgICAgICB7cHJvdmlkZXJOYW1lICYmIDxCYWRnZSB2YXJpYW50PVwibGlnaHRcIj57cHJvdmlkZXJOYW1lfTwvQmFkZ2U+fVxuICAgICAgPC9Hcm91cD5cblxuICAgICAgPGRpdlxuICAgICAgICByZWY9e2NoYXRSZWZ9XG4gICAgICAgIG9uU2Nyb2xsPXtvbkNoYXRTY3JvbGx9XG4gICAgICAgIGRhdGEtdGVzdGlkPVwiY29waWxvdC1jaGF0XCJcbiAgICAgICAgc3R5bGU9e3tcbiAgICAgICAgICBmbGV4OiAxLFxuICAgICAgICAgIG1pbkhlaWdodDogMCxcbiAgICAgICAgICBvdmVyZmxvd1k6ICdhdXRvJyxcbiAgICAgICAgICBwYWRkaW5nUmlnaHQ6IDQsXG4gICAgICAgICAgZGlzcGxheTogJ2ZsZXgnLFxuICAgICAgICAgIGZsZXhEaXJlY3Rpb246ICdjb2x1bW4nLFxuICAgICAgICAgIGdhcDogOCxcbiAgICAgICAgICBwb3NpdGlvbjogJ3JlbGF0aXZlJyxcbiAgICAgICAgfX1cbiAgICAgID5cbiAgICAgICAge2hpc3RvcnkubGVuZ3RoID09PSAwICYmICFwZW5kaW5nICYmIChcbiAgICAgICAgICA8VGV4dCBzaXplPVwic21cIiBjPVwiZGltbWVkXCI+XG4gICAgICAgICAgICDsmIg6IFwi7KeA64KcIDMw7J28IOunpOy2nCDsg4HsnIQg64+E7IucIDXqsJwg7JWM66Ck7KSYXCIg4oCUIOy7pOuEpeyFmOydhCDqs6DrpbTrqbQg7Iqk7YKk66eIIOy7qO2FjeyKpO2KuOulvCDsnpDrj5kg7KO87J6F7ZWp64uI64ukLlxuICAgICAgICAgICAg7J2R64u17JeQIFNRTC9QeXRob24g7L2U65Oc6rCAIO2PrO2VqOuQmOuptCDsnpDrj5nsnLzroZwge0NPUElMT1RfTk9URUJPT0t9IOyXkCDshYDsnYQg7LaU6rCA7ZWp64uI64ukLlxuICAgICAgICAgIDwvVGV4dD5cbiAgICAgICAgKX1cblxuICAgICAgICB7aGlzdG9yeS5tYXAoKG0sIGkpID0+IHtcbiAgICAgICAgICBjb25zdCBibG9ja3MgPVxuICAgICAgICAgICAgbS5yb2xlID09PSAnYXNzaXN0YW50JyA/IHNwbGl0TWFya2Rvd25Db2RlQmxvY2tzKG0uY29udGVudClbMF0uYmxvY2tzIDogW107XG4gICAgICAgICAgY29uc3QgbmFycmF0aW9uID1cbiAgICAgICAgICAgIG0ucm9sZSA9PT0gJ2Fzc2lzdGFudCcgJiYgYmxvY2tzLmxlbmd0aCA+IDBcbiAgICAgICAgICAgICAgPyBzdHJpcENvZGVGZW5jZXMobS5jb250ZW50KVxuICAgICAgICAgICAgICA6IG0uY29udGVudDtcbiAgICAgICAgICByZXR1cm4gKFxuICAgICAgICAgICAgPENhcmQga2V5PXtpfSB3aXRoQm9yZGVyIHBhZGRpbmc9XCJzbVwiIHJhZGl1cz1cInNtXCI+XG4gICAgICAgICAgICAgIDxHcm91cCBnYXA9XCJ4c1wiIG1iPXs0fT5cbiAgICAgICAgICAgICAgICA8QmFkZ2Ugc2l6ZT1cInhzXCIgY29sb3I9e20ucm9sZSA9PT0gJ3VzZXInID8gJ2JsdWUnIDogJ2dyYXBlJ30+XG4gICAgICAgICAgICAgICAgICB7bS5yb2xlID09PSAndXNlcicgPyAn64KYJyA6ICfsvZTtjIzsnbzrn78nfVxuICAgICAgICAgICAgICAgIDwvQmFkZ2U+XG4gICAgICAgICAgICAgIDwvR3JvdXA+XG4gICAgICAgICAgICAgIHsvKiBDb2RlIGFuc3dlcnM6IHNob3cgdGhlIHByb3NlIGFyb3VuZCB0aGUgY29kZSAoaWYgYW55KSwgbm90XG4gICAgICAgICAgICAgICAgIHRoZSBjb2RlIGl0c2VsZiDigJQgdGhlIGNvZGUgbGl2ZXMgaW4gY29waWxvdC5pcHluYi4gUHVyZS10ZXh0XG4gICAgICAgICAgICAgICAgIGFuc3dlcnMgKFwi7Iqk7YKk66eI66W8IOyVjOugpOyjvOyEuOyalFwiIOuTsSkgYXJlIHNob3duIHVuY2hhbmdlZC4gKi99XG4gICAgICAgICAgICAgIHtuYXJyYXRpb24gJiYgKFxuICAgICAgICAgICAgICAgIDxUZXh0IHNpemU9XCJzbVwiIHN0eWxlPXt7IHdoaXRlU3BhY2U6ICdwcmUtd3JhcCcgfX0+XG4gICAgICAgICAgICAgICAgICB7bmFycmF0aW9ufVxuICAgICAgICAgICAgICAgIDwvVGV4dD5cbiAgICAgICAgICAgICAgKX1cbiAgICAgICAgICAgICAge20ucm9sZSA9PT0gJ2Fzc2lzdGFudCcgJiYgYmxvY2tzLmxlbmd0aCA+IDAgJiYgKFxuICAgICAgICAgICAgICAgIDxHcm91cCBtdD17Nn0gZ2FwPVwieHNcIj5cbiAgICAgICAgICAgICAgICAgIDxCYWRnZSB2YXJpYW50PVwib3V0bGluZVwiIGNvbG9yPVwiZ3JlZW5cIiBzaXplPVwic21cIj5cbiAgICAgICAgICAgICAgICAgICAg4pyFIHtibG9ja3MubGVuZ3RofeqwnCDshYDsnbQge0NPUElMT1RfTk9URUJPT0t9IOyXkCDsnpDrj5kg7LaU6rCA65CoXG4gICAgICAgICAgICAgICAgICA8L0JhZGdlPlxuICAgICAgICAgICAgICAgICAge2Jsb2Nrcy5tYXAoKGIsIGspID0+IChcbiAgICAgICAgICAgICAgICAgICAgPEJhZGdlXG4gICAgICAgICAgICAgICAgICAgICAga2V5PXtrfVxuICAgICAgICAgICAgICAgICAgICAgIHZhcmlhbnQ9XCJsaWdodFwiXG4gICAgICAgICAgICAgICAgICAgICAgY29sb3I9e2IubGFuZ3VhZ2UgPT09ICdzcWwnID8gJ3RlYWwnIDogJ29yYW5nZSd9XG4gICAgICAgICAgICAgICAgICAgICAgc2l6ZT1cInNtXCJcbiAgICAgICAgICAgICAgICAgICAgPlxuICAgICAgICAgICAgICAgICAgICAgIHtiLmxhbmd1YWdlLnRvVXBwZXJDYXNlKCl9ICN7ayArIDF9XG4gICAgICAgICAgICAgICAgICAgIDwvQmFkZ2U+XG4gICAgICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgICAgICAgIDxCdXR0b25cbiAgICAgICAgICAgICAgICAgICAgc2l6ZT1cInhzXCJcbiAgICAgICAgICAgICAgICAgICAgdmFyaWFudD1cInN1YnRsZVwiXG4gICAgICAgICAgICAgICAgICAgIG9uQ2xpY2s9eygpID0+IGJsb2Nrcy5mb3JFYWNoKChiKSA9PiBvbkluc2VydChiKSl9XG4gICAgICAgICAgICAgICAgICA+XG4gICAgICAgICAgICAgICAgICAgIPCflIEg64uk7IucIOyCveyehVxuICAgICAgICAgICAgICAgICAgPC9CdXR0b24+XG4gICAgICAgICAgICAgICAgPC9Hcm91cD5cbiAgICAgICAgICAgICAgKX1cbiAgICAgICAgICAgIDwvQ2FyZD5cbiAgICAgICAgICApO1xuICAgICAgICB9KX1cblxuICAgICAgICB7cGVuZGluZyAmJiAoXG4gICAgICAgICAgPENhcmQgd2l0aEJvcmRlciBwYWRkaW5nPVwic21cIiByYWRpdXM9XCJzbVwiIGJnPVwiZ3JheS4wXCI+XG4gICAgICAgICAgICA8R3JvdXAgZ2FwPVwieHNcIiBtYj17NH0+XG4gICAgICAgICAgICAgIDxMb2FkZXIgc2l6ZT1cInhzXCIgLz5cbiAgICAgICAgICAgICAgPEJhZGdlIHNpemU9XCJ4c1wiIGNvbG9yPVwiZ3JhcGVcIj7svZTtjIzsnbzrn788L0JhZGdlPlxuICAgICAgICAgICAgPC9Hcm91cD5cbiAgICAgICAgICAgIDxUZXh0IHNpemU9XCJzbVwiIHN0eWxlPXt7IHdoaXRlU3BhY2U6ICdwcmUtd3JhcCcgfX0+e3BlbmRpbmd9PC9UZXh0PlxuICAgICAgICAgIDwvQ2FyZD5cbiAgICAgICAgKX1cbiAgICAgIDwvZGl2PlxuXG4gICAgICB7IWF1dG9Gb2xsb3cgJiYgKFxuICAgICAgICA8R3JvdXAganVzdGlmeT1cImNlbnRlclwiPlxuICAgICAgICAgIDxCdXR0b24gc2l6ZT1cInhzXCIgdmFyaWFudD1cImxpZ2h0XCIgb25DbGljaz17c2Nyb2xsVG9MYXRlc3R9PlxuICAgICAgICAgICAg4pa8IOy1nOyLoCDrqZTsi5zsp4DroZxcbiAgICAgICAgICA8L0J1dHRvbj5cbiAgICAgICAgPC9Hcm91cD5cbiAgICAgICl9XG4gICAgICB7ZXJyb3IgJiYgPE5vdGlmaWNhdGlvbiBjb2xvcj1cInJlZFwiIHRpdGxlPVwi7Iuk7YyoXCIgb25DbG9zZT17KCkgPT4gc2V0RXJyb3IobnVsbCl9PntlcnJvcn08L05vdGlmaWNhdGlvbj59XG4gICAgICB7bGFzdEluc2VydCAmJiA8Tm90aWZpY2F0aW9uIGNvbG9yPVwiZ3JlZW5cIiB0aXRsZT1cIuyCveyehSDsmYTro4xcIiBvbkNsb3NlPXsoKSA9PiBzZXRMYXN0SW5zZXJ0KG51bGwpfT57bGFzdEluc2VydH08L05vdGlmaWNhdGlvbj59XG5cbiAgICAgIDxHcm91cCBnYXA9ezZ9PlxuICAgICAgICA8VGV4dGFyZWFcbiAgICAgICAgICBwbGFjZWhvbGRlcj1cIuyekOyXsOyWtOuhnCDsp4jrrLjtlZjshLjsmpTigKZcIlxuICAgICAgICAgIHZhbHVlPXtpbnB1dH1cbiAgICAgICAgICBvbkNoYW5nZT17KGUpID0+IHNldElucHV0KGUuY3VycmVudFRhcmdldC52YWx1ZSl9XG4gICAgICAgICAgb25LZXlEb3duPXsoZSkgPT4ge1xuICAgICAgICAgICAgaWYgKGUua2V5ID09PSAnRW50ZXInICYmIChlLmN0cmxLZXkgfHwgZS5tZXRhS2V5KSkgc2VuZCgpO1xuICAgICAgICAgIH19XG4gICAgICAgICAgYXV0b3NpemVcbiAgICAgICAgICBtaW5Sb3dzPXsyfVxuICAgICAgICAgIG1heFJvd3M9ezZ9XG4gICAgICAgICAgc3R5bGU9e3sgZmxleDogMSB9fVxuICAgICAgICAvPlxuICAgICAgICA8QnV0dG9uIG9uQ2xpY2s9e3NlbmR9IGxvYWRpbmc9e2J1c3l9IGRpc2FibGVkPXshaW5wdXQudHJpbSgpfT5cbiAgICAgICAgICDilrYg67O064K06riwXG4gICAgICAgIDwvQnV0dG9uPlxuICAgICAgPC9Hcm91cD5cbiAgICAgIDxUZXh0IHNpemU9XCJ4c1wiIGM9XCJkaW1tZWRcIj7ijJgvQ3RybCArIEVudGVyIOuhnCDsoITshqEg4oCUIOydkeuLteydgCDsiqTtirjrpqzrsI3rkKnri4jri6QuPC9UZXh0PlxuICAgIDwvU3RhY2s+XG4gICk7XG59XG5cbmZ1bmN0aW9uIEp1cHl0ZXJXaXRoQ29waWxvdCgpIHtcbiAgLy8gUGljayBhIGRlZmF1bHQgY29ubmVjdGlvbiDigJQgdGhlIGFuYWx5c3QgbGlrZWx5IHdhbnRzIHNhbGVzX2RiIGNvbnRleHQuXG4gIGNvbnN0IGNvbm5zID0gdXNlUXVlcnkoeyBxdWVyeUtleTogWydjb25ucyddLCBxdWVyeUZuOiBhcGkuY29ubmVjdGlvbnMgfSk7XG4gIGNvbnN0IGRlZmF1bHRDb25uID0gY29ubnMuZGF0YT8uZmluZCgoYykgPT4gYy5lbmdpbmUgIT09ICdoaXZlJyk/LmNvbm5lY3Rpb25faWQgPz8gbnVsbDtcbiAgY29uc3QgW2Nvbm5JZCwgc2V0Q29ubklkXSA9IHVzZVN0YXRlPHN0cmluZyB8IG51bGw+KG51bGwpO1xuICBjb25zdCBhY3RpdmVDb25uID0gY29ubklkID8/IGRlZmF1bHRDb25uO1xuICBjb25zdCBbbGFiUmVsb2FkVG9rZW4sIHNldExhYlJlbG9hZFRva2VuXSA9IHVzZVN0YXRlKDApO1xuXG4gIHJldHVybiAoXG4gICAgPGRpdiBzdHlsZT17eyBkaXNwbGF5OiAnZmxleCcsIGhlaWdodDogJzEwMCUnLCB3aWR0aDogJzEwMCUnIH19PlxuICAgICAgPGRpdiBzdHlsZT17eyBmbGV4OiAnMSAxIDY1JScsIG1pbldpZHRoOiAzMjAsIGhlaWdodDogJzEwMCUnIH19PlxuICAgICAgICA8SnVweXRlckxhYiByZWxvYWRUb2tlbj17bGFiUmVsb2FkVG9rZW59IC8+XG4gICAgICA8L2Rpdj5cbiAgICAgIDxkaXYgc3R5bGU9e3sgZmxleDogJzAgMCAzNSUnLCBtaW5XaWR0aDogMzIwLCBtYXhXaWR0aDogNjAwLCBoZWlnaHQ6ICcxMDAlJywgYm9yZGVyTGVmdDogJzFweCBzb2xpZCAjZTllY2VmJywgYmFja2dyb3VuZDogJyNmYWZhZmEnIH19PlxuICAgICAgICA8U3RhY2sgcD17MH0gZ2FwPXswfSBzdHlsZT17eyBoZWlnaHQ6ICcxMDAlJyB9fT5cbiAgICAgICAgICA8R3JvdXAgcD1cInhzXCIgZ2FwPVwieHNcIiBhbGlnbj1cImNlbnRlclwiIHN0eWxlPXt7IGJvcmRlckJvdHRvbTogJzFweCBzb2xpZCAjZTllY2VmJyB9fT5cbiAgICAgICAgICAgIDxUZXh0IHNpemU9XCJ4c1wiIGM9XCJkaW1tZWRcIj7su6TrhKXshZgg7Luo7YWN7Iqk7Yq4PC9UZXh0PlxuICAgICAgICAgICAgPFNlbGVjdFxuICAgICAgICAgICAgICBzaXplPVwieHNcIlxuICAgICAgICAgICAgICB2YWx1ZT17YWN0aXZlQ29ubn1cbiAgICAgICAgICAgICAgZGF0YT17KGNvbm5zLmRhdGEgPz8gW10pLm1hcCgoYykgPT4gKHsgdmFsdWU6IGMuY29ubmVjdGlvbl9pZCwgbGFiZWw6IGMubmFtZSB9KSl9XG4gICAgICAgICAgICAgIG9uQ2hhbmdlPXtzZXRDb25uSWR9XG4gICAgICAgICAgICAgIHBsYWNlaG9sZGVyPVwi7ISg7YOdXCJcbiAgICAgICAgICAgICAgc3R5bGU9e3sgZmxleDogMSB9fVxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L0dyb3VwPlxuICAgICAgICAgIDxkaXYgc3R5bGU9e3sgZmxleDogMSwgbWluSGVpZ2h0OiAwIH19PlxuICAgICAgICAgICAgPENvcGlsb3RQYW5lbFxuICAgICAgICAgICAgICBjb25uZWN0aW9uSWQ9e2FjdGl2ZUNvbm59XG4gICAgICAgICAgICAgIG9uQ2VsbEluc2VydGVkPXsoKSA9PiBzZXRMYWJSZWxvYWRUb2tlbigobikgPT4gbiArIDEpfVxuICAgICAgICAgICAgLz5cbiAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgPC9TdGFjaz5cbiAgICAgIDwvZGl2PlxuICAgIDwvZGl2PlxuICApO1xufVxuXG5mdW5jdGlvbiBTaGVsbCgpIHtcbiAgY29uc3QgbWUgPSB1c2VRdWVyeSh7IHF1ZXJ5S2V5OiBbJ21lJ10sIHF1ZXJ5Rm46IGFwaS5tZSB9KTtcbiAgY29uc3QgbG9jID0gdXNlTG9jYXRpb24oKTtcbiAgLy8gSnVweXRlckxhYiBuZWVkcyB0aGUgZnVsbCB2aWV3cG9ydCBzbyBpdHMgb3duIGxlZnQgcGFuZWwgaGFzIHJvb20uIE90aGVyXG4gIC8vIHJvdXRlcyBrZWVwIHRoZSBTUEEncyBuYXZiYXIgdmlzaWJsZSBieSBkZWZhdWx0LlxuICBjb25zdCBpc0p1cHl0ZXIgPSBsb2MucGF0aG5hbWUgPT09ICcvJyB8fCBsb2MucGF0aG5hbWUgPT09ICcnO1xuICBjb25zdCBbbmF2T3Blbiwgc2V0TmF2T3Blbl0gPSB1c2VTdGF0ZShmYWxzZSk7XG4gIGNvbnN0IG5hdkNvbGxhcHNlZCA9IGlzSnVweXRlciAmJiAhbmF2T3BlbjtcblxuICByZXR1cm4gKFxuICAgIDxBcHBTaGVsbFxuICAgICAgaGVhZGVyPXt7IGhlaWdodDogNDQgfX1cbiAgICAgIG5hdmJhcj17e1xuICAgICAgICB3aWR0aDogMjIwLFxuICAgICAgICBicmVha3BvaW50OiAnc20nLFxuICAgICAgICBjb2xsYXBzZWQ6IHsgZGVza3RvcDogbmF2Q29sbGFwc2VkLCBtb2JpbGU6IG5hdkNvbGxhcHNlZCB9LFxuICAgICAgfX1cbiAgICAgIHBhZGRpbmc9ezB9XG4gICAgPlxuICAgICAgPEFwcFNoZWxsLkhlYWRlcj5cbiAgICAgICAgPEdyb3VwIGg9XCIxMDAlXCIgcHg9XCJzbVwiIGp1c3RpZnk9XCJzcGFjZS1iZXR3ZWVuXCI+XG4gICAgICAgICAgPEdyb3VwIGdhcD1cInhzXCI+XG4gICAgICAgICAgICA8QnVyZ2VyXG4gICAgICAgICAgICAgIG9wZW5lZD17IW5hdkNvbGxhcHNlZH1cbiAgICAgICAgICAgICAgb25DbGljaz17KCkgPT4gc2V0TmF2T3BlbigobykgPT4gIW8pfVxuICAgICAgICAgICAgICBzaXplPVwic21cIlxuICAgICAgICAgICAgICBhcmlhLWxhYmVsPVwi7IKs7J2065Oc67CUIO2GoOq4gFwiXG4gICAgICAgICAgICAvPlxuICAgICAgICAgICAgPFRpdGxlIG9yZGVyPXs1fT7wn6eqIEFuYWx5c3QgV29ya3NwYWNlPC9UaXRsZT5cbiAgICAgICAgICA8L0dyb3VwPlxuICAgICAgICAgIHttZS5kYXRhICYmIChcbiAgICAgICAgICAgIDxHcm91cCBnYXA9XCJ4c1wiPlxuICAgICAgICAgICAgICA8VGV4dCBzaXplPVwic21cIiBjPVwiZGltbWVkXCI+e21lLmRhdGEuZGlzcGxheV9uYW1lID8/IG1lLmRhdGEuZW1haWx9PC9UZXh0PlxuICAgICAgICAgICAgICB7bWUuZGF0YS5yb2xlcy5tYXAoKHIpID0+IChcbiAgICAgICAgICAgICAgICA8QmFkZ2Uga2V5PXtyfSB2YXJpYW50PVwibGlnaHRcIj57cn08L0JhZGdlPlxuICAgICAgICAgICAgICApKX1cbiAgICAgICAgICAgIDwvR3JvdXA+XG4gICAgICAgICAgKX1cbiAgICAgICAgPC9Hcm91cD5cbiAgICAgIDwvQXBwU2hlbGwuSGVhZGVyPlxuICAgICAgPEFwcFNoZWxsLk5hdmJhciBwPVwic21cIj5cbiAgICAgICAgPE5hdkxpbmtcbiAgICAgICAgICBjb21wb25lbnQ9e0xpbmt9XG4gICAgICAgICAgdG89XCIvXCJcbiAgICAgICAgICBsYWJlbD1cIvCfk5MgIEp1cHl0ZXJMYWJcIlxuICAgICAgICAgIG9uQ2xpY2s9eygpID0+IHNldE5hdk9wZW4oZmFsc2UpfVxuICAgICAgICAvPlxuICAgICAgICA8TmF2TGlua1xuICAgICAgICAgIGNvbXBvbmVudD17TGlua31cbiAgICAgICAgICB0bz1cIi9zcWxcIlxuICAgICAgICAgIGxhYmVsPVwi8J+TnSAg67mg66W4IFNRTFwiXG4gICAgICAgICAgb25DbGljaz17KCkgPT4gc2V0TmF2T3Blbih0cnVlKX1cbiAgICAgICAgLz5cbiAgICAgICAgPE5hdkxpbmtcbiAgICAgICAgICBjb21wb25lbnQ9e0xpbmt9XG4gICAgICAgICAgdG89XCIvbm90ZWJvb2tzXCJcbiAgICAgICAgICBsYWJlbD1cIvCfk5ogIOuCtCDrhbjtirjrtoFcIlxuICAgICAgICAgIG9uQ2xpY2s9eygpID0+IHNldE5hdk9wZW4odHJ1ZSl9XG4gICAgICAgIC8+XG4gICAgICA8L0FwcFNoZWxsLk5hdmJhcj5cbiAgICAgIDxBcHBTaGVsbC5NYWluXG4gICAgICAgIHN0eWxlPXt7XG4gICAgICAgICAgLy8gNDRweCBjbGVhcnMgdGhlIGZpeGVkIGhlYWRlcjsgdGhlIEp1cHl0ZXJMYWIgZW1iZWQgd2FudHMgdGhlIGZ1bGxcbiAgICAgICAgICAvLyB2aWV3cG9ydCAoaXQgaGFzIGl0cyBvd24gbGVmdCByYWlsKSBzbyB3ZSBzdHJpcCB0aGUgU1BBJ3MgbmF2YmFyXG4gICAgICAgICAgLy8gZ3V0dGVyIHRoZXJlLiBFdmVyeSBvdGhlciByb3V0ZSBuZWVkcyB0byBwdXNoIHBhc3QgdGhlIDIyMC1weFxuICAgICAgICAgIC8vIG5hdmJhciBzbyB0aGUgYWN0aW9uIGJ1dHRvbnMgYXJlbid0IGhpZGRlbiBiZWhpbmQgaXQuXG4gICAgICAgICAgcGFkZGluZzogaXNKdXB5dGVyID8gJzQ0cHggMCAwIDAnIDogJzQ0cHggMCAwIDIyMHB4JyxcbiAgICAgICAgICBoZWlnaHQ6ICcxMDB2aCcsXG4gICAgICAgICAgYm94U2l6aW5nOiAnYm9yZGVyLWJveCcsXG4gICAgICAgICAgb3ZlcmZsb3c6IGlzSnVweXRlciA/ICdoaWRkZW4nIDogJ2F1dG8nLFxuICAgICAgICB9fVxuICAgICAgPlxuICAgICAgICA8Um91dGVzPlxuICAgICAgICAgIDxSb3V0ZSBwYXRoPVwiL1wiIGVsZW1lbnQ9ezxKdXB5dGVyV2l0aENvcGlsb3QgLz59IC8+XG4gICAgICAgICAgPFJvdXRlIHBhdGg9XCIvc3FsXCIgZWxlbWVudD17PFF1ZXJ5RWRpdG9yIC8+fSAvPlxuICAgICAgICAgIDxSb3V0ZSBwYXRoPVwiL25vdGVib29rc1wiIGVsZW1lbnQ9ezxOb3RlYm9va0xpc3QgLz59IC8+XG4gICAgICAgICAgPFJvdXRlIHBhdGg9XCIvbm90ZWJvb2tzLzppZFwiIGVsZW1lbnQ9ezxOb3RlYm9va0RldGFpbCAvPn0gLz5cbiAgICAgICAgPC9Sb3V0ZXM+XG4gICAgICA8L0FwcFNoZWxsLk1haW4+XG4gICAgPC9BcHBTaGVsbD5cbiAgKTtcbn1cblxuUmVhY3RET00uY3JlYXRlUm9vdChkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgncm9vdCcpISkucmVuZGVyKFxuICA8TWFudGluZVByb3ZpZGVyPlxuICAgIDxRdWVyeUNsaWVudFByb3ZpZGVyIGNsaWVudD17cXVlcnlDbGllbnR9PlxuICAgICAgPEJyb3dzZXJSb3V0ZXIgYmFzZW5hbWU9XCIvYW5hbHlzdFwiPlxuICAgICAgICA8U2hlbGwgLz5cbiAgICAgIDwvQnJvd3NlclJvdXRlcj5cbiAgICA8L1F1ZXJ5Q2xpZW50UHJvdmlkZXI+XG4gIDwvTWFudGluZVByb3ZpZGVyPlxuKTtcbiJdLCJmaWxlIjoiL2FwcC9zcmMvbWFpbi50c3gifQ==