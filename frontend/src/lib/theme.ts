import { useSyncExternalStore } from 'react'

export type Theme = 'light' | 'dark' | 'system'

const KEY = 'xp-theme' // index.html reads the same key before first paint
const media = typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: dark)') : null
const listeners = new Set<() => void>()

function read(): Theme {
  try {
    const saved = localStorage.getItem(KEY)
    return saved === 'light' || saved === 'dark' ? saved : 'system'
  } catch {
    return 'system'
  }
}

let theme: Theme = read()

export const resolve = (t: Theme): 'light' | 'dark' => (t === 'system' ? (media?.matches ? 'dark' : 'light') : t)

function apply() {
  const next = resolve(theme)
  if (document.documentElement.dataset.theme === next) return
  const swap = () => { document.documentElement.dataset.theme = next }
  // Cross-fade the page instead of snapping colours; browsers without view transitions just swap.
  const calm = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
  if (document.startViewTransition && !calm) document.startViewTransition(swap)
  else swap()
}

export function setTheme(next: Theme) {
  theme = next
  try {
    if (next === 'system') localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, next)
  } catch { /* private mode: the choice just won't persist */ }
  apply()
  listeners.forEach(l => l())
}

media?.addEventListener('change', () => {
  if (theme !== 'system') return
  apply()
  listeners.forEach(l => l())
})

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useTheme() {
  const current = useSyncExternalStore(subscribe, () => theme)
  return { theme: current, resolved: resolve(current), setTheme }
}
