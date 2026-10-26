import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

type Metrics = {
  sessions: number; no_context: number; unverified: number; faithfulness: number | null; hallucination_rate: number | null
  retrieval_top_similarity: number | null; judge_relevance: number | null; judge_faithfulness: number | null
}
export type InsightsData = {
  summary: {
    days: number
    totals: Metrics
    trends: (Metrics & { day: string })[]
    retrieval: { avg_chunks: number | null; avg_retrieval_ms: number | null; avg_total_ms: number | null; no_context_rate: number | null; avg_top_similarity: number | null }
    failures: { session_id: string; query: string; reasons: string[]; created_at: string }[]
  }
  recent: { session_id: string; question: string; subject_name: string; category: string; chunks: number; confidence: number | null; unverified: boolean; no_context: boolean; latency_ms: number | null; created_at: string }[]
}
type Chunk = { material_name: string; chunk_index: number; similarity: number; rerank: number | null; text: string }
export type Trace = {
  session_id: string; created_at: string; question: string; rewritten_query: string | null; follow_up: boolean; category: string; pipeline: string
  subject: { id: number; name: string } | null; chat: { subject_id: number; session_id: number } | null
  total_ms: number; stages: { name: string; ms: number; pct: number }[]
  chunks: Chunk[]; retry_chunks: Chunk[]
  prompts: Record<string, { role: string; content: string }[]>
  generated_answer: string; final_answer: string; retry_count: number
  retries: { attempt_number: number; rewritten_query: string; generated_answer: string; success: boolean; rewrite_strategy?: string }[]
  verification: { grounded: boolean | null; reasoning: string; supported_claims: string[]; unsupported_claims: string[] }
  unverified: boolean
  confidence: { score: number | null; interpretation: string | null; breakdown: Record<string, number> }
  evaluations: { evaluator: string; faithfulness: number | null; hallucination_rate: number | null; retrieval_mean_similarity: number | null; retrieval_top_similarity: number | null; answer_relevance: number | null; reasoning: string }[]
}

export const useInsights = (days: number) =>
  useQuery({ queryKey: ['insights', days], queryFn: () => api<InsightsData>(`/api/reasoning/insights/?days=${days}`), placeholderData: prev => prev })

export const useTrace = (sessionId: string) =>
  useQuery({ queryKey: ['trace', sessionId], queryFn: () => api<Trace>(`/api/reasoning/sessions/${sessionId}/trace/`), staleTime: Infinity })

export const ms = (n: number | null | undefined) => (n == null ? '—' : `${Math.round(n).toLocaleString('en-GB')} ms`)
export const num = (n: number | null | undefined, digits = 2) => (n == null ? '—' : n.toFixed(digits))
export const pct = (n: number | null | undefined) => (n == null ? '—' : `${(n * 100).toFixed(n * 100 < 10 && n > 0 ? 1 : 0)}%`)

/** Every day in the range (oldest first), with that day's numbers or nothing. */
export function dailySeries(trends: InsightsData['summary']['trends'], days: number, today = new Date()) {
  const byDay = new Map(trends.map(t => [t.day, t]))
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(today)
    d.setDate(d.getDate() - (days - 1 - i))
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return { date: d, day: byDay.get(key) }
  })
}
