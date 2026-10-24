import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Node 25 ships its own localStorage global that shadows jsdom's; use jsdom's (same fix as the widget).
const jsdomWindow = (globalThis as { jsdom?: { window: Window } }).jsdom?.window
if (jsdomWindow) {
  Object.defineProperty(globalThis, 'localStorage', { value: jsdomWindow.localStorage, configurable: true })
}

window.scrollTo = () => {} // jsdom has no scrolling; ScrollRestoration calls it

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
})
