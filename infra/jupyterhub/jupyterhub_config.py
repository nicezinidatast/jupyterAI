"""JupyterHub 설정 — DockerSpawner + PlatformAuthenticator 조합.

이 파일은 JupyterHub 런타임이 자동으로 로드하는 표준 설정 모듈이다.
`get_config()`는 JupyterHub가 실행 컨텍스트에서 주입하는 내장 함수이므로
import 없이 사용할 수 있다.
"""

import os

# JupyterHub가 실행 시 주입하는 설정 객체다. 이 객체를 통해
# 모든 컴포넌트(인증자, 스포너, 서비스 등)를 구성한다.
c = get_config()  # noqa: F821 — provided by jupyterhub at runtime

# 모든 인터페이스(0.0.0.0)의 8000번 포트에서 수신한다.
# 컨테이너 내부 포트이며, 실제 외부 노출은 Nginx 리버스 프록시(포트 5500)가 담당한다.
c.JupyterHub.bind_url = "http://:8000"

# 포털 nginx가 /jupyter/ 하위로 허브를 프록시하므로, 허브의 모든 경로를 그 접두사
# 아래로 둔다. 단일 jupyter 서버를 대체하면서 SPA가 쓰던 /jupyter/ 접두사를 그대로
# 유지하기 위함이다(허브 페이지·사용자 서버 모두 /jupyter/... 로 노출).
c.JupyterHub.base_url = "/jupyter/"

# DockerSpawner 필수: 스폰된 사용자 컨테이너가 허브에 "다시 접속"할 주소를 알려준다.
# 허브 기본값 hub_ip=127.0.0.1 은 같은 호스트(LocalProcessSpawner)에서만 통한다.
# 컨테이너별 스폰에서는 사용자 컨테이너가 허브를 자기 자신의 127.0.0.1 로 찾으려다
# 실패해 등록이 안 되고, 스폰이 타임아웃→컨테이너 제거되어 결국 Lab 접속이 404가 된다.
# 허브는 0.0.0.0 으로 듣고, 사용자 컨테이너는 도커 네트워크의 허브 서비스명(jupyterhub)으로
# 접속하게 한다. (compose의 서비스명과 반드시 일치 — env로도 덮어쓸 수 있게 둔다.)
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = os.environ.get("HUB_CONNECT_IP", "jupyterhub")

# 플랫폼 백엔드 SSO 토큰을 검증하는 커스텀 인증자를 사용한다.
# 기본 PAMAuthenticator(OS 사용자) 대신 platform_authenticator 모듈을 지정해
# 백엔드 /api/auth/me 검증 흐름과 통합한다.
c.JupyterHub.authenticator_class = "platform_authenticator.PlatformAuthenticator"

# 각 사용자의 노트북 서버를 격리된 Docker 컨테이너로 기동한다.
# 사용자별 프로세스 격리와 리소스 제한이 목적이다.
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

# 사용자 노트북 컨테이너에 사용할 이미지를 환경변수로 주입받는다.
# 이미지를 하드코딩하지 않으면 docker-compose.yml에서 버전을 중앙 관리할 수 있다.
c.DockerSpawner.image = os.environ.get("USER_IMAGE", "dataplatform/notebook-user:0.1.0")

# 사용자가 노트북 서버를 종료하면 컨테이너를 즉시 삭제한다.
# 일시 정지(pause) 대신 삭제(remove)를 택한 이유: 정지 컨테이너가 쌓여
# 디스크를 소모하는 것을 방지하기 위해서다. 영구 데이터는 볼륨으로 보존된다.
c.DockerSpawner.remove = True

# 동시 접속(동시에 떠 있는 사용자 노트북 서버) 상한. 작은 온프레미스(~8GB) 서버에선
# RAM이 곧 한계이므로 "1인당 메모리 × 동시 인원 ≤ 전체 RAM − 시스템 여유분"을 지켜야 한다.
# 기본 3명으로 시작하고, 서버 사양에 맞춰 JUPYTERHUB_ACTIVE_SERVER_LIMIT로 조정한다(0=무제한).
# 상한에 도달하면 새 사용자는 누군가 서버를 내릴 때까지 대기한다(스폰 거부가 아니라 큐잉).
c.JupyterHub.active_server_limit = int(os.environ.get("JUPYTERHUB_ACTIVE_SERVER_LIMIT", "3"))

# 사용자 1인당 자원 상한. 8GB 박스에서 시스템/백엔드/포털/허브에 ~2.5GB를 남기면 사용자 몫은
# ~5GB → 동시 3명이면 1인당 1.5GB가 적정(3×1.5=4.5GB). 더 무거운 분석이 필요하면 동시
# 인원을 줄이고 메모리를 키운다. 한 사용자의 과부하가 다른 사용자에게 번지지 않게 격리한다.
# mem/cpu/동시인원 모두 환경변수로 조정 가능.
c.DockerSpawner.mem_limit = os.environ.get("JUPYTERHUB_USER_MEM_LIMIT", "1.5G")
c.DockerSpawner.cpu_limit = float(os.environ.get("JUPYTERHUB_USER_CPU_LIMIT", "2.0"))

# 사용자 컨테이너가 JupyterHub(허브 컨테이너) 및 백엔드와 통신할 수 있도록
# 같은 Docker 네트워크에 연결한다. 네트워크명을 환경변수로 받아 유연성을 확보한다.
c.DockerSpawner.network_name = os.environ.get("DOCKER_NETWORK", "dataplatform_default")

# 사용자별 영속 볼륨 — 각 사용자의 작업 폴더를 자기만의 도커 볼륨에 저장한다.
# {username}은 DockerSpawner가 사용자 이름(=user_id)으로 치환한다. 이 컨테이너+볼륨
# 분리가 "남의 폴더가 보이지도, 접근되지도 않는다"는 격리의 핵심이다(파일시스템 완전 분리).
c.DockerSpawner.volumes = {"jupyterhub-user-{username}": "/home/jovyan/work"}
c.DockerSpawner.notebook_dir = "/home/jovyan/work"

# 사용자 노트북 서버를 Lab으로 띄우고, 포털(다른 경로 오리진)에서 iframe 임베드가
# 되도록 프레임 허용(CSP frame-ancestors) + XSRF 비활성화로 쿠키 기반 contents API
# 호출을 단순화한다. 단일 서버 때(compose의 jupyter)와 동일한 정책을 사용자 서버에도 준다.
c.DockerSpawner.default_url = "/lab"
c.DockerSpawner.args = [
    "--ServerApp.allow_origin=*",
    "--ServerApp.disable_check_xsrf=True",
    '--ServerApp.tornado_settings={"headers":{"Content-Security-Policy":"frame-ancestors *"}}',
    "--LabApp.expose_app_in_browser=True",
]

# 유휴 노트북 서버를 30분 후 자동 종료하는 idle-culler 서비스를 등록한다.
# 사용하지 않는 컨테이너가 장시간 메모리와 CPU를 점유하는 것을 막기 위해
# JupyterHub 공식 보조 서비스 패턴을 활용한다.
# admin=True 권한이 필요한 이유: culler가 모든 사용자 서버를 직접 종료해야 하기 때문이다.
c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "admin": True,
        "command": [
            "python",
            "-m",
            "jupyterhub_idle_culler",
            "--timeout=1800",
        ],
    }
]
