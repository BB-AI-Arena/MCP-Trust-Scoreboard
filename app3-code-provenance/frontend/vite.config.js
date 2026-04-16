import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/scan': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/scan-repo': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/languages': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
    },
  },
});
