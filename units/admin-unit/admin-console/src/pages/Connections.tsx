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

const ENGINES = ['postgres', 'mysql', 'oracle', 'mssql', 'hive', 'impala', 'presto', 'trino'];

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

  const [opened, setOpened] = useState(false);
  const [form, setForm] = useState({
    name: '',
    engine: 'postgres',
    host: '',
    port: 5432,
    database: '',
  });

  const create = useMutation({
    mutationFn: () =>
      connectionsApi.create({
        name: form.name,
        engine: form.engine,
        host: form.host,
        port: form.port,
        database: form.database || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['connections'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
      setOpened(false);
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

  const [testResults, setTestResults] = useState<
    Record<string, { ok: boolean; latency_ms: number | null; reason: string | null }>
  >({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const runTest = async (id: string) => {
    setTestingId(id);
    try {
      const r = await connectionsApi.test(id);
      setTestResults((prev) => ({ ...prev, [id]: r }));
    } catch (e) {
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
                    {c.grants.map((g, i) => (
                      <Badge key={i} variant="light" color="teal">
                        {(g.subject_role ?? g.subject_user_id ?? '?')}:{g.action}
                      </Badge>
                    ))}
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs" wrap="nowrap">
                    <Button
                      size="xs"
                      variant="light"
                      loading={testingId === c.connection_id}
                      onClick={() => runTest(c.connection_id)}
                    >
                      테스트
                    </Button>
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
