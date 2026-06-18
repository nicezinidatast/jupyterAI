/**
 * PiiPatterns 페이지 — PII(개인정보 식별 정보) 마스킹 정규식 관리.
 *
 * PII 패턴은 쿼리 결과를 사용자에게 렌더링하기 직전에 적용된다.
 * 매칭되는 텍스트는 마스킹 처리되어 원본 데이터가 화면에 노출되지 않는다.
 *
 * 패턴 종류(kind):
 *   name(이름), rrn(주민번호), phone(전화번호), email(이메일), custom(사용자 정의).
 *   kind는 백엔드에서 기본 정규식 제안 및 분류 목적으로 사용한다.
 *
 * toggle mutation:
 *   is_active를 바꾸는 가장 단순한 방법으로, body 없이 PATCH를 보내고
 *   백엔드가 현재 값을 반전시켜 반환한다. 낙관적 업데이트(optimistic update)는
 *   구현하지 않았다 — 정규식 적용 여부는 즉각 확정 상태가 중요하므로 서버 응답을 기다린다.
 *
 * 정규식 입력 안전성:
 *   백엔드에서 catastrophic backtracking 패턴을 자동 감지·거부한다.
 *   프론트엔드에서 별도 정규식 검증은 하지 않는다.
 */
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

// 지원 PII 종류 목록 — Select 컴포넌트의 선택지로 사용된다.
const KINDS = ['name', 'rrn', 'phone', 'email', 'custom'];

// 종류별 배지 색상 — 민감도 수준을 직관적으로 구분한다.
// rrn(주민번호)은 가장 위험한 식별자이므로 red로 표시한다.
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

  // 신규 패턴 등록 모달 상태
  const [opened, setOpened] = useState(false);
  // 단일 객체 form state — 세 필드를 함께 관리한다.
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

  // toggle: Switch 변경 이벤트에서 바로 mutate를 호출한다.
  // ['pii']만 무효화한다 — 통계에는 PII 패턴 활성 여부가 반영되지 않으므로 ['stats']는 불필요.
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
                {/* Code 컴포넌트로 정규식을 모노스페이스 폰트로 표시한다 */}
                <Table.Td>
                  <Code>{p.regex}</Code>
                </Table.Td>
                <Table.Td>
                  {/* Switch onChange에서 toggle.mutate를 직접 호출한다.
                      checked는 서버 상태(p.is_active)를 그대로 반영한다. */}
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

      {/* 신규 PII 패턴 등록 모달 */}
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
            {/* 이름과 정규식이 모두 채워져야 등록 버튼이 활성화된다 */}
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
