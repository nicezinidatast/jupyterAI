"""사용자별 JupyterHub 볼륨 가비지 컬렉터 — "하루 지나면 삭제" 정리 루프.

왜 이게 필요한가:
  자원이 빠듯한 온프레미스(8GB·소용량 디스크)에서는 사용자 데이터를 영구
  보존할 수 없다. 분석가가 업로드하는 데이터 파일은 ~/work/uploads/ 에 쌓여
  볼륨당 최대 1GiB까지 커질 수 있으므로, 오래된 사용자 볼륨을 주기적으로
  회수해 디스크를 비워야 한다.

왜 idle-culler 로는 부족한가:
  idle-culler 는 **노트북 서버(컨테이너)** 만 내린다(RAM 회수). 컨테이너가
  삭제(DockerSpawner.remove=True)돼도 사용자 데이터가 담긴 **명명 볼륨**
  (jupyterhub-user-<id>)은 그대로 남아 디스크를 계속 점유한다. 그 볼륨을
  지우는 주체가 없어서, 이 루프가 그 역할을 맡는다.

정책(보수적·안전 우선):
  - 이름이 ``jupyterhub-user-`` 로 시작하는 볼륨만 대상으로 한다
    (redis-data·uploads-data 같은 인프라 볼륨은 절대 건드리지 않는다).
  - **컨테이너에 붙어 있는(사용 중) 볼륨은 건너뛴다** — 지금 쓰고 있는
    사람의 파일을 작업 도중에 날리지 않기 위해서다. 30분 idle-culler 가
    서버를 내려 볼륨이 분리된 뒤에야 회수 후보가 된다.
  - 볼륨 생성 시각(CreatedAt)이 보존 기간(기본 1일)보다 오래된 것만 삭제한다.

결과적으로: 활동 중인 사용자는 데이터가 유지되고, 서버가 culling 된(=한동안
안 쓴) 1일 이상 묵은 볼륨만 정리된다. 다음 로그인 때는 빈 폴더로 새로 시작한다.

모든 값은 환경변수로 조정 가능(끄려면 RETENTION_SECONDS 를 매우 크게).
이 스크립트는 jupyterhub 이미지로 그대로 돌린다(docker SDK 가 dockerspawner
의존성으로 이미 깔려 있어 추가 설치·외부망이 필요 없다 — 닫힌 망 안전).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import docker  # dockerspawner 의존성으로 허브 이미지에 이미 존재

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [volume-gc] %(levelname)s %(message)s",
)
log = logging.getLogger("volume-gc")

# 정리 대상 볼륨 이름 접두사 — DockerSpawner 의 volumes 키
# {"jupyterhub-user-{username}": ...} 와 반드시 일치해야 한다.
VOLUME_PREFIX = os.environ.get("GC_VOLUME_PREFIX", "jupyterhub-user-")
# 보존 기간(초). 기본 1일. 이보다 오래된(그리고 분리된) 볼륨을 삭제한다.
RETENTION_SECONDS = int(os.environ.get("GC_RETENTION_SECONDS", str(24 * 60 * 60)))
# 정리 루프 주기(초). 기본 1시간 — 너무 자주 돌 필요는 없다(데몬 부하 최소화).
INTERVAL_SECONDS = int(os.environ.get("GC_INTERVAL_SECONDS", str(60 * 60)))


def _attached_volume_names(client: docker.DockerClient) -> set[str]:
    """현재 컨테이너(실행 중·정지 모두)에 마운트된 볼륨 이름 집합.

    all=True 로 정지 컨테이너까지 포함하는 이유: 스폰 직후/정지 직전의 짧은
    순간에 붙어 있는 볼륨을 '분리됨'으로 오판해 삭제하지 않도록 보수적으로 본다.
    """
    attached: set[str] = set()
    for container in client.containers.list(all=True):
        for mount in container.attrs.get("Mounts", []):
            name = mount.get("Name")
            if name:
                attached.add(name)
    return attached


def _age_seconds(created_at: str) -> float | None:
    """볼륨 CreatedAt(ISO8601 문자열)을 현재로부터의 경과 초로 변환.

    파싱 실패 시 None — 알 수 없는 형식의 볼륨은 안전하게 건너뛴다(삭제 안 함).
    docker 의 CreatedAt 은 보통 ``2026-06-18T10:00:00+09:00`` 또는 ``...Z`` 형태다.
    """
    try:
        # 파이썬 3.11+ fromisoformat 은 'Z' 접미사도 처리하지만, 구버전 호환을
        # 위해 'Z' 를 +00:00 으로 바꿔 준다.
        normalized = created_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except (ValueError, TypeError):
        return None


def collect_once(client: docker.DockerClient) -> None:
    """한 번의 정리 패스: 분리되고 오래된 사용자 볼륨을 삭제한다."""
    attached = _attached_volume_names(client)
    removed = 0
    for volume in client.volumes.list():
        name = volume.name
        if not name.startswith(VOLUME_PREFIX):
            continue  # 인프라 볼륨 — 절대 건드리지 않음
        if name in attached:
            continue  # 사용 중 — 작업 도중 데이터 보호를 위해 건너뜀
        age = _age_seconds(volume.attrs.get("CreatedAt", ""))
        if age is None or age < RETENTION_SECONDS:
            continue  # 형식 불명 또는 아직 보존 기간 이내
        try:
            volume.remove()
            removed += 1
            log.info("removed volume %s (age %.0fs ≥ %ds)", name, age, RETENTION_SECONDS)
        except docker.errors.APIError as exc:
            # 경합(방금 다시 붙음·이미 삭제됨 등)은 다음 패스에서 재시도되므로 무시.
            log.warning("could not remove volume %s: %s", name, exc)
    if removed:
        log.info("pass complete — %d volume(s) reclaimed", removed)


def main() -> None:
    log.info(
        "volume-gc 시작 — prefix=%r retention=%ds interval=%ds",
        VOLUME_PREFIX,
        RETENTION_SECONDS,
        INTERVAL_SECONDS,
    )
    client = docker.from_env()
    while True:
        try:
            collect_once(client)
        except Exception as exc:  # noqa: BLE001 — 루프는 어떤 오류에도 죽지 않아야 한다
            log.error("정리 패스 실패(다음 주기에 재시도): %s", exc)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
