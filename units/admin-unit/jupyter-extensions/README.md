# Dataplatform JupyterLab Extensions

Three plugins that attach to JupyterLab inside user notebooks:

- `connection-panel` — sidebar listing registered RDBMS/Big-Data connections.
- `sql-editor` — auto-complete + syntax highlighting for `%%sql` cells, backed by `/api/schemas`.
- `chart-button` — adds a "차트 변환" toolbar action that turns a result cell into a Plotly chart.

```bash
pnpm install
pnpm build
# To install into a running JupyterLab:
jupyter labextension install .
```

Phase 1 currently ships only the plugin registration shells; the UI work
lands in subsequent ralph cycles.
