import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist' },
  server: {
    proxy: {
      '/api': 'http://localhost:8002',
      '/auth': 'http://localhost:8002',
      '/admin': 'http://localhost:8002',
    }
  }
})
