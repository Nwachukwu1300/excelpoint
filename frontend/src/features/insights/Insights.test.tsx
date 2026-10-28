import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp } from '../../test/render'
import { dailySeries, type InsightsData, type Trace } from './api'

const metrics = { sessions: 4, no_context: 1, unverified: 1, faithfulness: 0.87, hallucination_rate: 0.064, retrieval_top_similarity: 0.84, judge_relevance: null, judge_faithfulness: null }
const insights: InsightsData = {
  summary: {
    days: 30, totals: metrics,
    trends: [{ ...metrics, day: new Date().toISOString().slice(0, 10) }],
    retrieval: { avg_chunks: 4.2, avg_retrieval_ms: 184, avg_total_ms: 1048, no_context_rate: 0.25, avg_top_similarity: 0.84 },
    failures: [{ session_id: 'abc', query: 'What is horizontal sharding?', reasons: ['nothing retrieved'], created_at: new Date().toISOString() }],
  },
  recent: [{ session_id: 'def', question: 'How do B-trees work?', subject_name: 'Database Systems', category: 'Standalone', chunks: 2, confidence: 0.92, unverified: false, no_context: false, latency_ms: 842, created_at: new Date().toISOString() }],
}
const trace: Trace = {
  session_id: 'def', created_at: '2026-10-24T10:42:00Z', question: 'How do B-trees work?', rewritten_query: null, follow_up: false, category: 'retrieval_required', pipeline: 'default',
  subject: { id: 3, name: 'Database Systems' }, chat: { subject_id: 3, session_id: 19 }, total_ms: 1284,
  stages: [{ name: 'embedding', ms: 122, pct: 9.5 }, { name: 'generation', ms: 638, pct: 49.7 }],
  chunks: [{ material_name: 'subject_materials/lecture4.pdf', chunk_index: 17, similarity: 0.94, rerank: 0.91, text: 'A B-tree is a self-balancing search tree…' }],
  retry_chunks: [], prompts: { generation: [{ role: 'system', content: 'You are XP' }, { role: 'user', content: 'Question: How do B-trees work?' }] },
  generated_answer: 'First draft', final_answer: 'A **B-tree** stays balanced.', retry_count: 0, retries: [],
  verification: { grounded: true, reasoning: 'All claims match.', supported_claims: ['Keys stay sorted'], unsupported_claims: [] },
  unverified: false, confidence: { score: 0.92, interpretation: 'HIGH_CONFIDENCE', breakdown: { faithfulness: 0.4, top_similarity: 0.09 } },
  evaluations: [{ evaluator: 'heuristic', faithfulness: 0.94, hallucination_rate: 0, retrieval_mean_similarity: 0.8, retrieval_top_similarity: 0.94, answer_relevance: null, reasoning: '' }],
}

afterEach(() => vi.unstubAllGlobals())

describe('Insights', () => {
  it('shows quality metrics, what needs attention and recent answers', async () => {
    const fetchMock = mockApi({ 'GET /api/me/': me, 'GET /api/reasoning/insights/?days=30': insights, 'GET /api/reasoning/insights/?days=7': { ...insights, summary: { ...insights.summary, days: 7 } } })
    renderApp('/insights')
    expect(await screen.findByText('0.87')).toBeInTheDocument()
    expect(screen.getByText('6.4%')).toBeInTheDocument() // unsupported claims
    expect(screen.getByText('25%')).toBeInTheDocument() // 1 of 4 found nothing
    expect(screen.getByRole('link', { name: /What is horizontal sharding\?.*See how this answer was made/ })).toHaveAttribute('href', '/insights/abc')
    const row = screen.getByRole('cell', { name: /How do B-trees work\?/ }).closest('tr')!
    expect(within(row).getByText('High · 0.92')).toBeInTheDocument()
    expect(within(row).getByText('842 ms')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '7 days' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/reasoning/insights/?days=7', expect.anything()))
    expect(screen.getByRole('button', { name: '7 days' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('explains what will appear before any questions are asked', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/reasoning/insights/?days=30': { ...insights, summary: { ...insights.summary, totals: { ...metrics, sessions: 0 } } } })
    renderApp('/insights')
    expect(await screen.findByRole('heading', { name: 'No insights yet' })).toBeInTheDocument()
  })

  it('shows the full trace of one answer', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/reasoning/sessions/def/trace/': trace })
    renderApp('/insights/def')
    expect(await screen.findByRole('heading', { name: 'How do B-trees work?', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open conversation' })).toHaveAttribute('href', '/subjects/3/chat/19')
    expect(screen.getByText('lecture4.pdf')).toBeInTheDocument()
    expect(screen.getByText('Chunk 18')).toBeInTheDocument()
    expect(screen.getByText('638 ms')).toBeInTheDocument()
    expect(screen.getByText('1 of 1 statement backed by your files')).toBeInTheDocument()
    expect(screen.getByText('Every statement is backed by your files.')).toBeInTheDocument()
    expect(screen.getByText('Passed on the first attempt')).toBeInTheDocument()
    expect(screen.getByText('B-tree', { selector: 'strong' })).toBeInTheDocument()
    expect(screen.getByText('View first attempt')).toBeInTheDocument()
    expect(screen.getByText('You are XP')).toBeInTheDocument() // first prompt open by default
    await userEvent.click(screen.getByRole('button', { name: /user prompt with context/ }))
    expect(await screen.findByText('Question: How do B-trees work?')).toBeInTheDocument()
    expect(screen.getByText('Not enabled')).toBeInTheDocument() // no LLM judge row
  })

  it('fills every day of the range for the chart', () => {
    const series = dailySeries([{ ...metrics, day: '2026-10-24' }], 7, new Date(2026, 9, 26))
    expect(series).toHaveLength(7)
    expect(series.filter(s => s.day)).toHaveLength(1)
    expect(series[4]!.day?.sessions).toBe(4)
  })
})
