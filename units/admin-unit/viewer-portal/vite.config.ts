import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8081';

export default defineConfig({
  plugins: [react()],
  base: '/viewer/',
  server: {
    host: true,
    port: 80,
    strictPort: true,
    proxy: { '/api': proxyTarget },
    hmr: { clientPort: 5180 },
    watch: { usePolling: true, interval: 500 },
  },
  build: { outDir: 'dist', sourcemap: true },
});
