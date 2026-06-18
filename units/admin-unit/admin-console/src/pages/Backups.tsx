/**
 * Backups 페이지 — 백업 이력 조회 및 즉시 실행.
 *
 * 폴링 전략:
 *   refetchInterval: 5_000 (5초) — 백업은 수초~수십 초가 걸리는 비동기 작업이므로
 *   'running' 상태의 작업이 완료되었는지 폴링으로 추적한다.
 *   WebSocket 스트리밍보다 단순하고, 백업 빈도가 낮아 서버 부하도 미미하다.
 *
 * 즉시 실행(run mutation):
 *   백엔드는 백업 작업을 백그라운드에 올리고 즉시 Backup 객체(state='running')를 반환한다.
 *   onSuccess에서 ['backups']를 무효화해 새 항목이 목록에 즉시 나타나게 한다.
 *
 * fmtBytes:
 *   size_bytes를 사람이 읽기 쉬운 단위로 변환하는 순수 함수.
 *   null이면 '—'을 반환한다 (백업 실패·진행 중일 때 크기 정보 없음).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge, Button, Group, Stack, Table, Text, Title } from '@mantine/core';
import { backupsApi } from '../api/client';

// 백업 상태별 배지 색상.
// 'running'은 yellow — 주의가 필요한 상태임을 표현하되, 에러는 아님을 구분한다.
function stateColor(state: string) {
  switch (state) {
    case 'success': return 'teal';
    case 'failed': return 'red';
    case 'running': return 'yellow';
    default: return 'gray';
  }
}

// 바이트 단위 크기를 B/KB/MB/GB로 변환한다.
// GB 이상에서만 소수점 2자리를 쓰고, 나머지는 1자리로 반올림한다.
function fmtBytes(n: number | null) {
  if (n === null) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function Backups() {
  const qc = useQueryClient();
  // 5초 폴링 — 'running' 상태 백업의 완료를 감지하기 위해 필요하다.
  const { data, isLoading, error } = useQuery({
    queryKey: ['backups'],
    queryFn: backupsApi.list,
    refetchInterval: 5_000,
  });

  // run: 백업 즉시 실행 mutation. 성공 시 목록을 무효화해 새 항목을 반영한다.
  const run = useMutation({
    mutationFn: () => backupsApi.run(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['backups'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  return (
    <Stack p="md" gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>백업 히스토리</Title>
          <Text c="dimmed" size="sm">
            메타DB / 워크스페이스 / Vault 백업 이력. 5초마다 자동 갱신됩니다.
          </Text>
        </div>
        {/* isPending 중 버튼을 loading 상태로 잠가 중복 실행을 방지한다 */}
        <Button
          loading={run.isPending}
          onClick={() => run.mutate()}
        >
          + 지금 백업 실행
        </Button>
      </Group>

      {isLoading && <Text>불러오는 중…</Text>}
      {error && <Text c="red">{(error as Error).message}</Text>}

      {data && (
        <Table striped withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>대상</Table.Th>
              <Table.Th>시작</Table.Th>
              <Table.Th>종료</Table.Th>
              <Table.Th>상태</Table.Th>
              <Table.Th>크기</Table.Th>
              <Table.Th>위치 / 오류</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.map((b) => (
              <Table.Tr key={b.backup_id}>
                {/* target은 'metadb', 'workspace', 'vault' 등의 식별자 */}
                <Table.Td><Badge variant="light">{b.target}</Badge></Table.Td>
                <Table.Td>{new Date(b.started_at).toLocaleString()}</Table.Td>
                {/* ended_at이 null이면 아직 진행 중임을 나타낸다 */}
                <Table.Td>{b.ended_at ? new Date(b.ended_at).toLocaleString() : '진행 중'}</Table.Td>
                <Table.Td>
                  <Badge color={stateColor(b.state)}>{b.state}</Badge>
                </Table.Td>
                <Table.Td>{fmtBytes(b.size_bytes)}</Table.Td>
                <Table.Td>
                  {/* 실패 시 오류 메시지를, 성공 시 저장 위치를 표시한다 */}
                  {b.state === 'failed'
                    ? <Text c="red" size="sm">{b.error}</Text>
                    : <Text size="xs" c="dimmed">{b.location}</Text>}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}
