"""GitLab/Gitea adapter — HTTP-only, no shell out to ``git``."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret


class GitAdapter(Protocol):
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
        """Return the new commit SHA on success."""
        ...


class GiteaGitAdapter:
    """Minimal Gitea client. GitLab is API-compatible enough to share the path
    /api/v1/repos/{owner}/{repo}/contents/{path}."""

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

        # The Gitea / GitLab Contents API distinguishes between creating a
        # new file (POST) and updating an existing one (PUT with the current
        # blob ``sha``). We probe for the existing blob first so a second
        # save of the same notebook does not 409.
        url = f"{repo_url}/contents/{path}"
        existing_sha = await self._lookup_existing_sha(url, branch, token)
        encoded = base64.b64encode(json.dumps(content).encode()).decode()
        body: dict[str, Any] = {
            "branch": branch,
            "content": encoded,
            "message": message,
            "author": {"name": author, "email": f"{author}@dataplatform.internal"},
        }
        if existing_sha is not None:
            body["sha"] = existing_sha
        try:
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
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        if r.status_code in (200, 201):
            sha = r.json().get("commit", {}).get("sha")
            if not sha:
                return Err(DomainError.EXTERNAL_UNAVAILABLE)
            return Ok(sha)
        if r.status_code in (401, 403):
            return Err(DomainError.UNAUTHORIZED)
        return Err(DomainError.EXTERNAL_UNAVAILABLE)

    async def _lookup_existing_sha(
        self, url: str, branch: str, token: Secret
    ) -> str | None:
        """Return the blob sha for ``path`` on ``branch``, or None if absent."""
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
            return None
