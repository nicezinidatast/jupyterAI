"""플랫폼 백엔드에 인증을 위임하는 JupyterHub 커스텀 Authenticator.

동작 방식:
- 게이트웨이(Nginx)에서 SSO를 처리한 백엔드가 단기 유효 ``platform_token``을 발급한다.
- JupyterHub 로그인 폼이 이 토큰을 POST하면 이 Authenticator가 받아서
  백엔드 /api/auth/me 엔드포인트로 재검증한다.
- 검증 성공 시 user_id를 JupyterHub 사용자 이름으로 반환한다.

표준 PAMAuthenticator(OS 계정 기반)를 사용하지 않는 이유:
컨테이너 환경에서 OS 사용자를 미리 생성할 수 없고, 인증 권한을 백엔드에
일원화해 세션 취소·역할 변경을 즉시 반영하기 위해서다.
"""

from __future__ import annotations

import os

import httpx
from jupyterhub.auth import Authenticator


class PlatformAuthenticator(Authenticator):
    async def authenticate(self, handler, data):  # noqa: ARG002
        """플랫폼 토큰을 백엔드에 검증하고 JupyterHub 사용자 딕셔너리를 반환한다.

        반환값:
            dict: {"name": user_id, "auth_state": {"token": token}} — 인증 성공
            None: 토큰 없음 또는 백엔드 검증 실패 → JupyterHub가 로그인 거부로 처리

        handler 인자를 사용하지 않는 이유:
        HTTP 요청 정보(IP, User-Agent 등)는 이 흐름에서 필요하지 않으며,
        토큰 유효성만 백엔드가 판단하도록 설계했다.
        """
        token = data.get("platform_token")
        if not token:
            # 로그인 폼에 platform_token 필드가 없으면 즉시 거부한다.
            # 일반 JupyterHub 기본 폼(username/password)으로 진입한 경우에도 해당된다.
            return None

        # 백엔드 URL을 환경변수로 주입받아 하드코딩을 피한다.
        # docker-compose 네트워크에서 서비스명 "backend"로 통신하는 것이 기본값이다.
        backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")

        # timeout=5.0: 백엔드가 느리거나 다운되었을 때 JupyterHub 인증 요청 스레드가
        # 무한정 블로킹되지 않도록 5초 안전망을 설정한다.
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{backend_url}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

        if r.status_code != 200:
            # 토큰이 만료되었거나 백엔드가 거부한 경우 None을 반환해 로그인을 막는다.
            # 에러 상세를 JupyterHub 레이어에서 로깅하지 않는 이유:
            # 원인 분석은 백엔드 로그에서 해야 하며, 여기서 중복 로깅하면 혼선이 생긴다.
            return None

        # auth_state에 토큰을 포함해 반환하면, JupyterHub가 이를 암호화해 DB에 저장한다.
        # 이후 spawner가 사용자 컨테이너 기동 시 이 토큰을 환경변수로 주입할 수 있다.
        return {"name": r.json().get("user_id"), "auth_state": {"token": token}}
