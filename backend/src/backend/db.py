"""요청마다 AsyncSession을 제공하는 FastAPI 의존성 함수.

SQLAlchemy 비동기 세션의 생명 주기를 요청 단위로 관리한다.
세션 팩토리는 최초 요청 시 한 번만 생성되고 ``app.state``에 캐시된다.
이후 요청은 캐시된 팩토리를 재사용해 엔진을 매번 재생성하는 오버헤드를 없앤다.

사용 방법:
    ``Depends(get_session)``으로 라우터 함수에 주입한다.
    컨텍스트 매니저가 요청 완료 후 세션을 자동으로 닫는다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """``app.state``에서 세션 팩토리를 가져오거나 없으면 생성한다.

    ``expire_on_commit=False``로 설정한 이유:
    커밋 후 ORM 인스턴스의 속성을 재조회 없이 바로 읽어야 하는 경우가 많기 때문.
    커밋 즉시 만료되면 응답 직렬화 단계에서 추가 SELECT가 발생한다.
    """
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        factory = async_sessionmaker(request.app.state.engine, expire_on_commit=False)
        request.app.state.session_factory = factory
    return factory


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """요청 수명 동안 유효한 AsyncSession을 yield하는 FastAPI 의존성.

    컨텍스트 매니저(async with)가 정상 종료와 예외 모두에서 세션을 닫는다.
    세션은 ``yield`` 이후 응답 직렬화가 끝날 때까지 열린 상태를 유지한다.
    """
    factory = _session_factory(request)
    async with factory() as session:
        try:
            yield session
        finally:
            # 컨텍스트 매니저가 이미 닫지만, 명시적 close로 double-close 안전성을 보장.
            await session.close()
