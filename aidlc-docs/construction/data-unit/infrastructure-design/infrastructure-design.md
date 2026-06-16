# data-unit — Infrastructure Design

## 배포
- backend 컨테이너 B에 모듈 동거
- 백그라운드 잡 worker는 별도 worker 컨테이너(Phase 2) 또는 backend lifespan에 task로 동거 (MVP)

## DB 마이그레이션
- Alembic — connections, connection_grants, pii_patterns, column_policies, query_executions, file_uploads

## 환경 변수
- `DATABASE_URL`
- `REDIS_URL`
- `UPLOAD_STORAGE` = `nas:/mnt/uploads` 또는 `s3://uploads@minio.internal`
- `UPLOAD_MAX_BYTES=1073741824` (1GB)
- `RESULT_CACHE_DIR=/var/cache/query-results`
- `QUERY_TIMEOUT_SECONDS=5`
- `BG_JOB_MAX_PER_USER=10`

## 드라이버 인스톨 시 사내 미러
- Oracle: `oracledb` (thin mode — 사내 client lib 불필요)
- MSSQL: `pymssql` (libfreetds-dev 사내 미러 필요) 또는 `pyodbc` (Microsoft ODBC Driver)
- Kerberos: `gssapi` (krb5-dev 사내 미러)

## 외부 의존
- 사내 RDBMS 4종 + 빅데이터 SQL 4종 (TLS/Kerberos)
- NAS (NFS 마운트) 또는 MinIO
- Redis (jobs, result cache)

## 파일 스토리지 마운트
- `/mnt/uploads/{user_id}/{file_id}.{ext}` (NAS, 권한 mode 0700)
- `/var/cache/query-results/{handle}.parquet` (로컬, TTL 15분)
- 공유 분석 폴더: `/mnt/shared/{folder}` (사용자별 권한 제어, Admin이 마운트 등록)

## 네트워크
- 사내 DB host 화이트리스트 (deny-by-default, SECURITY-07)
- MinIO/NAS는 사내 네트워크 한정

## 백업
- connections, connection_grants, pii_patterns, column_policies → 일 1회
- file_uploads 메타 + 파일 본문 → 일 1회 (선택적, 큰 파일은 NAS 자체 백업에 위임)
- query_executions → 30일 보존 후 archive

## 보안 강화
- 평문 자격증명은 connector 호출 시점에만 메모리 보존
- 파일 업로드는 항상 magic-bytes 검증
- 결과 cache parquet은 사용자 권한 chown
