/**
 * 플랫폼 로그인 SPA 진입점.
 *
 * 이 앱은 감사자 콘솔·분석 워크스페이스와 별도 Vite 빌드다.
 * 단일 페이지(AuthPage)만 존재하므로 라우터를 두지 않는다.
 *
 * React.StrictMode: 개발 중 이중 렌더링·effect 를 통해 부작용을 조기에 발견한다.
 *   프로덕션 빌드에서는 StrictMode 오버헤드가 제거된다.
 * MantineProvider: defaultColorScheme="light" 로 항상 라이트 테마를 강제한다.
 *   내부망 운영 환경에서 사용자 선호와 무관하게 일관된 UI 를 보장하기 위함이다.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';

import { AuthPage } from './AuthPage';

// document.getElementById('root')! — HTML 의 <div id="root"> 가 반드시 존재한다고 단언한다.
// index.html 에 해당 요소가 없으면 런타임 오류가 발생한다.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MantineProvider defaultColorScheme="light">
      <AuthPage />
    </MantineProvider>
  </React.StrictMode>
);
