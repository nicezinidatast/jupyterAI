/**
 * JupyterLab extension registry.
 *
 * Phase 1 ships only the registration scaffold. Concrete plugins
 * (connection-panel, sql-editor, chart-button) attach in subsequent
 * iterations once the backend endpoints are stable.
 */
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';

const connectionPanelPlugin: JupyterFrontEndPlugin<void> = {
  id: '@dataplatform/jupyter-extensions:connection-panel',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('dataplatform: connection-panel registered', app);
  },
};

const sqlEditorPlugin: JupyterFrontEndPlugin<void> = {
  id: '@dataplatform/jupyter-extensions:sql-editor',
  autoStart: true,
  activate: () => {
    console.log('dataplatform: sql-editor registered');
  },
};

const chartButtonPlugin: JupyterFrontEndPlugin<void> = {
  id: '@dataplatform/jupyter-extensions:chart-button',
  autoStart: true,
  activate: () => {
    console.log('dataplatform: chart-button registered');
  },
};

export default [connectionPanelPlugin, sqlEditorPlugin, chartButtonPlugin];
