import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp, reply } from '../../test/render'
import type { Attempt, Results } from './api'

const quiz = { id: 9, title: 'Lecture 4', material_name: 'lecture4.pdf', subject_id: 3, subject_name: 'Database Systems', time_limit: null, pass_score: 60 }
const questions: Attempt['questions'] = [
  { id: 'dynamic_1', text: 'Which tree stays balanced?', type: 'multiple_choice', points: 1, choices: [{ id: 'c1', text: 'B-tree' }, { id: 'c2', text: 'Heap' }] },
  { id: 'dynamic_2', text: 'Name the index for ranges', type: 'short_answer', points: 1, choices: [] },
]
const attempt = (over: Partial<Attempt> = {}): Attempt => ({ id: 41, status: 'ready', fresh: true, started_at: new Date().toISOString(), quiz, questions, ...over })
const results: Results = {
  id: 41, quiz, fresh: true, score: 50, passed: false, earned_points: 1, total_points: 2, correct_count: 1, question_count: 2,
  finished_at: new Date().toISOString(),
  questions: [
    { id: 'dynamic_1', text: 'Which tree stays balanced?', type: 'multiple_choice', points: 1, your_answer: 'B-tree', correct_answer: 'B-tree', is_correct: true, explanation: 'B-trees rebalance.' },
    { id: 'dynamic_2', text: 'Name the index for ranges', type: 'short_answer', points: 1, your_answer: 'heap', correct_answer: 'B-tree', is_correct: false, explanation: '' },
  ],
}

afterEach(() => vi.unstubAllGlobals())

describe('Quizzes', () => {
  it('writes fresh questions, lets you answer them, and shows the results', async () => {
    let polls = 0
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'POST /api/quiz/9/attempts/': reply(201, attempt({ status: 'generating', questions: [] })),
      'GET /api/quiz/attempts/41/': () => ({ body: ++polls < 2 ? attempt({ status: 'generating', questions: [] }) : attempt() }),
      'POST /api/quiz/attempts/41/submit/': results,
    })
    renderApp('/quizzes/9/start?fresh=1')

    expect(await screen.findByRole('heading', { name: 'Writing fresh questions' })).toBeInTheDocument()
    expect(screen.getByText(/Reading lecture4.pdf/)).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Which tree stays balanced?' }, { timeout: 4000 })).toBeInTheDocument()
    expect(JSON.parse(fetchMock.mock.calls.find(([u]) => u === '/api/quiz/9/attempts/')![1]!.body as string)).toEqual({ fresh: true })

    await userEvent.click(screen.getByRole('radio', { name: /B-tree/ }))
    expect(screen.getByRole('radio', { name: /B-tree/ })).toHaveAttribute('aria-checked', 'true')
    await userEvent.click(screen.getByRole('button', { name: /Next/ }))
    await userEvent.type(screen.getByLabelText('Name the index for ranges'), 'heap')
    await userEvent.click(screen.getByRole('button', { name: /Submit quiz/ }))

    expect(await screen.findByRole('heading', { name: /Keep going, Alex/ })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'score 50%' })).toBeInTheDocument()
    const wrong = screen.getByRole('heading', { name: 'Name the index for ranges' }).closest('article')!
    expect(within(wrong).getByText('Correct answer')).toBeInTheDocument()
    expect(screen.getByText('B-trees rebalance.')).toBeInTheDocument()
    expect(JSON.parse(fetchMock.mock.calls.find(([u]) => u === '/api/quiz/attempts/41/submit/')![1]!.body as string))
      .toEqual({ answers: { dynamic_1: 'c1', dynamic_2: 'heap' } })
    expect(localStorage.getItem('xp-quiz-41')).toBeNull() // draft cleared once submitted
  })

  it('keeps answers through "Save & exit" and a reload', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/quiz/attempts/41/': attempt() })
    const first = renderApp('/quiz-attempts/41')
    await userEvent.click(await screen.findByRole('radio', { name: /Heap/ }))
    first.unmount()
    renderApp('/quiz-attempts/41')
    expect(await screen.findByRole('radio', { name: /Heap/ })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByRole('link', { name: 'Save and exit' })).toHaveAttribute('href', '/subjects/3?tab=quizzes')
  })

  it('offers the standard quiz when XP could not write new questions', async () => {
    mockApi({
      'GET /api/me/': me,
      'GET /api/quiz/attempts/41/': attempt({ status: 'failed', questions: [] }),
      'POST /api/quiz/9/attempts/': reply(201, attempt({ id: 42, fresh: false })),
      'GET /api/quiz/attempts/42/': attempt({ id: 42, fresh: false }),
    })
    renderApp('/quiz-attempts/41')
    expect(await screen.findByRole('heading', { name: 'XP couldn’t write new questions' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Take the standard quiz' }))
    expect(await screen.findByRole('heading', { name: 'Which tree stays balanced?' })).toBeInTheDocument()
  })

  it('lists past attempts with averages per subject', async () => {
    mockApi({
      'GET /api/me/': me,
      'GET /api/quiz/attempts/': {
        attempts: [{ id: 41, quiz_id: 9, quiz_title: 'lecture4.pdf', subject_id: 3, subject_name: 'Database Systems', score: 72, passed: true, fresh: true, finished_at: new Date().toISOString() }],
        subjects: [{ id: 3, name: 'Database Systems', average: 72, attempts: 1 }],
      },
    })
    renderApp('/quizzes/history')
    expect(await screen.findByText('Performance by subject')).toBeInTheDocument()
    const row = screen.getByRole('cell', { name: /lecture4.pdf/ }).closest('tr')!
    expect(within(row).getByText('72%')).toBeInTheDocument()
    expect(within(row).getByRole('link', { name: 'View details' })).toHaveAttribute('href', '/quiz-attempts/41/results')
  })
})
