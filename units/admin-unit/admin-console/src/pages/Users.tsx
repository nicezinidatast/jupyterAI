/**
 * Users 페이지 — 플랫폼 사용자 목록 조회, 신규 생성, 역할 변경, 삭제.
 *
 * 상태 구조:
 *   - useQuery(['users']): 사용자 목록 서버 상태 (react-query 캐시 관리)
 *   - createOpen / newEmail / newName / newRoles / newPassword: 신규 사용자 생성 모달의 로컬 폼 상태
 *     newPassword는 초기 로그인 비밀번호다. 백엔드가 bcrypt로 해싱해 저장한다.
 *     이 값이 없으면 생성된 사용자는 password_hash가 없어 로컬 로그인을 할 수 없다
 *     (admin이 만든 계정으로 로그인이 안 되던 결함의 원인이었다 — 그래서 폼에서 필수로 받는다).
 *   - rolesUser / pendingRoles: 역할 변경 모달의 로컬 상태
 *     rolesUser가 null이면 모달이 닫힌다 (opened={!!rolesUser} 패턴).
 *
 * mutation 성공 후 캐시 무효화 전략:
 *   모든 mutation의 onSuccess에서 ['users']와 ['stats']를 동시에 무효화한다.
 *   ['stats']까지 무효화하는 이유는 Dashboard의 사용자 수 카드가 즉시 갱신되어야 하기 때문이다.
 *   react-query가 두 쿼리를 순차적으로 refetch하므로 별도 동기화 코드는 필요 없다.
 *
 * RBAC(역할 기반 접근 제어) 역할 목록:
 *   Admin > Analyst > Viewer > Auditor 순서로 권한이 낮아진다.
 *   신규 사용자 기본 역할은 'Analyst'다 — 읽기·분석만 허용하는 안전한 기본값.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  MultiSelect,
  PasswordInput,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { usersApi, type User } from '../api/client';

// 플랫폼에서 지원하는 역할 전체 목록.
// 백엔드 enum과 일치해야 하며, 변경 시 여기도 함께 수정한다.
const ALL_ROLES = ['Admin', 'Analyst', 'Viewer', 'Auditor'];

// 역할별 배지 색상 — 시각적으로 권한 수준을 직관적으로 구분하기 위해 색을 고정한다.
// Admin(red)은 위험·고권한을 암시하고, Viewer(gray)는 읽기 전용임을 표현한다.
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
  // qc: 쿼리 캐시를 직접 조작하기 위한 QueryClient 인스턴스
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ['users'], queryFn: usersApi.list });

  // --- 신규 사용자 생성 모달 상태 ---
  const [createOpen, setCreateOpen] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRoles, setNewRoles] = useState<string[]>(['Analyst']); // 기본값: Analyst
  // newPassword: 초기 로그인 비밀번호. 이 값을 보내야 백엔드가 password_hash를 채워
  // 생성된 사용자가 실제로 로그인할 수 있다. 빈 값이면 생성 버튼이 비활성화된다.
  const [newPassword, setNewPassword] = useState('');

  // createUser mutation: 성공 시 모달을 닫고 폼을 초기화한다.
  const createUser = useMutation({
    mutationFn: () =>
      usersApi.create({
        email: newEmail,
        display_name: newName || undefined,
        roles: newRoles,
        password: newPassword,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
      setCreateOpen(false);
      setNewEmail('');
      setNewName('');
      setNewRoles(['Analyst']);
      setNewPassword('');
    },
  });

  // --- 역할 변경 모달 상태 ---
  // rolesUser: 현재 역할을 변경 중인 사용자. null이면 모달 닫힘.
  // pendingRoles: 모달에서 선택 중인 임시 역할 배열. 저장 전까지 서버에 반영되지 않는다.
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

  // --- 비밀번호 초기화 모달 상태 ---
  // pwUser: 비밀번호를 초기화할 대상 사용자. null이면 모달 닫힘.
  // pwValue: 입력 중인 새 비밀번호. 4자 미만이면 초기화 버튼이 비활성화된다.
  const [pwUser, setPwUser] = useState<User | null>(null);
  const [pwValue, setPwValue] = useState('');
  const resetPw = useMutation({
    mutationFn: () => usersApi.resetPassword(pwUser!.user_id, pwValue),
    onSuccess: () => {
      // 비밀번호는 목록에 표시되지 않으므로 캐시 무효화는 필요 없다. 모달만 닫는다.
      setPwUser(null);
      setPwValue('');
    },
  });

  // removeUser: 삭제 전 confirm으로 실수를 방지한다. mutationFn이 id를 직접 받으므로 클로저 불필요.
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
                {/* display_name이 없으면 em 대시로 빈 셀을 채운다 */}
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
                    {/* 역할 버튼 클릭 시 해당 사용자와 현재 역할을 모달 state에 주입한다 */}
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
                    {/* 비밀번호 초기화: 대상 사용자를 모달 state에 주입하고 입력칸을 비운다 */}
                    <Button
                      size="xs"
                      variant="light"
                      color="orange"
                      onClick={() => {
                        setPwUser(u);
                        setPwValue('');
                      }}
                    >
                      비밀번호
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

      {/* 신규 사용자 생성 모달 */}
      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="신규 사용자">
        <Stack>
          <TextInput
            label="이메일"
            description="로그인 아이디로 사용됩니다 (대소문자 구분 없음)."
            placeholder="user@example.com"
            value={newEmail}
            onChange={(e) => setNewEmail(e.currentTarget.value)}
          />
          <TextInput
            label="이름 (선택)"
            value={newName}
            onChange={(e) => setNewName(e.currentTarget.value)}
          />
          {/* 초기 비밀번호 — 이 값이 있어야 생성된 사용자가 실제로 로그인할 수 있다 */}
          <PasswordInput
            label="초기 비밀번호"
            description="이 비밀번호로 로그인합니다. 최소 4자."
            placeholder="비밀번호"
            value={newPassword}
            onChange={(e) => setNewPassword(e.currentTarget.value)}
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
            {/* 이메일이 없거나 비밀번호가 4자 미만이면 생성 버튼을 비활성화한다.
                비밀번호를 필수로 받는 이유: 비밀번호 없이 만들면 로컬 로그인이 불가능하기 때문. */}
            <Button
              loading={createUser.isPending}
              disabled={!newEmail || newPassword.length < 4}
              onClick={() => createUser.mutate()}
            >
              생성
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* 역할 변경 모달 — rolesUser가 null이 아닐 때만 열린다 */}
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

      {/* 비밀번호 초기화 모달 — pwUser가 null이 아닐 때만 열린다 */}
      <Modal opened={!!pwUser} onClose={() => setPwUser(null)} title={`비밀번호 초기화 — ${pwUser?.email}`}>
        <Stack>
          <PasswordInput
            label="새 비밀번호"
            description="최소 4자. 초기화한 비밀번호를 사용자에게 직접 전달하세요."
            placeholder="새 비밀번호"
            value={pwValue}
            onChange={(e) => setPwValue(e.currentTarget.value)}
          />
          {resetPw.isError && (
            <Text c="red" size="sm">{(resetPw.error as Error).message}</Text>
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setPwUser(null)}>취소</Button>
            {/* 4자 미만이면 비활성화해 백엔드 422를 미리 방지한다 */}
            <Button
              loading={resetPw.isPending}
              disabled={pwValue.length < 4}
              onClick={() => resetPw.mutate()}
            >
              초기화
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
