import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, initials } from './api'
import { timeAgo } from './format'
import { setTheme } from './theme'

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('sends the CSRF token only on unsafe requests and raises ApiError with the server detail', async () => {
    document.cookie = 'csrftoken=abc%3D'
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ detail: 'Nope' }), { status: 400 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api('/api/x/', { method: 'POST', body: { a: 1 } })).rejects.toMatchObject({ status: 400, message: 'Nope' })
    const [, post] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(post.headers).toMatchObject({ 'X-CSRFToken': 'abc=', 'Content-Type': 'application/json' })
    expect(post.credentials).toBe('same-origin')

    await expect(api('/api/x/')).rejects.toBeInstanceOf(ApiError)
    const [, get] = fetchMock.mock.calls[1] as unknown as [string, RequestInit]
    expect(get.headers).not.toHaveProperty('X-CSRFToken')
  })
})

describe('helpers', () => {
  it('builds initials', () => {
    expect(initials('Alex Morgan')).toBe('AM')
    expect(initials('sam')).toBe('S')
    expect(initials('')).toBe('?')
  })

  it('formats relative times', () => {
    const now = Date.parse('2026-10-24T12:00:00Z')
    expect(timeAgo('2026-10-24T11:59:50Z', now)).toBe('just now')
    expect(timeAgo('2026-10-24T11:58:00Z', now)).toBe('2 minutes ago')
    expect(timeAgo('2026-10-23T12:00:00Z', now)).toBe('yesterday')
  })

  it('applies and persists the theme', () => {
    setTheme('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('xp-theme')).toBe('dark')
    setTheme('system') // no matchMedia in jsdom, so system resolves to light
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(localStorage.getItem('xp-theme')).toBeNull()
  })
})
