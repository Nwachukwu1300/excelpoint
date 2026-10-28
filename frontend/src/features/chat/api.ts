import { useQuery } from '@tanstack/react-query'
import { api, ApiError, csrfToken } from '../../lib/api'

export type SourceChunk = { chunk_id?: number; content: string; chunk_index?: number; material_id?: number; material_name: string; similarity_score: number }
export type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  trace_url?: string | null
  metadata?: {
    retrieved_chunks?: SourceChunk[]
    context_used?: boolean
    model_info?: { pipeline?: string; verified?: boolean; confidence?: number | null; files_ready?: boolean }
  }
}
export type ChatSession = { id: number; title: string | null; last_activity: string; message_count: number; is_active: boolean }
export type Exchange = { user_message: ChatMessage; assistant_message: ChatMessage; session: ChatSession }

export const sessionsKey = (subjectId: number) => ['chat-sessions', subjectId]
export const messagesKey = (subjectId: number, sessionId: number) => ['chat-messages', subjectId, sessionId]

export const useSessions = (subjectId: number) =>
  useQuery({
    queryKey: sessionsKey(subjectId),
    queryFn: () => api<{ sessions: ChatSession[] }>(`/api/subjects/${subjectId}/chat/sessions/?limit=30`),
    select: d => d.sessions.filter(s => s.message_count > 0),
  })

export const useMessages = (subjectId: number, sessionId: number | undefined) =>
  useQuery({
    queryKey: messagesKey(subjectId, sessionId ?? 0),
    queryFn: () => api<{ messages: ChatMessage[] }>(`/api/subjects/${subjectId}/chat/messages/?session_id=${sessionId}`),
    select: d => d.messages,
    enabled: !!sessionId,
    // Loaded once; after that the page adds each exchange itself, so a refetch can't double a question mid-stream.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  })

export const createSession = (subjectId: number) =>
  api<ChatSession>(`/api/subjects/${subjectId}/chat/session/`, { method: 'POST', body: {} })

/** The stream couldn't start (network, server error, no body): safe to retry without streaming. */
export class StreamUnavailableError extends Error {}

/** The per-user LLM limit (LLM_RATE_LIMIT, default 60/hour). */
export class RateLimitError extends Error {
  retryInSeconds: number | null
  constructor(detail: string) {
    super(detail)
    const seconds = detail.match(/available in (\d+) second/)
    this.retryInSeconds = seconds ? Number(seconds[1]) : null
  }
}

/** One Server-Sent Events block ("event: x\ndata: {...}") as its type and JSON data. */
export function parseSseBlock(block: string): { type: string; data: unknown } | null {
  let type = 'message'
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) type = line.slice(6).trim()
    else if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  return data ? { type, data: JSON.parse(data) } : null
}

async function failure(response: Response): Promise<Error> {
  const body = await response.json().catch(() => null) as { detail?: string; message?: string } | null
  const detail = body?.detail ?? body?.message ?? `Request failed (${response.status})`
  if (response.status === 429) return new RateLimitError(detail)
  if (response.status >= 500) return new StreamUnavailableError(detail)
  return new ApiError(response.status, detail, body)
}

/** Ask XP and get the answer as it's written; resolves with the saved exchange (authoritative text). */
export async function streamMessage(
  subjectId: number,
  body: { message: string; session_id: number },
  onToken: (text: string) => void,
  signal?: AbortSignal,
): Promise<Exchange> {
  let response: Response
  try {
    response = await fetch(`/api/subjects/${subjectId}/chat/stream/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new StreamUnavailableError(String(error))
  }
  if (!response.ok) throw await failure(response)
  if (!response.body) throw new StreamUnavailableError('No stream body')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let boundary
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const event = parseSseBlock(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + 2)
      if (!event) continue
      if (event.type === 'token') onToken((event.data as { text: string }).text)
      else if (event.type === 'done') return event.data as Exchange
      else if (event.type === 'error') throw new Error((event.data as { message: string }).message)
    }
  }
  throw new Error('The answer stream ended unexpectedly')
}

/** Same question without streaming (used when the stream can't start). */
export async function sendMessage(subjectId: number, body: { message: string; session_id: number }): Promise<Exchange> {
  const response = await fetch(`/api/subjects/${subjectId}/chat/messages/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-CSRFToken': csrfToken() },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const error = await failure(response)
    throw error instanceof StreamUnavailableError ? new Error('XP is currently unavailable. Please try again later.') : error
  }
  return response.json()
}

const UNVERIFIED_NOTE = /\n*_Note: parts of this answer could not be fully verified against your materials\._\s*$/

/** What the thread needs to know about an answer. */
export function describeAnswer(m: ChatMessage) {
  const info = m.metadata?.model_info ?? {}
  const chunks = m.metadata?.retrieved_chunks ?? []
  return {
    notFound: info.pipeline === 'fallback' || (m.metadata?.context_used === false && chunks.length === 0 && info.pipeline !== 'single_call'),
    noFilesReady: info.files_ready === false,
    verified: info.verified,
    confidence: info.confidence ?? null,
    chunks,
    // The backend appends a sentence when verification failed; the app shows a notice box instead.
    body: m.content.replace(UNVERIFIED_NOTE, ''),
  }
}
