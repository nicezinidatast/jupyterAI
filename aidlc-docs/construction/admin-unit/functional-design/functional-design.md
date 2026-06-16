# admin-unit — Functional Design

**모듈**: AdminConsole(SPA), AuditorConsole(SPA), JupyterExtensionsBundle, AdminService, BackupService, BackupScheduler, RestoreVerifier

---

## 1. SPA 구조 (React 18 + Vite + TypeScript)

### AdminConsole 화면
- 대시보드: 시스템 헬스 (Grafana embed iframe + 자체 위젯)
- 사용자/역할 관리
- 커넥션 관리 (CRUD + 권한 부여)
- PII 패턴 관리
- 백업 상태 + 수동 트리거

### AuditorConsole 화면
- 감사 로그 검색
- 필터 (사용자, 기간, 액션, 리소스)
- CSV/JSON 내보내기
- 권한-사용 매트릭스 (분기별 자동 보고서)

### JupyterExtensionsBundle
- ConnectionPanel (사이드 패널: 등록된 커넥션 + 스키마 트리)
- SqlEditorExtensions (자동완성, 구문 강조 — 백엔드 SchemaIntrospector 호출)
- ChartButton (결과 셀에 "차트 변환" 버튼)

## 2. 데이터 모델

```sql
CREATE TABLE backups (
    backup_id UUID PRIMARY KEY,
    target TEXT NOT NULL,           -- 'meta_db', 'workspaces', 'vault_export'
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    state TEXT NOT NULL DEFAULT 'running' CHECK (state IN ('running','success','failed')),
    size_bytes BIGINT,
    location TEXT,
    error TEXT
);

CREATE TABLE restore_rehearsals (
    rehearsal_id UUID PRIMARY KEY,
    backup_id UUID NOT NULL REFERENCES backups(backup_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    state TEXT NOT NULL DEFAULT 'running' CHECK (state IN ('running','success','failed')),
    report JSONB
);

CREATE TABLE quarterly_access_reviews (
    review_id UUID PRIMARY KEY,
    quarter TEXT NOT NULL UNIQUE,    -- '2026Q2'
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    report_path TEXT NOT NULL        -- PDF 또는 markdown
);
```

## 3. 핵심 비즈니스 룰

### 3.1 사용자/역할 관리 (US-ADM-01)
- AdminService.searchUsers(filter, page) — 1000명 이하 가정, page 50
- 검색은 200ms 내 응답 (인덱스 보장)
- 역할 변경은 auth-unit.RoleResolver.changeRole 위임 (트랜잭션 + invariant)

### 3.2 커넥션 관리 (US-ADM-02)
- 콘솔 UI는 data-unit 의 API 호출
- 활성 쿼리 있는 커넥션 삭제 시 경고 + 강제 옵션
- 강제 삭제 시 활성 쿼리 모두 cancel + 감사

### 3.3 PII 패턴 관리 (US-ADM-03)
- AdminService.addPiiPattern → data-unit.PiiPolicyStore.add_pattern 위임
- 정규식 검증 + 테스트 입력으로 매칭 확인 (UI에서 실시간)

### 3.4 헬스 대시보드 (US-ADM-04)
- Grafana 임베드 (iframe with SSO token forward)
- 자체 위젯: outbox depth, 활성 사용자 수, 최근 5xx 비율
- 15초 단위 갱신 (WebSocket 또는 polling)

### 3.5 백업 (US-ADM-05)
```text
BackupService.runScheduled():
  for target in (meta_db, workspaces, vault_export):
    backup_id = uuid4()
    INSERT INTO backups(backup_id, target, ...)
    spawn backup process
    on complete: UPDATE state + size_bytes + location
    on failure 3 consecutive (track via backups 테이블): alert Admin/Auditor
```

- 메타DB: pg_dump → 사내 백업 스토리지 (NAS or S3)
- workspaces: tar.gz 또는 rsync → 사내 백업 스토리지
- vault_export: Vault snapshot (Vault Enterprise) 또는 secret 메타데이터만

### 3.6 복구 리허설 (US-ADM-05)
```text
RestoreVerifier.monthlyRehearsal():
  latest_backup = SELECT ... ORDER BY started_at DESC LIMIT 1
  spawn isolated docker compose env from backup
  run smoke tests (SELECT 1, user count, etc.)
  generate report → restore_rehearsals.report (jsonb)
  emit audit('rehearsal_completed', result)
```

### 3.7 분기 권한 리뷰 (NFR-AUDIT-03)
- 분기 시작 시 자동: 사용자별 역할 + 마지막 90일 활동 매트릭스 생성
- markdown 또는 PDF로 저장 → 사내 보안팀에 자동 송부 (메일)

## 4. 외부 의존
- auth-unit, data-unit, audit-unit, credential-unit (API 호출)
- Prometheus + Grafana (대시보드 데이터)
- 사내 백업 스토리지
- 사내 메일 시스템 (SMTP 또는 사내 메신저 API)

## 5. Story 매핑
US-ADM-01~05, US-VIS-04 (JupyterExt의 ChartButton), US-DS-05 (JupyterExt의 ConnectionPanel), US-NB-04 (JupyterExt의 SqlEditor)
