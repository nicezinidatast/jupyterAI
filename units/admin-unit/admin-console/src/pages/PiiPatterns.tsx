import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ActionIcon,
  Badge,
  Button,
  Code,
  Group,
  Modal,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { piiApi } from '../api/client';

const KINDS = ['name', 'rrn', 'phone', 'email', 'custom'];

function kindColor(kind: string) {
  switch (kind) {
    case 'name': return 'pink';
    case 'rrn': return 'red';
    case 'phone': return 'orange';
    case 'email': return 'blue';
    default: return 'gray';
  }
}

export function PiiPatterns() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ['pii'], queryFn: piiApi.list });

  const [opened, setOpened] = useState(false);
  const [form, setForm] = useState({ name: '', kind: 'custom', regex: '' });

  const create = useMutation({
    mutationFn: () => piiApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pii'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
      setOpened(false);
      setForm({ name: '', kind: 'custom', regex: '' });
    },
  });

  const toggle = useMutation({
    mutationFn: (id: string) => piiApi.toggle(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pii'] }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => piiApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pii'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  return (
    <Stack p="md" gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>PII 마스킹 패턴</Title>
          <Text c="dimmed" size="sm">
            결과 렌더링 직전에 적용되는 PII 정규식. catastrophic backtracking 패턴은 자동 거부됩니다.
          </Text>
        </div>
        <Button onClick={() => setOpened(true)}>+ 신규 패턴</Button>
      </Group>

      {isLoading && <Text>불러오는 중…</Text>}
      {error && <Text c="red">{(error as Error).message}</Text>}

      {data && (
        <Table striped withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>이름</Table.Th>
              <Table.Th>종류</Table.Th>
              <Table.Th>정규식</Table.Th>
              <Table.Th>활성</Table.Th>
              <Table.Th>액션</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.map((p) => (
              <Table.Tr key={p.pattern_id}>
                <Table.Td>{p.name}</Table.Td>
                <Table.Td>
                  <Badge color={kindColor(p.kind)} variant="light">{p.kind}</Badge>
                </Table.Td>
                <Table.Td>
                  <Code>{p.regex}</Code>
                </Table.Td>
                <Table.Td>
                  <Switch
                    checked={p.is_active}
                    onChange={() => toggle.mutate(p.pattern_id)}
                  />
                </Table.Td>
                <Table.Td>
                  <ActionIcon
                    color="red"
                    variant="light"
                    onClick={() => {
                      if (confirm(`"${p.name}" 패턴을 삭제할까요?`)) {
                        remove.mutate(p.pattern_id);
                      }
                    }}
                  >
                    ✕
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={opened} onClose={() => setOpened(false)} title="신규 PII 패턴">
        <Stack>
          <TextInput
            label="이름"
            placeholder="Custom Card Number"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
          />
          <Select
            label="종류"
            data={KINDS}
            value={form.kind}
            onChange={(v) => setForm({ ...form, kind: v ?? 'custom' })}
          />
          <TextInput
            label="정규식"
            placeholder="\b\d{4}-\d{4}-\d{4}-\d{4}\b"
            value={form.regex}
            onChange={(e) => setForm({ ...form, regex: e.currentTarget.value })}
          />
          {create.isError && <Text c="red" size="sm">{(create.error as Error).message}</Text>}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setOpened(false)}>취소</Button>
            <Button
              loading={create.isPending}
              disabled={!form.name || !form.regex}
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
