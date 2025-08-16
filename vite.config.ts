/**
 * Vite configuration for the Excelpoint frontend build system.
 * 
 * This configuration sets up the build pipeline for React components,
 * specifically the chat widget that integrates with Django templates.
 * It handles TypeScript compilation, React JSX transformation, and
 * asset bundling for production deployment.
 * 
 * Key features:
 * - React 18 support with JSX transformation
 * - TypeScript compilation and type checking
 * - Path aliases for clean imports (@/components)
 * - Django integration with static/js output
 * - Development server on localhost:3000
 * - Production build optimization
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Output to Django's static directory for template integration
    outDir: 'static/js',
    rollupOptions: {
      input: {
        // Main entry point for the chat widget
        'chat-widget': 'src/main.tsx'
      },
      output: {
        // Clean file naming for Django static file serving
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name].[ext]'
      }
    },
    manifest: true,
    emptyOutDir: true
  },
  resolve: {
    alias: {
      // Enable clean imports like @/components/ChatWidget
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    host: 'localhost',
    port: 3000,
    open: false
  }
}) 