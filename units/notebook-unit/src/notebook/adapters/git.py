"""GitLab/Gitea 어댑터 — HTTP 전용, ``git`` 셸 호출 없음.

로컬에 git을 깔거나 작업 디렉터리를 clone하지 않고 GitLab/Gitea의 Contents API
(REST)만으로 커밋·푸시를 처리한다. 셸 아웃을 피한 이유: 컨테이너에 git 바이너리
의존을 두지 않고, 동시 커밋 시 로컬 작업본 충돌 같은 상태 관리 문제를 없애기
위함이다. 비용은 "한 파일 단위 커밋만 가능"하다는 제약인데, 노트북 자동 커밋엔
충분하다.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret


class GitAdapter(Protocol):
    """Git 호스팅 어댑터의 계약(인터페이스).

    구현체를 Protocol로 추상화해 오케스트레이터가 특정 Git 서버(Gitea/GitLab)에
    묶이지 않게 하고, 테스트에서 가짜 어댑터로 갈아끼울 수 있게 한다.
    """

    async def commit_and_push(
        self,
        *,
        repo_url: str,
        branch: str,
        path: str,
        content: dict[str, Any],
        message: str,
        author: str,
        token: Secret,
    ) -> Result[str, DomainError]:
        """성공 시 새 커밋 SHA를 돌려준다."""
        ...


class GiteaGitAdapter:
    """최소 Gitea 클라이언트. GitLab도 API 호환성이 충분해
    /api/v1/repos/{owner}/{repo}/contents/{path} 경로를 공유한다."""

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def commit_and_push(
        self,
        *,
        repo_url: str,
        branch: str,
        path: str,
        content: dict[str, Any],
        message: str,
        author: str,
        token: Secret,
    ) -> Result[str, DomainError]:
        import base64
        import json

        # Gitea / GitLab Contents API는 새 파일 생성(POST)과 기존 파일
        # 수정(PUT, 현재 blob ``sha`` 필요)을 구분한다. 같은 노트북을 두 번째로
        # 저장할 때 409(충돌)가 나지 않도록, 먼저 기존 blob을 조회해서 그 sha를
        # 본문에 실어 보낸다 — 즉 항상 PUT로 통일하는 멱등 전략.
        url = f"{repo_url}/contents/{path}"
        existing_sha = await self._lookup_existing_sha(url, branch, token)
        # Contents API는 파일 내용을 base64로 인코딩한 문자열로 받는다.
        encoded = base64.b64encode(json.dumps(content).encode()).decode()
        body: dict[str, Any] = {
            "branch": branch,
            "content": encoded,
            "message": message,
            "author": {"name": author, "email": f"{author}@dataplatform.internal"},
        }
        # 기존 파일이 있으면 그 sha를 실어야 PUT이 "수정"으로 받아들여진다.
        # 없으면(=새 파일) sha 없이 보내 생성으로 처리된다.
        if existing_sha is not None:
            body["sha"] = existing_sha
        try:
            # 토큰은 호출 직전에만 reveal()로 평문화한다(노출 최소화).
            r = await self._http.put(
                url,
                headers={
                    "Authorization": f"token {token.reveal()}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
        except httpx.HTTPError:
            # 네트워크/타임아웃 등 전송 실패는 일시적 외부 장애로 분류 → 재시도 대상.
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        if r.status_code in (200, 201):
            # 응답에서 새 커밋 SHA를 꺼낸다. 200/201인데 sha가 없으면
            # 응답 형식이 기대와 달라 신뢰할 수 없으므로 실패로 본다.
            sha = r.json().get("commit", {}).get("sha")
            if not sha:
                return Err(DomainError.EXTERNAL_UNAVAILABLE)
            return Ok(sha)
        # 인증/권한 실패는 재시도해도 같으므로 별도 오류로 구분한다.
        if r.status_code in (401, 403):
            return Err(DomainError.UNAUTHORIZED)
        return Err(DomainError.EXTERNAL_UNAVAILABLE)

    async def _lookup_existing_sha(
        self, url: str, branch: str, token: Secret
    ) -> str | None:
        """``branch``의 ``path`` 파일 blob sha를 반환, 없으면 None.

        조회 자체가 실패하거나(네트워크/비정상 응답) 파일이 없으면 None을 돌려
        호출부가 "새 파일 생성" 경로로 자연스럽게 흐르게 한다. 즉 sha 조회
        실패를 치명적 오류로 올리지 않는다.
        """
        try:
            r = await self._http.get(
                url,
                params={"ref": branch},
                headers={"Authorization": f"token {token.reveal()}"},
                timeout=10.0,
            )
        except httpx.HTTPError:
            return None
        if r.status_code != 200:
            return None
        try:
            return r.json().get("sha")
        except ValueError:
            # JSON 파싱 실패도 "sha 알 수 없음"으로 처리.
            return None
