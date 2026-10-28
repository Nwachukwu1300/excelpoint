import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { api, upload } from '../../lib/api'
import type { MaterialStatus } from '../../ui/primitives'

export type SubjectSummary = {
  id: number; name: string; materials_count: number; due_count: number; last_quiz_score: number | null; updated_at: string
}
export type Material = {
  id: number; filename: string; file_type: string; status: MaterialStatus; error?: string; created_at: string; summary: string; quiz_id: number | null
}
export type Flashcard = { id: number; question: string; answer: string; material_name: string | null; due_at: string | null }
export type QuizSummary = {
  id: number; title: string; question_count: number; material_name: string | null
  attempts: number; last_score: number | null; best_score: number | null
}

export const useSubjects = () =>
  useQuery({ queryKey: ['subjects'], queryFn: () => api<SubjectSummary[]>('/api/subjects/summary/') })

const busy = (m: Material) => m.status === 'PENDING' || m.status === 'PROCESSING'

/** Re-checks every 4s while something is processing; when a file finishes, its study tools appear elsewhere too. */
export function useMaterials(subjectId: number) {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['materials', subjectId],
    queryFn: () => api<Material[]>(`/api/subjects/${subjectId}/materials/`),
    refetchInterval: q => (q.state.data?.some(busy) ? 4000 : false),
  })
  const statuses = query.data?.map(m => `${m.id}:${m.status}`).join()
  const previous = useRef(statuses)
  useEffect(() => {
    if (previous.current && statuses && previous.current !== statuses) {
      for (const key of [['flashcards', subjectId], ['quizzes', subjectId], ['subjects'], ['me'], ['home']]) {
        queryClient.invalidateQueries({ queryKey: key })
      }
    }
    previous.current = statuses
  }, [statuses, subjectId, queryClient])
  return query
}

export const useFlashcards = (subjectId: number) =>
  useQuery({ queryKey: ['flashcards', subjectId], queryFn: () => api<Flashcard[]>(`/api/subjects/${subjectId}/flashcards/`) })

export const useQuizzes = (subjectId: number) =>
  useQuery({ queryKey: ['quizzes', subjectId], queryFn: () => api<QuizSummary[]>(`/api/subjects/${subjectId}/quizzes/`) })

function useRefreshAfter() {
  const queryClient = useQueryClient()
  return (...keys: unknown[][]) => keys.forEach(queryKey => queryClient.invalidateQueries({ queryKey }))
}

export function useCreateSubject() {
  const refresh = useRefreshAfter()
  return useMutation({
    mutationFn: (name: string) => api<{ id: number; name: string }>('/api/subjects/', { method: 'POST', body: { name } }),
    onSuccess: () => refresh(['subjects'], ['me'], ['home']),
  })
}

export function useDeleteSubject() {
  const refresh = useRefreshAfter()
  return useMutation({
    mutationFn: (id: number) => api(`/api/subjects/${id}/`, { method: 'DELETE' }),
    onSuccess: () => refresh(['subjects'], ['me'], ['home'], ['notifications']),
  })
}

export function useUploadMaterial() {
  const refresh = useRefreshAfter()
  return useMutation({
    mutationFn: ({ subjectId, file }: { subjectId: number; file: File }) => {
      const form = new FormData()
      form.append('file', file)
      return upload<Material>(`/api/subjects/${subjectId}/upload_material/`, form)
    },
    onSuccess: (_, { subjectId }) => refresh(['materials', subjectId], ['subjects'], ['home']),
  })
}

export function useDeleteMaterial(subjectId: number) {
  const refresh = useRefreshAfter()
  return useMutation({
    mutationFn: (id: number) => api(`/api/materials/${id}/`, { method: 'DELETE' }),
    onSuccess: () => refresh(['materials', subjectId], ['flashcards', subjectId], ['quizzes', subjectId], ['subjects'], ['me'], ['home']),
  })
}

/** Accepted uploads, mirroring the backend's UPLOAD_FILE_TYPES and its 100 MB limit. */
export const ACCEPTED = ['pdf', 'docx'] // the server can read these; audio and video need transcription, which isn't installed
export const MAX_BYTES = 100 * 1024 * 1024

export function checkFile(file: File): string | null {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (ext === 'doc') return 'Old .doc files can’t be read. Save it as .docx or PDF, then upload that.'
  if (!ACCEPTED.includes(ext)) return 'This file type isn’t supported. Upload a PDF or Word (.docx) file.'
  if (file.size > MAX_BYTES) return 'That file is over 100 MB. Try a smaller or compressed version.'
  return null
}

/** Summaries come back as markdown-ish bullets; split them into an intro and a list. */
export function parseSummary(text: string): { intro: string[]; points: string[] } {
  const intro: string[] = []
  const points: string[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/)
    if (bullet) points.push(bullet[1]!.replace(/\*\*(.+?)\*\*/g, '$1'))
    else intro.push(line.replace(/\*\*(.+?)\*\*/g, '$1'))
  }
  return { intro, points }
}
