import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppShell, Burger, Group, MantineProvider, NavLink, Text, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import '@mantine/core/styles.css';

import { Dashboard } from './pages/Dashboard';
import { Users } from './pages/Users';
import { Connections } from './pages/Connections';
import { PiiPatterns } from './pages/PiiPatterns';
import { Backups } from './pages/Backups';

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

const NAV = [
  { to: '/', label: '대시보드', emoji: '📊' },
  { to: '/users', label: '사용자', emoji: '👥' },
  { to: '/connections', label: '데이터 커넥션', emoji: '🔌' },
  { to: '/pii', label: 'PII 패턴', emoji: '🔒' },
  { to: '/backups', label: '백업', emoji: '💾' },
];

function Shell() {
  const [opened, { toggle }] = useDisclosure();
  const loc = useLocation();

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={4}>🛠️ Dataplatform Admin</Title>
          </Group>
          <Text size="sm" c="dimmed">내부망 데이터 분석 플랫폼 v0.1.0</Text>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            component={Link}
            to={item.to}
            label={`${item.emoji}  ${item.label}`}
            active={
              item.to === '/'
                ? loc.pathname === '/'
                : loc.pathname.startsWith(item.to)
            }
            variant="light"
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/users" element={<Users />} />
          <Route path="/connections" element={<Connections />} />
          <Route path="/pii" element={<PiiPatterns />} />
          <Route path="/backups" element={<Backups />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="light">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter basename="/admin">
          <Shell />
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>
);
