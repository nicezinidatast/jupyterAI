import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge, Button, Group, Stack, Table, Text, Title } from '@mantine/core';
import { backupsApi } from '../api/client';

function stateColor(state: string) {
  switch (state) {
    case 'success': return 'teal';
    case 'failed': return 'red';
    case 'running': return 'yellow';
    default: return 'gray';
  }
}

function fmtBytes(n: number | null) {
  if (n === null) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function Backups() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['backups'],
    queryFn: backupsApi.list,
    refetchInterval: 5_000,
  });

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
                <Table.Td><Badge variant="light">{b.target}</Badge></Table.Td>
                <Table.Td>{new Date(b.started_at).toLocaleString()}</Table.Td>
                <Table.Td>{b.ended_at ? new Date(b.ended_at).toLocaleString() : '진행 중'}</Table.Td>
                <Table.Td>
                  <Badge color={stateColor(b.state)}>{b.state}</Badge>
                </Table.Td>
                <Table.Td>{fmtBytes(b.size_bytes)}</Table.Td>
                <Table.Td>
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
