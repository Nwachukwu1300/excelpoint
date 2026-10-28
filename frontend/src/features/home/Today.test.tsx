import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { emptyHome, me, mockApi, renderApp } from '../../test/render'
import { subjectInitials } from '../../ui/SubjectIcon'
import { greeting, todayLabel } from './Today'

const home = {
  due: { count: 20, subjects: 2, minutes: 9 },
  suggestions: [
    { kind: 'weak_quiz', title: 'Retake the quiz on lecture4.pdf', reason: 'Your last score was 45%.', url: '/api/quiz/9/take/', subject_id: 3, quiz_id: 9 },
    { kind: 'review', title: 'Review 12 flashcards in Database Systems', reason: 'They’re due now.', url: '/subjects/3/review/', subject_id: 3, quiz_id: null },
  ],
  recent_chats: [{ id: 5, title: 'B-tree indexes explained', subject_id: 3, subject_name: 'Database Systems', last_activity: new Date().toISOString() }],
  subjects: [
    { id: 3, name: 'Database Systems', materials_count: 8, due_count: 12, last_quiz_score: 45 },
    { id: 4, name: 'Maths', materials_count: 0, due_count: 0, last_quiz_score: null },
  ],
}

afterEach(() => vi.unstubAllGlobals())

describe('Today', () => {
  it('shows due cards, ranked suggestions, subjects and recent chats', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/home/': home })
    renderApp('/')

    expect(await screen.findByRole('heading', { name: '20 flashcards to review' }, { timeout: 3000 })).toBeInTheDocument()
    expect(screen.getByText('Across 2 subjects · about 9 minutes')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Start review' })).toHaveAttribute('href', '/review')

    const steps = screen.getAllByRole('article')
    expect(within(steps[0]!).getByRole('link', { name: 'Retake' })).toHaveAttribute('href', '/quizzes/9/start?fresh=1')
    expect(within(steps[0]!).getByRole('link', { name: 'Retake' })).toHaveClass('button--primary') // top pick stands out
    expect(within(steps[1]!).getByRole('link', { name: 'Review' })).toHaveClass('button--secondary')
    expect(within(steps[1]!).getByRole('link', { name: 'Review' })).toHaveAttribute('href', '/review?subject=3')

    const db = screen.getByRole('link', { name: /Database Systems\s*8 files/ })
    expect(within(db).getByText('45%')).toBeInTheDocument()
    expect(within(screen.getByRole('link', { name: /Maths\s*0 files/ })).getByText('—')).toBeInTheDocument()

    expect(screen.getByRole('link', { name: /B-tree indexes explained/ })).toHaveAttribute('href', '/subjects/3/chat/5')
    expect(screen.queryByText('New to ExcelPoint?')).not.toBeInTheDocument()
  })

  it('welcomes a brand-new user instead of showing empty numbers', async () => {
    mockApi({ 'GET /api/me/': { ...me, subjects: [], due_count: 0 }, 'GET /api/home/': emptyHome })
    renderApp('/')
    expect(await screen.findByRole('heading', { name: 'Nothing to review now' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Start review' })).not.toBeInTheDocument()
    expect(screen.getByText('New to ExcelPoint?')).toBeInTheDocument()
    expect(screen.getByText(/No conversations yet/)).toBeInTheDocument()
    expect(screen.getByText(/Nothing to suggest yet/)).toBeInTheDocument()
  })

  it('offers a retry when the page fails to load', async () => {
    let calls = 0
    mockApi({
      'GET /api/me/': me,
      'GET /api/home/': () => (++calls === 1 ? { status: 500, body: { detail: 'boom' } } : { body: home }),
    })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: '20 flashcards to review' }, { timeout: 3000 })).toBeInTheDocument()
  })
})

describe('Today helpers', () => {
  it('formats the greeting, date and subject initials like the design', () => {
    expect(greeting(9)).toBe('Good morning')
    expect(greeting(14)).toBe('Good afternoon')
    expect(greeting(20)).toBe('Good evening')
    expect(todayLabel(new Date(2026, 2, 18))).toBe('WEDNESDAY, 18 MARCH')
    expect(subjectInitials('Computer Networks')).toBe('CN')
    expect(subjectInitials('Database Systems')).toBe('DS') // the mock-up's "DB" was hand-picked
    expect(subjectInitials('Maths')).toBe('MA')
  })
})
