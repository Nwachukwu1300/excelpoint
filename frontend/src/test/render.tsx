import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { vi } from 'vitest'
import type { Me } from '../lib/api'
import { routes } from '../router'

export const me: Me = {
  id: 1, username: 'alex', first_name: 'Alex', last_name: 'Morgan', email: 'alex@example.com',
  unread_notifications: 2, due_count: 20,
  subjects: [{ id: 3, name: 'Database Systems', due_count: 12 }, { id: 4, name: 'Maths', due_count: 0 }],
}

type Handler = (init: RequestInit | undefined) => { status?: number; body: unknown }

/** Stub fetch by "METHOD /path"; anything unexpected fails loudly. Returns the mock to inspect calls. */
export function mockApi(handlers: Record<string, Handler | unknown>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${String(input)}`
    if (!(key in handlers)) throw new Error(`Unexpected request: ${key}`)
    const handler = handlers[key]
    const { status = 200, body } = typeof handler === 'function' ? (handler as Handler)(init) : { body: handler }
    if (status === 204) return new Response(null, { status }) // a 204 can't carry a body
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

export function renderApp(path = '/') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

export const emptyHome = { due: { count: 0, subjects: 0, minutes: 0 }, suggestions: [], recent_chats: [], subjects: [] }

/** A handler for mockApi that answers with a status code (plain objects are always 200 bodies). */
export const reply = (status: number, body: unknown = null) => () => ({ status, body })
