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

# 사용자 한 명당 메모리 상한 4 GB, CPU 상한 2코어.
# 한 사용자의 과부하 쿼리가 다른 사용자 세션에 영향을 주지 않도록 격리한다.
c.DockerSpawner.mem_limit = "4G"
c.DockerSpawner.cpu_limit = 2.0

# 사용자 컨테이너가 JupyterHub(허브 컨테이너) 및 백엔드와 통신할 수 있도록
# 같은 Docker 네트워크에 연결한다. 네트워크명을 환경변수로 받아 유연성을 확보한다.
c.DockerSpawner.network_name = os.environ.get("DOCKER_NETWORK", "dataplatform_default")

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
