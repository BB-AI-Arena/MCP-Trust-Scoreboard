import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5176,
    proxy: {
      '/scan': 'http://localhost:8004',
      '/health': 'http://localhost:8004',
    },
  },
})
