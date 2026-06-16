# credential-unit — NFR Design

## 1. Vault Adapter

```python
class VaultAdapter:
    def __init__(self, addr: str, token_provider: Callable[[], str]):
        self._client = hvac.Client(url=addr)
        self._token_provider = token_provider

    def _refresh_token(self):
        self._client.token = self._token_provider()

    async def read(self, path: str) -> Result[Secret, DomainError]:
        try:
            r = self._client.secrets.kv.v2.read_secret_version(path=path)
            return Ok(Secret(r['data']['data']['value']))
        except hvac.exceptions.Forbidden:
            return Err(DomainError.FORBIDDEN)
        except hvac.exceptions.InvalidPath:
            return Err(DomainError.NOT_FOUND)
        except hvac.exceptions.VaultError as e:
            log.error("vault_error", path=path, exc=str(e))
            return Err(DomainError.EXTERNAL_UNAVAILABLE)

    async def write(self, path: str, value: Secret) -> Result[None, DomainError]:
        ...
    async def delete(self, path: str) -> Result[None, DomainError]:
        ...
```

- Vault 토큰: AppRole 인증 (Vault Agent or 직접 login)
- 토큰 만료 시 자동 갱신 (refresh thread)

## 2. Resolve 캐시

```python
class ResolveCache:
    def __init__(self, ttl_seconds=60):
        self._store: dict[UUID, tuple[Secret, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get_or_fetch(self, credential_id, fetcher):
        now = datetime.utcnow()
        async with self._lock:
            entry = self._store.get(credential_id)
            if entry and entry[1] > now:
                return entry[0]
        secret = await fetcher()
        async with self._lock:
            self._store[credential_id] = (secret, now + timedelta(seconds=60))
        return secret

    def invalidate(self, credential_id):
        self._store.pop(credential_id, None)
```

- rotate / delete 시 즉시 invalidate

## 3. Secret Lifecycle

```python
async def execute_query(connection_id, user_ctx):
    cred_id = lookup_connection(connection_id).credential_id
    secret_result = await vault_service.resolve(cred_id, user_ctx)
    if isinstance(secret_result, Err): return secret_result
    try:
        # 사용 직전에만 평문 노출
        plain = secret_result.value.reveal()
        conn = await connector.connect(host, user, plain)
        del plain   # GC 힌트
        ...
    finally:
        # Secret 객체는 함수 종료 시 GC
        pass
```

## 4. 권한 검증 흐름

`resolve` 호출 시 시퀀스:
1. CredentialVault → AuthService.verify_credential_access(user_ctx, credential_id)
2. AuthService가 connection_grants + credential.scope 결합 검증
3. 통과 시 Vault read

## 5. 메트릭

```
credential_resolve_total{result, cache_hit}
credential_resolve_latency_seconds
credential_vault_errors_total{op, error_type}
credential_active_count        (gauge)
```
