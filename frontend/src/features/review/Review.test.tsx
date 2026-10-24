import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp, reply } from '../../test/render'
import { interval } from './ReviewSession'

const grades = [{ grade: 1, label: 'Again' }, { grade: 3, label: 'Hard' }, { grade: 4, label: 'Good' }, { grade: 5, label: 'Easy' }]
const card = (id: number, question: string, answer: string) => ({
  id, question, answer, subject_id: 3, subject_name: 'Database Systems', material_name: 'lecture4.pdf',
  next_days: { 1: 1, 3: 6, 4: 15, 5: 18 },
})
const queue = { due_count: 2, subject: null, grades, cards: [card(1, 'What is a B-tree?', 'A balanced tree index'), card(2, 'What is ACID?', 'Atomicity, consistency…')] }

afterEach(() => vi.unstubAllGlobals())

describe('Review session', () => {
  it('shows a card, reveals the answer, grades with clicks or keys, then celebrates', async () => {
    document.cookie = 'csrftoken=tok'
    const fetchMock = mockApi({ 'GET /api/me/': me, 'GET /api/review/queue/': queue, 'POST /api/review/grade/': { flashcard_id: 1, interval_days: 15 } })
    renderApp('/review')

    expect(await screen.findByRole('heading', { name: 'What is a B-tree?' })).toBeInTheDocument()
    expect(screen.getByText('1 of 2 due')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Primary navigation' })).not.toBeInTheDocument() // focus mode: no sidebar

    await userEvent.click(screen.getByRole('button', { name: 'Show answer' }))
    expect(screen.getByRole('heading', { name: 'A balanced tree index' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Good\s*15 days/ })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Good/ }))

    expect(await screen.findByRole('heading', { name: 'What is ACID?' })).toBeInTheDocument()
    await userEvent.keyboard(' ')
    await userEvent.keyboard('4') // 4th button = Easy
    expect(await screen.findByRole('heading', { name: 'All caught up' })).toBeInTheDocument()
    expect(screen.getByText(/You reviewed 2 cards/)).toBeInTheDocument()

    const grades = fetchMock.mock.calls.filter(([url]) => url === '/api/review/grade/').map(([, init]) => JSON.parse(init!.body as string))
    expect(grades).toEqual([{ flashcard_id: 1, grade: 4 }, { flashcard_id: 2, grade: 5 }])
  })

  it('shows a forgotten card again before the session ends', async () => {
    const fetchMock = mockApi({ 'GET /api/me/': me, 'GET /api/review/queue/': { ...queue, cards: [queue.cards[0]] }, 'POST /api/review/grade/': { flashcard_id: 1, interval_days: 1 } })
    renderApp('/review')
    await userEvent.click(await screen.findByRole('button', { name: 'Show answer' }))
    expect(screen.getByRole('button', { name: /Again\s*This session/ })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Again/ }))
    expect(await screen.findByText('2 of 2 due')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'What is a B-tree?' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Show answer' }))
    await userEvent.click(screen.getByRole('button', { name: /Good/ }))
    expect(await screen.findByText(/You reviewed 1 card\./)).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/review/grade/')).toHaveLength(2) // both grades saved
  })

  it('brings a card back at the end if its grade fails to save', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/review/queue/': { ...queue, cards: [queue.cards[0]] }, 'POST /api/review/grade/': reply(500, { detail: 'boom' }) })
    renderApp('/review')
    await userEvent.click(await screen.findByRole('button', { name: 'Show answer' }))
    await userEvent.click(screen.getByRole('button', { name: /Again/ }))
    expect(await screen.findByText('Couldn’t save that grade')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'What is a B-tree?' })).toBeInTheDocument())
  })

  it('says when nothing is due', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/review/queue/?subject=4': { ...queue, due_count: 0, cards: [] } })
    renderApp('/review?subject=4')
    expect(await screen.findByRole('heading', { name: 'All caught up' })).toBeInTheDocument()
    expect(screen.getByText(/Nothing is due right now/)).toBeInTheDocument()
  })

  it('labels intervals', () => {
    expect(interval(1)).toBe('1 day')
    expect(interval(15)).toBe('15 days')
    expect(interval(31)).toBe('1 month')
    expect(interval(95)).toBe('3 months')
  })
})
