import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Django serves the built index.html at /app/ (config/views.py app_shell); assets live under /static/app/.
const django = 'http://127.0.0.1:8000'

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/app/' : '/',
  build: { outDir: '../static/app', emptyOutDir: true },
  server: {
    port: 5173,
    // Dev: Vite serves the app, Django answers the API and the old pages (cookies ignore the port).
    proxy: Object.fromEntries(['/api', '/users', '/media', '/subjects', '/insights', '/learning'].map(p => [p, django])),
  },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'] },
}))
