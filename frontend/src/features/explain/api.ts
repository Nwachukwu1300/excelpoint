import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, uploadWithProgress } from '../../lib/api'

export type Passage = { chunk_id: number; material_name: string; chunk_index: number; content: string }
export type Verdict = 'correct' | 'wrong' | 'not_in_notes'
export type Mark = { sentence: string; verdict: Verdict; note: string; quote: string; passage: Passage | null }
export type KeyPoint = { id: string; point: string; covered: boolean; passage: Passage }
export type Turn = {
  id: number; mode: 'voice' | 'text'; kind: 'explanation' | 'question' | 'off_topic'
  student_text: string; reply: string; answer: string; marks: Mark[]; trace_id: string | null; created_at: string
}
export type Limit = { used: number; limit: number; resets_at: string | null }
export type Summary = { nailed: Mark[]; wrong: Mark[]; not_in_notes: Mark[]; missed: KeyPoint[] }
export type Session = {
  id: number; topic: string; subject_id: number; subject_name: string; material_id: number | null; material_name: string | null
  finished: boolean; coverage: number | null; accuracy: number | null; created_at: string
  key_points: KeyPoint[]; turns: Turn[]; voice: 'browser' | 'openai'; max_rounds: number; summary: Summary | null; limit: Limit
}
export type SessionRow = Pick<Session, 'id' | 'topic' | 'subject_id' | 'finished' | 'coverage' | 'accuracy' | 'created_at'> & { rounds: number }
export type Overview = { files_ready: boolean; files: { id: number; name: string }[]; topics: string[]; sessions: SessionRow[]; limit: Limit }
export type NotCovered = { covered: false; topic: string; suggestions: string[] }

export const overviewKey = (subjectId: number) => ['explain', 'subject', subjectId]
export const sessionKey = (id: number) => ['explain', 'session', id]

export const useOverview = (subjectId: number) =>
  useQuery({ queryKey: overviewKey(subjectId), queryFn: () => api<Overview>(`/api/subjects/${subjectId}/explain/`) })

export const useSession = (id: number | undefined) =>
  useQuery({ queryKey: sessionKey(id ?? 0), queryFn: () => api<Session>(`/api/explain/${id}/`), enabled: !!id })

export const startSession = (subjectId: number, body: { topic: string } | { material_id: number } | { section_id: number }) =>
  api<Session | NotCovered>(`/api/subjects/${subjectId}/explain/`, { method: 'POST', body })

export const transcribe = (sessionId: number, clip: Blob, onProgress: (fraction: number) => void) => {
  const form = new FormData()
  const extension = clip.type.includes('mp4') ? 'mp4' : clip.type.includes('ogg') ? 'ogg' : 'webm'
  form.append('audio', clip, `explanation.${extension}`)
  return uploadWithProgress<{ text: string }>(`/api/explain/${sessionId}/transcribe/`, form, onProgress)
}

/** Every change returns the whole session, so the page and the subject's history update from one reply. */
function useSessionChange<A>(sessionId: number, request: (arg: A) => Promise<Session>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: request,
    onSuccess: session => {
      queryClient.setQueryData(sessionKey(sessionId), session)
      queryClient.invalidateQueries({ queryKey: overviewKey(session.subject_id) })
      queryClient.invalidateQueries({ queryKey: ['home'] })
    },
  })
}

export const useSendTurn = (sessionId: number) =>
  useSessionChange(sessionId, (body: { text: string; mode: 'voice' | 'text' }) =>
    api<Session>(`/api/explain/${sessionId}/turns/`, { method: 'POST', body }))

export const useFinish = (sessionId: number) =>
  useSessionChange(sessionId, () => api<Session>(`/api/explain/${sessionId}/finish/`, { method: 'POST' }))

export function useDeleteSession(subjectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api<null>(`/api/explain/${id}/`, { method: 'DELETE' }),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: sessionKey(id) })
      queryClient.invalidateQueries({ queryKey: overviewKey(subjectId) })
    },
  })
}

export const percent = (fraction: number | null) => (fraction === null ? null : Math.round(fraction * 100))

/** "14:32", or "tomorrow at 09:10", for when a check is free again. */
export function resetTime(iso: string | null, now = new Date()) {
  if (!iso) return null
  const at = new Date(iso)
  const time = at.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  return at.toDateString() === now.toDateString() ? time : `tomorrow at ${time}`
}
