# tests/integration 패키지 마커.
# 이 디렉터리의 테스트는 testcontainers(postgres:16-alpine)를 이용해
# 실제 데이터베이스 드라이버 경로를 검증하는 통합 테스트 모음이다.
# Docker 데몬이 없는 환경에서는 conftest의 pytestmark_docker 에 의해 자동 skip된다.
