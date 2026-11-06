import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { IconName } from '../../ui/Icon'
import type { Tone } from '../../ui/primitives'

export type Status = 'not_studied' | 'shaky' | 'solid' | 'fading'
export type SectionRow = {
  id: number; title: string; label: string; range: string | null; status: Status; reason: string
  size: number; last_studied: string | null; cards: number; questions: number
}
export type FileCoverage = {
  id: number; name: string; state: 'processing' | 'building' | 'failed' | 'ready'; error: string
  percent: number | null; studied: number; sections: SectionRow[]
}
export type Coverage = {
  subject: { id: number; name: string }; state: 'empty' | 'ready'; percent: number; sentence: string
  counts: Record<Status, number>; files: FileCoverage[]
}
export type SectionDetail = {
  id: number; title: string; label: string; range: string | null; status: Status; reason: string; last_studied: string | null
  subject_id: number; file: { id: number; name: string }; cards: number; text: string
  passages: { chunk_id: number; chunk_index: number; material_name: string; content: string }[]
}

/** Each status is told apart by its label and icon as well as its colour. */
export const LOOK: Record<Status, { label: string; tone: Tone; icon: IconName | null }> = {
  not_studied: { label: 'Not studied', tone: 'neutral', icon: null },
  shaky: { label: 'Shaky', tone: 'warning', icon: 'alert' },
  solid: { label: 'Solid', tone: 'success', icon: 'check' },
  fading: { label: 'Fading', tone: 'neutral', icon: 'clock' },
}
export const ORDER: Status[] = ['solid', 'fading', 'shaky', 'not_studied']

const busy = (c: Coverage | undefined) => c?.files.some(f => f.state === 'processing' || f.state === 'building')

/** Re-checks every 5s while a file is still being read or its map is being built. */
export const useCoverage = (subjectId: number) =>
  useQuery({
    queryKey: ['coverage', subjectId],
    queryFn: () => api<Coverage>(`/api/subjects/${subjectId}/coverage/`),
    refetchInterval: q => (busy(q.state.data) ? 5000 : false),
  })

export const useSection = (id: number | null) =>
  useQuery({ queryKey: ['section', id], queryFn: () => api<SectionDetail>(`/api/sections/${id}/`), enabled: !!id })

export const startSectionQuiz = (id: number) => api<{ id: number }>(`/api/sections/${id}/quiz/`, { method: 'POST' })
