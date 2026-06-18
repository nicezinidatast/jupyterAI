# tests/e2e 패키지 마커.
# 이 디렉터리의 테스트는 실행 중인 docker compose 스택(portal nginx + FastAPI + JupyterLab)
# 을 전제로 하는 Playwright 기반 end-to-end 시나리오 모음이다.
# 개별 파일이 자체적으로 _portal_reachable() / _anthropic_configured() 를 체크하여
# 스택이 없는 환경에서는 자동으로 skip된다.
