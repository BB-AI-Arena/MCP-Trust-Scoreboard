import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/agents': { target: 'http://localhost:8002', changeOrigin: true },
      '/baseline': { target: 'http://localhost:8002', changeOrigin: true },
      '/anomalies': { target: 'http://localhost:8002', changeOrigin: true },
      '/summary': { target: 'http://localhost:8002', changeOrigin: true },
      '/ingest': { target: 'http://localhost:8002', changeOrigin: true },
      '/agent-data': { target: 'http://localhost:8002', changeOrigin: true },
    },
  },
});
