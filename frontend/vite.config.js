import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Served by the FastAPI gateway at the /ui/ base path.
export default defineConfig({
  base: '/ui/',
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI gateway during dev.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
