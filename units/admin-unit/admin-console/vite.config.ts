import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8081';

export default defineConfig({
  plugins: [react()],
  base: '/admin/',
  server: {
    host: true,
    port: 80,
    strictPort: true,
    proxy: { '/api': proxyTarget },
    hmr: { clientPort: 5180 },
    // Polling — Windows host → docker bind mount에서 inotify가 안 통할 때 필수.
    watch: { usePolling: true, interval: 500 },
  },
  // 소스맵은 prod 'rendering chunks' 메모리를 크게 키운다(작은 on-prem 빌드
  // 박스에서 OOM 위험). 포털 prod 이미지엔 불필요하므로 기본 off —
  // 디버그가 필요하면 VITE_SOURCEMAP=true 로 빌드.
  build: { outDir: 'dist', sourcemap: process.env.VITE_SOURCEMAP === 'true' },
});
