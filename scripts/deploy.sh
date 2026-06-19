#!/usr/bin/env bash
# 폐쇄망(망분리) prod 서버에서 "직접" 실행하는 배포 스크립트.
#
# 왜 이게 필요한가:
#   GitHub 클라우드 러너는 사설 IP·망분리 서버에 닿을 수 없고, 망분리 서버는
#   github.com / hooks.slack.com 으로 아웃바운드가 막혀 있어서 GitHub 가
#   트리거하는 자동 배포·공개 Slack 알림이 불가능하다. 그래서 배포 자체는
#   서버 안에서 이 스크립트로 수행하고, "배포 시작/종료"를 콘솔에 찍는다
#   (내부망에서 닿는 알림 웹훅이 있으면 거기로도 보낸다).
#
# 사용:
#   bash scripts/deploy.sh
#   # Windows + WSL 서버면 WSL 안에서:  wsl bash scripts/deploy.sh
#   # 크론으로 준자동화도 가능(내부 git 미러가 있을 때): 예) 5분마다 변경 감지 후 실행
#
# 선택 환경변수:
#   DEPLOY_NOTIFY_WEBHOOK : 내부망에서 닿는 Slack/Mattermost 호환 Incoming Webhook.
#                           설정하면 배포 시작/종료를 거기로도 POST(없으면 콘솔만).
#   COMPOSE_FILE          : compose 파일 경로(기본 infra/docker-compose/compose.prod.yml).
#   DOCKER                : docker 실행 명령(기본 "docker"). 필요 시 "sudo docker" 등으로 덮어쓰기.
set -euo pipefail

# 스크립트 위치 기준으로 리포 루트로 이동 — 어디서 호출하든 경로가 안 꼬이게.
cd "$(dirname "$0")/.."

COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose/compose.prod.yml}"
DOCKER="${DOCKER:-docker}"
# 알림에 붙일 프로젝트 라벨 — CI(러너)면 GITHUB_REPOSITORY, 수동이면 현재 폴더명.
PROJECT="${GITHUB_REPOSITORY:-$(basename "$(pwd)")}"

# 콘솔 + (설정됐으면) 내부 알림 웹훅으로 한 줄 메시지를 보낸다.
# 메시지에 따옴표를 넣지 않으므로 JSON 조립은 단순 치환으로 충분하다.
notify() {
  echo "[deploy $(date '+%F %T')] $1"
  if [ -n "${DEPLOY_NOTIFY_WEBHOOK:-}" ]; then
    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$1\"}" "${DEPLOY_NOTIFY_WEBHOOK}" >/dev/null \
      || echo "  (내부 알림 전송 실패 — 무시하고 배포는 계속)"
  fi
}

# 어느 단계에서 실패하든(=set -e 로 중단) "배포 실패"를 먼저 알리고 종료한다.
on_err() { notify "❌ 배포 실패 — ${PROJECT} (로그 확인 필요)"; }
trap on_err ERR

REV="$(git rev-parse --short HEAD 2>/dev/null || echo '?')"
notify "🚀 배포 시작 — ${PROJECT} (${REV})"

# 내부 git 미러(또는 외부 origin)에 닿으면 최신 main 으로 동기화한다.
# 완전 망분리라 origin 에 못 닿으면(=오프라인으로 코드를 반입한 경우) 이 단계는
# 건너뛰고, 서버에 이미 반입돼 있는 현재 코드로 빌드한다(배포를 막지 않는다).
if git remote get-url origin >/dev/null 2>&1; then
  if git fetch --prune origin main 2>/dev/null; then
    git reset --hard origin/main
    REV="$(git rev-parse --short HEAD)"
    echo "  origin/main 동기화 완료 → ${REV}"
  else
    echo "  origin 에 닿지 못함 — 반입된 현재 코드로 진행(망분리 정상 동작)"
  fi
fi

# prod 스택 재빌드·기동. 코드/이미지가 서버에 있으면 외부망 없이도 빌드된다
# (PyPI·apt·DockerHub 의존을 이미 제거/오프라인 반입 처리한 구성).
# DB 스키마는 앱 시작 시 멱등 보강 → 수동 DB 작업 불필요.
$DOCKER compose -f "${COMPOSE_FILE}" up -d --build --remove-orphans

# 떠 있는 컨테이너 상태를 한눈에 남긴다(배포 후 점검용).
$DOCKER compose -f "${COMPOSE_FILE}" ps

# 빌드로 생긴 dangling 이미지 정리(디스크 회수). 실패해도 배포 성공엔 영향 없음.
$DOCKER image prune -f || true

notify "✅ 배포 완료 — ${PROJECT} (${REV})"
