import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, initials } from './api'
import { timeAgo } from './format'
import { setTheme } from './theme'
import { useOneAtATime } from './useOneAtATime'
import { act, renderHook } from '@testing-library/react'

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

describe('useOneAtATime', () => {
  it('ignores a second start until the first request settles', async () => {
    const { result } = renderHook(() => useOneAtATime())
    let finish!: () => void
    const start = vi.fn(() => new Promise<void>(resolve => { finish = resolve }))
    result.current(start)
    result.current(start) // the double click
    expect(start).toHaveBeenCalledTimes(1)
    await act(async () => finish())
    result.current(start)
    expect(start).toHaveBeenCalledTimes(2)
  })

  it('stays locked after a final success, but not after a failure', async () => {
    const { result } = renderHook(() => useOneAtATime())
    const fail = vi.fn(() => Promise.reject(new Error('no')))
    result.current(fail, { final: true })
    await act(async () => {})
    result.current(fail, { final: true })
    expect(fail).toHaveBeenCalledTimes(2)
    const ok = vi.fn(() => Promise.resolve())
    await act(async () => result.current(ok, { final: true }))
    result.current(ok, { final: true })
    expect(ok).toHaveBeenCalledTimes(1)
  })
})
