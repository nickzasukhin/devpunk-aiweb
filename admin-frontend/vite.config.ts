import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist' },
  server: {
    proxy: {
      '/api': { target: 'https://api.devpunks.io', changeOrigin: true, secure: true },
      '/auth': { target: 'https://api.devpunks.io', changeOrigin: true, secure: true },
      '/admin': { target: 'https://api.devpunks.io', changeOrigin: true, secure: true },
    }
  }
})
