import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  MultiSelect,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { usersApi, type User } from '../api/client';

const ALL_ROLES = ['Admin', 'Analyst', 'Viewer', 'Auditor'];

function roleColor(role: string) {
  switch (role) {
    case 'Admin': return 'red';
    case 'Analyst': return 'blue';
    case 'Viewer': return 'gray';
    case 'Auditor': return 'grape';
    default: return 'dark';
  }
}

export function Users() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ['users'], queryFn: usersApi.list });

  const [createOpen, setCreateOpen] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRoles, setNewRoles] = useState<string[]>(['Analyst']);

  const createUser = useMutation({
    mutationFn: () =>
      usersApi.create({ email: newEmail, display_name: newName || undefined, roles: newRoles }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
      setCreateOpen(false);
      setNewEmail('');
      setNewName('');
      setNewRoles(['Analyst']);
    },
  });

  const [rolesUser, setRolesUser] = useState<User | null>(null);
  const [pendingRoles, setPendingRoles] = useState<string[]>([]);
  const saveRoles = useMutation({
    mutationFn: () => usersApi.setRoles(rolesUser!.user_id, pendingRoles),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
      setRolesUser(null);
    },
  });

  const removeUser = useMutation({
    mutationFn: (id: string) => usersApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
    },
  });

  return (
    <Stack p="md" gap="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>사용자 관리</Title>
          <Text c="dimmed" size="sm">
            플랫폼 사용자와 역할 (Admin / Analyst / Viewer / Auditor).
          </Text>
        </div>
        <Button onClick={() => setCreateOpen(true)}>+ 신규 사용자</Button>
      </Group>

      {isLoading && <Text>불러오는 중…</Text>}
      {error && <Text c="red">{(error as Error).message}</Text>}

      {data && (
        <Table striped withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>이메일</Table.Th>
              <Table.Th>이름</Table.Th>
              <Table.Th>역할</Table.Th>
              <Table.Th>상태</Table.Th>
              <Table.Th>가입일</Table.Th>
              <Table.Th>액션</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {data.map((u) => (
              <Table.Tr key={u.user_id}>
                <Table.Td>{u.email}</Table.Td>
                <Table.Td>{u.display_name ?? '—'}</Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    {u.roles.map((r) => (
                      <Badge key={r} color={roleColor(r)} variant="light">
                        {r}
                      </Badge>
                    ))}
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Badge color={u.is_active ? 'teal' : 'gray'}>
                    {u.is_active ? '활성' : '비활성'}
                  </Badge>
                </Table.Td>
                <Table.Td>{new Date(u.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        setRolesUser(u);
                        setPendingRoles(u.roles);
                      }}
                    >
                      역할
                    </Button>
                    <ActionIcon
                      color="red"
                      variant="light"
                      onClick={() => {
                        if (confirm(`정말 ${u.email}를 삭제할까요?`)) {
                          removeUser.mutate(u.user_id);
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

      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="신규 사용자">
        <Stack>
          <TextInput
            label="이메일"
            placeholder="user@example.com"
            value={newEmail}
            onChange={(e) => setNewEmail(e.currentTarget.value)}
          />
          <TextInput
            label="이름 (선택)"
            value={newName}
            onChange={(e) => setNewName(e.currentTarget.value)}
          />
          <MultiSelect
            label="역할"
            data={ALL_ROLES}
            value={newRoles}
            onChange={setNewRoles}
          />
          {createUser.isError && (
            <Text c="red" size="sm">{(createUser.error as Error).message}</Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCreateOpen(false)}>취소</Button>
            <Button
              loading={createUser.isPending}
              disabled={!newEmail}
              onClick={() => createUser.mutate()}
            >
              생성
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={!!rolesUser} onClose={() => setRolesUser(null)} title={`역할 변경 — ${rolesUser?.email}`}>
        <Stack>
          <MultiSelect data={ALL_ROLES} value={pendingRoles} onChange={setPendingRoles} />
          {saveRoles.isError && (
            <Text c="red" size="sm">{(saveRoles.error as Error).message}</Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRolesUser(null)}>취소</Button>
            <Button loading={saveRoles.isPending} onClick={() => saveRoles.mutate()}>저장</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
