/**
 * Vitest configuration for the Excelpoint frontend testing suite.
 * 
 * This configuration sets up the testing environment for React components
 * using Vitest as the test runner. It provides a modern, fast testing
 * experience with full TypeScript support and React testing utilities.
 * 
 * Key features:
 * - React component testing with jsdom environment
 * - TypeScript compilation and type checking
 * - Path aliases for clean imports (@/components)
 * - Global test utilities and setup files
 * - Fast test execution with Vite bundling
 */

/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
  resolve: {
    alias: {
      // Enable clean imports like @/components/ChatWidget in tests
      '@': path.resolve(__dirname, './src')
    }
  }
}) 