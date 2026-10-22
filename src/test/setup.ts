import '@testing-library/jest-dom'
import { afterEach } from 'vitest'

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  root = null
  rootMargin = ''
  thresholds = []
  
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() { return [] }
} as any

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any 
// Node 25+ ships a global localStorage that is broken without --localstorage-file, and it shadows
// jsdom's. Use jsdom's storage so code that persists chat sessions actually runs in tests.
for (const name of ['localStorage', 'sessionStorage'] as const) {
  if (typeof (globalThis as any)[name]?.getItem !== 'function') {
    Object.defineProperty(globalThis, name, {
      value: (globalThis as any).jsdom.window[name],
      configurable: true,
    })
  }
}

// Stored sessions must not leak between tests
afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})
