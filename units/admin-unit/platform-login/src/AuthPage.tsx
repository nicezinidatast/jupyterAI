import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  Center,
  Loader,
  PasswordInput,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
} from '@mantine/core';

import { ApiError, authApi, goToAnalyst } from './api/auth';

type Mode = 'login' | 'signup';

// Must mirror the backend validation (login_router.SignupBody).
const USERNAME_RE = /^[A-Za-z0-9_.-]{3,20}$/;
const PASSWORD_MIN = 4;

export function AuthPage() {
  // While we check /me on mount we show a full-screen loader instead of the
  // form, so an already-authenticated user never sees a flash of the login UI.
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState<Mode>('login');

  useEffect(() => {
    let cancelled = false;
    authApi
      .me()
      .then(() => {
        if (!cancelled) goToAnalyst();
      })
      .catch(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (checking) {
    return (
      <Background>
        <Center mih="100vh">
          <Loader />
        </Center>
      </Background>
    );
  }

  return (
    <Background>
      <Center mih="100vh" px="md" py="xl">
        <Stack gap="lg" align="center" w="100%" maw={420}>
          <Stack gap={4} align="center">
            <Title order={2} ta="center">
              내부망 데이터 분석 플랫폼
            </Title>
            <Text size="sm" c="dimmed" ta="center">
              로그인하거나 새 계정을 만드세요.
            </Text>
          </Stack>

          <Card withBorder radius="md" shadow="sm" p="lg" w="100%">
            <Tabs value={mode} onChange={(v) => v && setMode(v as Mode)} variant="default">
              <Tabs.List grow mb="md">
                <Tabs.Tab value="login">로그인</Tabs.Tab>
                <Tabs.Tab value="signup">회원가입</Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="login">
                <LoginForm />
              </Tabs.Panel>
              <Tabs.Panel value="signup">
                <SignupForm onDone={() => setMode('login')} />
              </Tabs.Panel>
            </Tabs>
          </Card>

          <Text size="xs" c="dimmed" ta="center">
            로그인하면 분석 워크스페이스로 이동합니다.
          </Text>
        </Stack>
      </Center>
    </Background>
  );
}

function Background({ children }: { children: ReactNode }) {
  return (
    <Box
      style={{
        minHeight: '100vh',
        background:
          'linear-gradient(135deg, var(--mantine-color-blue-0), var(--mantine-color-gray-1))',
      }}
    >
      {children}
    </Box>
  );
}

// ── Login ──────────────────────────────────────────────────────────────
function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      await authApi.login({ username, password });
      goToAnalyst();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError('아이디 또는 비밀번호가 올바르지 않습니다.');
      } else {
        setError('로그인 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Stack gap="sm">
        {error && (
          <Alert color="red" variant="light">
            {error}
          </Alert>
        )}
        <TextInput
          label="아이디"
          placeholder="아이디"
          required
          value={username}
          onChange={(e) => setUsername(e.currentTarget.value)}
          autoComplete="username"
        />
        <PasswordInput
          label="비밀번호"
          placeholder="비밀번호"
          required
          value={password}
          onChange={(e) => setPassword(e.currentTarget.value)}
          autoComplete="current-password"
        />
        <Button type="submit" fullWidth loading={busy} mt="xs">
          로그인
        </Button>
      </Stack>
    </form>
  );
}

// ── Signup (id / password / password-confirm) ──────────────────────────
function SignupForm({ onDone }: { onDone: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function validate(): string | null {
    if (!USERNAME_RE.test(username.trim())) {
      return '아이디는 3~20자의 영문/숫자/._- 만 사용할 수 있습니다.';
    }
    if (password.length < PASSWORD_MIN) {
      return `비밀번호는 ${PASSWORD_MIN}자 이상이어야 합니다.`;
    }
    if (password !== confirm) {
      return '비밀번호 확인이 일치하지 않습니다.';
    }
    return null;
  }

  async function submit() {
    setError(null);
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setBusy(true);
    try {
      // Active immediately + auto-logged-in (cookie set) → straight to workspace.
      await authApi.signup({ username: username.trim(), password });
      goToAnalyst();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError('이미 사용 중인 아이디입니다.');
      } else if (e instanceof ApiError && e.status === 422) {
        setError('아이디(3~20자) 또는 비밀번호(4자 이상) 형식을 확인하세요.');
      } else {
        setError('회원가입 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.');
      }
    } finally {
      setBusy(false);
    }
  }

  // `onDone` is available for callers that want to bounce back to the login tab;
  // we auto-login on success so it's only used if you later add an opt-out.
  void onDone;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Stack gap="sm">
        {error && (
          <Alert color="red" variant="light">
            {error}
          </Alert>
        )}
        <TextInput
          label="아이디"
          description="3~20자, 영문/숫자/._-"
          placeholder="아이디"
          required
          value={username}
          onChange={(e) => setUsername(e.currentTarget.value)}
          autoComplete="username"
        />
        <PasswordInput
          label="비밀번호"
          description="4자 이상"
          placeholder="비밀번호"
          required
          value={password}
          onChange={(e) => setPassword(e.currentTarget.value)}
          autoComplete="new-password"
        />
        <PasswordInput
          label="비밀번호 확인"
          placeholder="비밀번호 확인"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.currentTarget.value)}
          autoComplete="new-password"
          error={confirm.length > 0 && confirm !== password ? '일치하지 않습니다' : undefined}
        />
        <Button type="submit" fullWidth loading={busy} mt="xs">
          가입하고 시작하기
        </Button>
      </Stack>
    </form>
  );
}
