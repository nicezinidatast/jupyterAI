/**
 * 플랫폼 로그인/회원가입 페이지 컴포넌트.
 *
 * 이 파일은 세 가지 폼 컴포넌트와 레이아웃 헬퍼를 포함한다:
 *  - AuthPage   : 마운트 시 /me 로 기존 세션을 확인하고, 이미 로그인된 사용자를
 *                 즉시 분석 워크스페이스(/analyst/)로 보낸다. 미인증이면 로그인 탭을 표시한다.
 *  - LoginForm  : username + password → /login API 호출 → 세션 쿠키 수신 → 리다이렉트.
 *  - SignupForm : username + password + confirm → 클라이언트 유효성 검사 →
 *                 /signup API 호출 → 회원가입 즉시 로그인(세션 쿠키) → 리다이렉트.
 *  - Background : 그라데이션 전체화면 래퍼. 재사용 목적으로 분리했다.
 *
 * 인증 흐름 요약:
 *  세션은 httpOnly 쿠키로 관리된다. 폼 제출 시 authApi 가 `credentials: 'include'` 로
 *  요청을 보내면 서버가 Set-Cookie 로 세션 쿠키를 내려준다. 이후 모든 API 요청에
 *  브라우저가 자동으로 쿠키를 포함하므로 JWT 를 클라이언트에 저장할 필요가 없다.
 */
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

/**
 * 아이디 유효성 정규식 — 백엔드 login_router.SignupBody 의 검증 조건과 동일해야 한다.
 * 프론트엔드에서 먼저 걸러서 불필요한 API 왕복을 줄이지만,
 * 서버 측 검증이 최종 진실이므로 422 응답도 별도로 처리한다.
 */
// Must mirror the backend validation (login_router.SignupBody).
const USERNAME_RE = /^[A-Za-z0-9_.-]{3,20}$/;
const PASSWORD_MIN = 4;

/**
 * 인증 페이지 루트 컴포넌트.
 *
 * 마운트 시 authApi.me() 로 기존 세션을 확인한다:
 *  - 성공(세션 유효): goToAnalyst() 로 즉시 리다이렉트한다.
 *    이미 로그인된 사용자가 /login/ 에 접근했을 때 폼이 깜빡이지 않게 하는 핵심 트릭이다.
 *  - 실패(세션 없음 또는 401): checking = false 로 전환해 로그인 폼을 표시한다.
 *
 * cancelled 플래그를 두는 이유: 컴포넌트가 언마운트된 뒤 비동기 콜백이 setState 를
 * 호출하면 React 가 경고를 낸다. 클린업 함수에서 cancelled = true 로 막는다.
 */
