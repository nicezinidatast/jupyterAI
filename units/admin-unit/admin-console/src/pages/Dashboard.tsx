/**
 * Dashboard 페이지 — 플랫폼 운영 현황을 한눈에 볼 수 있는 요약 화면.
 *
 * 데이터 흐름:
 *   statsApi.dashboard() → react-query useQuery → Grid 카드 렌더링
 *
 * 10초 폴링(refetchInterval)을 쓰는 이유:
 *   운영 중 사용자·백업 수 등이 실시간으로 변하므로 관리자가 수동으로
 *   새로고침하지 않아도 최신 상태를 볼 수 있어야 한다.
 *   WebSocket 대신 폴링을 선택한 것은 백엔드 구조가 단순하고 트래픽이 적기 때문이다.
 */
import { useQuery } from '@tanstack/react-query';
import { Badge, Card, Grid, Group, Loader, Stack, Text, Title } from '@mantine/core';
import { statsApi } from '../api/client';

// 대시보드 카드 정의 배열.
// key는 DashboardStats의 필드명과 일치하며, 타입 수준에서 강제한다.
// color가 없는 카드(기본값 gray)는 단순 참조 지표를 나타낸다.
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
  // queryKey: ['stats'] — Users/Backups 페이지의 mutation이 성공 후
  // qc.invalidateQueries({ queryKey: ['stats'] })를 호출해 이 쿼리를 자동 갱신한다.
  const { data, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: statsApi.dashboard,
    refetchInterval: 10_000, // 10초 폴링 — 실시간성과 서버 부하의 균형점
  });

  return (
    <Stack p="md" gap="lg">
      <div>
        <Title order={2}>대시보드</Title>
        <Text c="dimmed" size="sm">
          내부망 데이터 분석 플랫폼 운영 현황. 10초마다 자동 갱신됩니다.
        </Text>
      </div>

      {/* 초기 로딩 시에만 표시한다. refetch 중에는 stale 데이터를 유지해 깜빡임을 줄인다. */}
      {isLoading && <Loader />}
      {error && (
        <Text c="red">통계 로드 실패: {(error as Error).message}</Text>
      )}

      {data && (
        <Grid gutter="md">
          {cards.map((c) => (
            // span 반응형: 전체 화면 12칸 → xs 6칸 → md 3칸 (4열 그리드)
            <Grid.Col key={c.key} span={{ base: 12, xs: 6, md: 3 }}>
              <Card padding="lg" radius="md" withBorder>
                <Group justify="space-between" mb="xs">
                  <Text size="sm" c="dimmed">
                    {c.label}
                  </Text>
                  {/* color가 지정된 카드에만 'live' 배지를 붙여 실시간 갱신 지표임을 표시한다. */}
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
