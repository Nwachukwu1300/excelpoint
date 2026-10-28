import { useQuery } from '@tanstack/react-query'

export class ApiError extends Error {
  status: number
  data: unknown
  constructor(status: number, message: string, data?: unknown) {
    super(message)
    this.status = status
    this.data = data
  }
}

/** Django sets `csrftoken` (not HttpOnly) via /api/me/ and the /app/ shell; unsafe requests echo it back. */
export function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

type Options = { method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'; body?: unknown; signal?: AbortSignal }

export async function api<T>(path: string, { method = 'GET', body, signal }: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET') headers['X-CSRFToken'] = csrfToken()
  const response = await fetch(path, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const detail = (data as { detail?: string; message?: string } | null) ?? {}
    throw new ApiError(response.status, detail.detail ?? detail.message ?? `Request failed (${response.status})`, data)
  }
  return data as T
}

/** Multipart upload (FormData). Same CSRF and error handling as api(); the browser sets the boundary. */
export async function upload<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { Accept: 'application/json', 'X-CSRFToken': csrfToken() },
    credentials: 'same-origin',
    body: form,
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const fieldError = data && typeof data === 'object' ? Object.values(data as Record<string, unknown>).flat()[0] : null
    throw new ApiError(response.status, typeof fieldError === 'string' ? fieldError : `Upload failed (${response.status})`, data)
  }
  return data as T
}

export const loginUrl = () => `/app/login?next=${encodeURIComponent(location.pathname + location.search)}`

export type Me = {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  education_level: string
  education_choices: { value: string; label: string }[]
  has_password: boolean
  unread_notifications: number
  due_count: number
  subjects: { id: number; name: string; due_count: number }[]
}

export const useMe = () => useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/api/me/') })

export const displayName = (me: Me) => [me.first_name, me.last_name].filter(Boolean).join(' ') || me.username

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]!.toUpperCase()).join('') || '?'