export function AuthPage() {
  // While we check /me on mount we show a full-screen loader instead of the
  // form, so an already-authenticated user never sees a flash of the login UI.
  // 마운트 시 /me 확인 중에는 전체화면 Loader 를 표시해 이미 인증된 사용자가
  // 로그인 폼을 순간이라도 보지 않게 한다.
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState<Mode>('login');

  useEffect(() => {
    let cancelled = false;
    authApi
      .me()
      .then(() => {
        // 세션이 유효하면 워크스페이스로 바로 이동한다.
        if (!cancelled) goToAnalyst();
      })
      .catch(() => {
        // 세션이 없거나 오류면 로그인 폼을 표시한다.
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true; // 언마운트 시 비동기 setState 를 차단한다
    };
  }, []);

  // 세션 확인 중에는 폼 대신 스피너를 보여준다.
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

          {/* 로그인/회원가입 탭: mode 상태로 제어하며, SignupForm 성공 시 onDone 으로 로그인 탭으로 돌아올 수 있다 */}
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
                {/* onDone: 회원가입 완료 후 로그인 탭으로 전환하는 콜백. 현재는 자동 로그인이므로 실제로 호출되지 않는다. */}
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

/**
 * 전체화면 그라데이션 배경 래퍼.
 * AuthPage 와 로딩 상태 양쪽에서 재사용해 배경 색상을 일관되게 유지한다.
 * CSS 변수(--mantine-color-*)를 사용하므로 다크 모드 전환에도 자동 대응된다.
 */
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
/**
 * 로그인 폼 컴포넌트.
 *
 * 제출 흐름:
 *  1) authApi.login() 으로 POST /api/auth/login 을 호출한다.
 *  2) 성공 시 서버가 httpOnly 세션 쿠키를 Set-Cookie 로 내려준다.
 *  3) goToAnalyst() 로 /analyst/ 에 도달하면 모든 이후 요청에 쿠키가 자동 포함된다.
 *
 * 에러 분기:
 *  - 401: 아이디/비밀번호 불일치. 사용자에게 구체적인 이유를 알리되,
 *    어느 쪽이 틀렸는지는 알리지 않는다(보안 원칙).
 *  - 그 외: 서버/네트워크 오류로 간주해 일반 오류 메시지를 표시한다.
 */
function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false); // 중복 제출 방지용 로딩 상태

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
        e.preventDefault(); // 기본 페이지 새로고침 동작을 막고 submit() 을 호출한다
        submit();
      }}
    >
      <Stack gap="sm">
        {/* 에러 메시지: null 이면 렌더링하지 않는다 */}
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
          autoComplete="username" // 브라우저 자동완성이 올바른 필드에 채워지도록 hint 를 준다
        />
        <PasswordInput
          label="비밀번호"
          placeholder="비밀번호"
          required
          value={password}
          onChange={(e) => setPassword(e.currentTarget.value)}
          autoComplete="current-password"
        />
        {/* loading={busy} 로 제출 중 버튼을 비활성화해 중복 요청을 방지한다 */}
        <Button type="submit" fullWidth loading={busy} mt="xs">
          로그인
        </Button>
      </Stack>
    </form>
  );
}

// ── Signup (id / password / password-confirm) ──────────────────────────
/**
 * 회원가입 폼 컴포넌트.
 *
 * @param onDone - 성공 후 호출될 콜백(로그인 탭 복귀 등). 현재는 회원가입 즉시 자동 로그인
 *                 되어 워크스페이스로 이동하므로 실제로 호출되지 않는다.
 *                 향후 "이메일 인증 후 로그인" 등 옵트아웃 시나리오를 위해 보존한다.
 *
 * 유효성 검사(validate):
 *  - 클라이언트에서 먼저 USERNAME_RE / PASSWORD_MIN 을 검사해 API 왕복을 줄인다.
 *  - 비밀번호 확인 불일치도 여기서 잡는다.
 *  - 백엔드에서 409(중복 아이디)/422(형식 오류)가 오면 catch 블록에서 별도 처리한다.
 *
 * 제출 흐름:
 *  1) validate() 통과 후 authApi.signup() 으로 POST /api/auth/signup 을 호출한다.
 *  2) 서버가 세션 쿠키를 즉시 발급하므로(active immediately + auto-logged-in)
 *     별도 로그인 단계 없이 goToAnalyst() 로 이동한다.
 */
function SignupForm({ onDone }: { onDone: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  /**
   * 클라이언트 측 유효성 검사.
   * 오류가 있으면 사용자에게 보여줄 메시지 문자열을 반환하고, 통과하면 null 을 반환한다.
   * 순서: 아이디 형식 → 비밀번호 최소 길이 → 비밀번호 확인 일치.
   */
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
      // 회원가입 즉시 활성화 + 자동 로그인(쿠키 발급) → 워크스페이스로 바로 이동한다.
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
  // onDone 은 로그인 탭으로 돌아가기 위한 콜백이다.
  // 현재는 가입 성공 시 자동 로그인 후 바로 이동하므로 실제로는 호출하지 않는다.
  // 향후 이메일 인증 등 수동 로그인 단계가 추가되면 사용한다.
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
          autoComplete="new-password" // 브라우저가 새 비밀번호로 인식해 기존 비밀번호를 덮어쓰지 않게 한다
        />
        {/* 비밀번호 확인 필드: 한 글자라도 입력한 뒤에만 불일치 오류를 표시해
            빈 상태에서 오류가 먼저 보이는 현상을 막는다 */}
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
