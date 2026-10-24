import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export type QuizInfo = { id: number; title: string; material_name: string | null; subject_id: number; subject_name: string; time_limit: number | null; pass_score: number }
export type Question = { id: string; text: string; type: 'multiple_choice' | 'true_false' | 'short_answer'; points: number; choices: { id: string; text: string }[] }
export type AttemptStatus = 'generating' | 'ready' | 'failed' | 'completed' | 'abandoned'
export type Attempt = { id: number; status: AttemptStatus; fresh: boolean; started_at: string; quiz: QuizInfo; questions: Question[]; fell_back?: boolean }
export type ReviewRow = { id: string; text: string; type: Question['type']; points: number; your_answer: string; correct_answer: string; is_correct: boolean; explanation: string }
export type Results = {
  id: number; quiz: QuizInfo; fresh: boolean; score: number; passed: boolean; earned_points: number; total_points: number
  correct_count: number; question_count: number; finished_at: string; questions: ReviewRow[]
}
export type History = {
  attempts: { id: number; quiz_id: number; quiz_title: string; subject_id: number; subject_name: string; score: number; passed: boolean; fresh: boolean; finished_at: string }[]
  subjects: { id: number; name: string; average: number; attempts: number }[]
}

export const startAttempt = (quizId: number, fresh: boolean) =>
  api<Attempt>(`/api/quiz/${quizId}/attempts/`, { method: 'POST', body: { fresh } })

/** Polls every 2s while XP writes fresh questions. */
export const useAttempt = (attemptId: number) =>
  useQuery({
    queryKey: ['quiz-attempt', attemptId],
    queryFn: () => api<Attempt>(`/api/quiz/attempts/${attemptId}/`),
    refetchInterval: q => (q.state.data?.status === 'generating' ? 2000 : false),
    refetchOnWindowFocus: false,
  })

export const submitAttempt = (attemptId: number, answers: Record<string, string>) =>
  api<Results>(`/api/quiz/attempts/${attemptId}/submit/`, { method: 'POST', body: { answers } })

export const useResults = (attemptId: number) =>
  useQuery({ queryKey: ['quiz-results', attemptId], queryFn: () => api<Results>(`/api/quiz/attempts/${attemptId}/results/`), staleTime: Infinity })

export const useHistory = (subjectId: string | null) =>
  useQuery({ queryKey: ['quiz-history', subjectId], queryFn: () => api<History>(`/api/quiz/attempts/${subjectId ? `?subject=${subjectId}` : ''}`) })

/** Answers in progress survive "Save & exit" and reloads (this browser only). */
const draftKey = (attemptId: number) => `xp-quiz-${attemptId}`
export function loadDraft(attemptId: number): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(draftKey(attemptId)) ?? '{}') } catch { return {} }
}
export function saveDraft(attemptId: number, answers: Record<string, string> | null) {
  try {
    if (answers) localStorage.setItem(draftKey(attemptId), JSON.stringify(answers))
    else localStorage.removeItem(draftKey(attemptId))
  } catch { /* private mode: the draft just isn't kept */ }
}

export const typeLabel: Record<Question['type'], string> = { multiple_choice: 'Multiple choice', true_false: 'True or false', short_answer: 'Short answer' }
