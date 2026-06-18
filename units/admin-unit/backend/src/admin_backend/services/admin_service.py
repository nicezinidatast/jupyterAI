"""AdminConsole에 노출되는 서비스 파사드(facade).

이 모듈은 admin-unit이 제공하는 최상위 서비스 진입점이다.
실제 도메인 로직은 각 유닛(auth, data, credential 등)의 서비스 클래스에 있으며,
AdminService는 그 서비스들을 조합·위임하는 얇은 파사드 역할만 담당한다.

설계 의도:
- AdminService를 파사드로 둠으로써 라우터(router.py)가 여러 유닛 서비스를
  직접 import하지 않아도 되고, 단위 테스트 시 이 클래스 하나만 목(mock)하면 된다.
- 구체적인 의존성 연결(auth/RoleResolver, data/PiiPolicyStore 등)은
  백엔드 통합 패키지(backend integration package)에서 수행한다.
  이렇게 하면 admin_backend 패키지 내부에 순환 import가 생기지 않는다.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class AdminService:
    """어드민 콘솔용 파사드 — 세션을 보유하고 적절한 유닛 서비스로 요청을 전달한다.

    현재는 세션 보관자 역할만 하며, 추후 각 도메인 작업이 추가될 때
    메서드를 확장하는 방식으로 성장할 설계다.
    구체적인 의존성(RoleResolver, PiiPolicyStore 등) 주입은 이 클래스가 아니라
    상위 통합 패키지에서 담당한다(순환 import 방지).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # 구체적인 의존성 연결(auth/RoleResolver, data/PiiPolicyStore 등)은
        # 백엔드 통합 패키지에서 수행하므로 이 클래스는 순환 import 없이 유지된다.
