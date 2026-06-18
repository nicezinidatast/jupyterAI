/**
 * Connections 페이지 — 데이터 커넥션(DB 접속 정보) 관리 화면.
 *
 * 기능:
 *   - 등록된 커넥션 목록 조회 (엔진·호스트·포트·DB·권한 부여 현황)
 *   - 신규 커넥션 등록 (모달 폼)
 *   - 커넥션 삭제
 *   - 커넥션 연결 테스트 (백엔드가 실제 TCP/DB 접속을 시도하고 레이턴시 반환)
 *
 * 커넥션 테스트 상태 관리:
 *   testResults: Record<connection_id, 결과> — 커넥션별로 마지막 테스트 결과를 보관한다.
 *   testingId: 현재 테스트 중인 커넥션 ID — 해당 행의 버튼에만 로딩 스피너를 표시하기 위해 쓴다.
 *   테스트 결과는 서버에 저장하지 않으므로 페이지를 새로고침하면 초기화된다.
 *   useMutation 대신 async 함수(runTest)를 직접 쓴 이유:
 *     테스트는 캐시 무효화 없이 로컬 state만 갱신하므로 react-query mutation이 불필요하다.
 *
 * 권한(grants) 표시:
 *   subject_role과 subject_user_id 중 하나만 값이 있다.
 *   역할 기반 부여면 역할 이름을, 사용자 직접 부여면 user_id를 보여 준다.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { connectionsApi } from '../api/client';

// 지원 DB 엔진 목록. 백엔드의 ENGINE_DRIVERS와 일치해야 한다.
const ENGINES = ['postgres', 'mysql', 'oracle', 'mssql', 'hive', 'impala', 'presto', 'trino'];

// 엔진별 배지 색상 — 관행적인 브랜드 색을 따른다.
// 빅데이터 계열(hive, impala 등)은 grape로 묶는다.
function engineColor(engine: string) {
  if (engine === 'postgres') return 'blue';
  if (engine === 'mysql') return 'orange';
  if (engine === 'oracle') return 'red';
  if (engine === 'mssql') return 'cyan';
  return 'grape';  // big-data
}

export function Connections() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['connections'],
    queryFn: connectionsApi.list,
  });

  // 신규 커넥션 모달 열림 여부
  const [opened, setOpened] = useState(false);
  // 단일 객체 form state — 여러 필드를 하나로 묶어 관련 상태가 흩어지지 않게 한다.
  const [form, setForm] = useState({
    name: '',
    engine: 'postgres',
    host: '',
    port: 5432,  // postgres 기본 포트
    database: '',
  });

  const create = useMutation({
    mutationFn: () =>
      connectionsApi.create({
        name: form.name,
        engine: form.engine,
        host: form.host,
        port: form.port,
        // 빈 문자열은 undefined로 변환해 백엔드에 null로 저장되게 한다.
        database: form.database || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['connections'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
      setOpened(false);
      // 폼을 기본값으로 리셋
      setForm({ name: '', engine: 'postgres', host: '', port: 5432, database: '' });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => connectionsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['connections'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  // 커넥션별 마지막 테스트 결과를 보관한다.
  // 키: connection_id, 값: 백엔드가 반환한 TestConnectionResult
  const [testResults, setTestResults] = useState<
    Record<string, { ok: boolean; latency_ms: number | null; reason: string | null }>
  >({});
  // 현재 테스트 중인 커넥션 ID — null이면 테스트 중인 항목 없음
  const [testingId, setTestingId] = useState<string | null>(null);

  // runTest: API 호출 실패도 결과로 기록해 사용자에게 오류 메시지를 보여 준다.
  const runTest = async (id: string) => {
    setTestingId(id);
    try {
      const r = await connectionsApi.test(id);
      setTestResults((prev) => ({ ...prev, [id]: r }));
    } catch (e) {
      // 네트워크 오류·백엔드 예외를 reason 필드에 담아 실패로 표시한다.
      setTestResults((prev) => ({
        ...prev,
        [id]: { ok: false, latency_ms: null, reason: (e as Error).message },
      }));
    } finally {
      setTestingId(null);
    }
  };

  return (
    <Stack p="md" gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>데이터 커넥션</Title>
          <Text c="dimmed" size="sm">
            등록된 RDBMS/Big-Data 커넥션. 권한은 역할 기반으로 자동 부여됩니다.
          </Text>
        </div>
        <Button onClick={() => setOpened(true)}>+ 신규 커넥션</Button>
      </Group>

      {isLoading && <Text>불러오는 중…</Text>}
      {error && <Text c="red">{(error as Error).message}</Text>}

      {data && (
        <Table striped withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>이름</Table.Th>
              <Table.Th>엔진</Table.Th>
              <Table.Th>호스트</Table.Th>
              <Table.Th>포트</Table.Th>
              <Table.Th>DB</Table.Th>
              <Table.Th>권한</Table.Th>
              <Table.Th>액션</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.map((c) => (
              <Table.Tr key={c.connection_id}>
                <Table.Td>{c.name}</Table.Td>
                <Table.Td>
                  <Badge color={engineColor(c.engine)} variant="filled">{c.engine}</Badge>
                </Table.Td>
                <Table.Td>{c.host}</Table.Td>
                <Table.Td>{c.port}</Table.Td>
                <Table.Td>{c.database ?? '—'}</Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    {/* 역할 기반 부여면 역할명을, 사용자 직접 부여면 user_id를 표시한다 */}
                    {c.grants.map((g, i) => (
                      <Badge key={i} variant="light" color="teal">
                        {(g.subject_role ?? g.subject_user_id ?? '?')}:{g.action}
                      </Badge>
                    ))}
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" wrap="nowrap">
                    {/* loading 조건: 이 행의 커넥션 ID가 testingId와 같을 때만 스피너를 표시한다 */}
                    <Button
                      size="xs"
                      variant="light"
                      loading={testingId === c.connection_id}
                      onClick={() => runTest(c.connection_id)}
                    >
                      테스트
                    </Button>
                    {/* 테스트 결과가 있으면 성공/실패 배지를 즉시 표시한다 */}
                    {testResults[c.connection_id] && (
                      <Badge
                        color={testResults[c.connection_id].ok ? 'green' : 'red'}
                        variant="filled"
                      >
                        {testResults[c.connection_id].ok
                          ? `OK ${testResults[c.connection_id].latency_ms}ms`
                          : testResults[c.connection_id].reason ?? '실패'}
                      </Badge>
                    )}
                    <ActionIcon
                      color="red"
                      variant="light"
                      onClick={() => {
                        if (confirm(`커넥션 "${c.name}"을 삭제할까요?`)) {
                          remove.mutate(c.connection_id);
                        }
                      }}
                    >
                      ✕
                    </ActionIcon>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* 신규 커넥션 등록 모달 */}
      <Modal opened={opened} onClose={() => setOpened(false)} title="신규 커넥션">
        <Stack>
          <TextInput
            label="이름"
            placeholder="sales_db"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <Select
            label="엔진"
            data={ENGINES}
            value={form.engine}
            onChange={(v) => setForm({ ...form, engine: v ?? 'postgres' })}
          />
          <TextInput
            label="호스트"
            placeholder="db.internal"
            value={form.host}
            onChange={(e) => setForm({ ...form, host: e.currentTarget.value })}
          />
          <NumberInput
            label="포트"
            value={form.port}
            onChange={(v) => setForm({ ...form, port: typeof v === 'number' ? v : 0 })}
          />
          <TextInput
            label="데이터베이스 (선택)"
            value={form.database}
            onChange={(e) => setForm({ ...form, database: e.currentTarget.value })}
          />
          {create.isError && <Text c="red" size="sm">{(create.error as Error).message}</Text>}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setOpened(false)}>취소</Button>
            {/* 이름·호스트·포트가 모두 채워져야 등록 버튼이 활성화된다 */}
            <Button
              loading={create.isPending}
              disabled={!form.name || !form.host || !form.port}
              onClick={() => create.mutate()}
            >
              등록
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
