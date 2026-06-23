import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8081';

export default defineConfig({
  plugins: [react()],
  base: '/analyst/',
  server: {
    host: true,
    port: 80,
    strictPort: true,
    proxy: { '/api': proxyTarget },
    hmr: { clientPort: 5180 },
    watch: { usePolling: true, interval: 500 },
  },
  build: {
    outDir: 'dist',
    // plotly(수 MB) + mantine 번들이라 'rendering chunks'가 빌드 최대 메모리
    // 구간. 소스맵은 이 구간 메모리를 약 2배로 키워 작은 on-prem 빌드 박스에서
    // OOM(SIGKILL)을 일으킨다 → prod 기본 off(디버그 시 VITE_SOURCEMAP=true).
    sourcemap: process.env.VITE_SOURCEMAP === 'true',
    // plotly를 별도 청크로 분리 → 청크 렌더 peak 메모리 완화 + 브라우저 캐싱.
    rollupOptions: {
      output: {
        manualChunks: { plotly: ['plotly.js-dist-min', 'react-plotly.js'] },
      },
    },
  },
});
