/**
 * JupyterLab 확장 레지스트리 — 데이터 플랫폼 통합 진입점.
 *
 * JupyterFrontEndPlugin 은 JupyterLab 의 의존성 주입(DI) 단위다.
 * 각 plugin 을 배열로 export default 하면 JupyterLab 이 부트스트랩 시
 * autoStart: true 인 plugin 의 activate 함수를 순서대로 호출한다.
 *
 * Phase 1 현황: 세 plugin 모두 등록 스캐폴드(scaffold)만 갖춘 상태다.
 * 구체적인 UI·로직(패널 렌더링, SQL 에디터, 차트 버튼)은 백엔드 엔드포인트가
 * 확정된 이후 각 plugin 의 activate 함수 안에서 구현한다.
 *
 * 왜 plugin 을 분리하는가:
 *  - 각 plugin 이 독립적으로 토큰(JupyterFrontEnd.IShell 등)을 요청할 수 있다.
 *  - 특정 plugin 만 disable 하거나 교체할 때 다른 plugin 에 영향을 주지 않는다.
 *  - 테스트 시 activate 단위로 격리해 검증할 수 있다.
 *
 * Phase 1 ships only the registration scaffold. Concrete plugins
 * (connection-panel, sql-editor, chart-button) attach in subsequent
 * iterations once the backend endpoints are stable.
 */
import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';

/**
 * 데이터 소스 연결 패널 plugin.
 *
 * 역할(예정): 좌측 사이드바에 데이터베이스 연결 목록 패널을 추가한다.
 * activate 인자로 app(JupyterFrontEnd) 을 받는 이유: 패널을 shell 에 추가하려면
 * app.shell.add() 를 호출해야 하기 때문이다. Phase 1 에서는 등록만 로그로 확인한다.
 */
const connectionPanelPlugin: JupyterFrontEndPlugin<void> = {
  id: '@dataplatform/jupyter-extensions:connection-panel',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('dataplatform: connection-panel registered', app);
  },
};

/**
 * SQL 에디터 plugin.
 *
 * 역할(예정): 노트북 셀 옆에 SQL 에디터 위젯을 추가하거나,
 * 별도 탭으로 열어 플랫폼 데이터 소스에 직접 쿼리한다.
 * Phase 1 에서는 등록 확인 로그만 출력한다.
 */
const sqlEditorPlugin: JupyterFrontEndPlugin<void> = {
  id: '@dataplatform/jupyter-extensions:sql-editor',
  autoStart: true,
  activate: () => {
    console.log('dataplatform: sql-editor registered');
  },
};

/**
 * 차트 버튼 plugin.
 *
 * 역할(예정): 셀 출력 영역에 "차트로 보기" 버튼을 삽입해
 * DataFrame 결과를 시각화 컴포넌트로 바로 전환한다.
 * Phase 1 에서는 등록 확인 로그만 출력한다.
 */
const chartButtonPlugin: JupyterFrontEndPlugin<void> = {
  id: '@dataplatform/jupyter-extensions:chart-button',
  autoStart: true,
  activate: () => {
    console.log('dataplatform: chart-button registered');
  },
};

/**
 * 세 plugin 을 배열로 export default 한다.
 * JupyterLab 은 이 배열을 순회하며 각 plugin 을 DI 컨테이너에 등록한다.
 * autoStart: true 인 plugin 은 앱 시작 시 자동으로 activate 된다.
 */
export default [connectionPanelPlugin, sqlEditorPlugin, chartButtonPlugin];
