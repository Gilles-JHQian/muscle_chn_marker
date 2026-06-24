import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev (two-process) the FastAPI backend runs on :8001 and Vite proxies /api
// to it (see scripts/dev.sh). In production the built dist/ is served by the
// backend itself on a single port, so the proxy is dev-only.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
});
