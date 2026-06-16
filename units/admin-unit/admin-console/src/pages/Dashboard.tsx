import { useQuery } from '@tanstack/react-query';
import { Badge, Card, Grid, Group, Loader, Stack, Text, Title } from '@mantine/core';
import { statsApi } from '../api/client';

const cards: { key: keyof Awaited<ReturnType<typeof statsApi.dashboard>>; label: string; color?: string }[] = [
  { key: 'users', label: '전체 사용자' },
  { key: 'active_users', label: '활성 사용자', color: 'teal' },
  { key: 'connections', label: '데이터 커넥션', color: 'blue' },
  { key: 'pii_patterns', label: 'PII 패턴', color: 'grape' },
  { key: 'notebooks', label: '노트북', color: 'orange' },
  { key: 'audit_events_last_24h', label: '감사 이벤트', color: 'pink' },
  { key: 'backups_successful', label: '백업 성공', color: 'green' },
  { key: 'backups_failed', label: '백업 실패', color: 'red' },
];

export function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: statsApi.dashboard,
    refetchInterval: 10_000,
  });

  return (
    <Stack p="md" gap="lg">
      <div>
        <Title order={2}>대시보드</Title>
        <Text c="dimmed" size="sm">
          내부망 데이터 분석 플랫폼 운영 현황. 10초마다 자동 갱신됩니다.
        </Text>
      </div>

      {isLoading && <Loader />}
      {error && (
        <Text c="red">통계 로드 실패: {(error as Error).message}</Text>
      )}

      {data && (
        <Grid gutter="md">
          {cards.map((c) => (
            <Grid.Col key={c.key} span={{ base: 12, xs: 6, md: 3 }}>
              <Card padding="lg" radius="md" withBorder>
                <Group justify="space-between" mb="xs">
                  <Text size="sm" c="dimmed">
                    {c.label}
                  </Text>
                  {c.color && <Badge color={c.color} variant="light">live</Badge>}
                </Group>
                <Text size="xl" fw={700}>
                  {data[c.key]}
                </Text>
              </Card>
            </Grid.Col>
          ))}
        </Grid>
      )}
    </Stack>
  );
}
