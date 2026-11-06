import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp } from '../../test/render'
import type { Coverage, SectionDetail } from './api'

const now = new Date().toISOString()
const summary = [{ id: 3, name: 'Database Systems', materials_count: 2, due_count: 0, last_quiz_score: null, updated_at: now, studied_percent: 40 }]
const materials = [{ id: 10, filename: 'indexes.pdf', file_type: 'PDF', status: 'COMPLETED', created_at: now, summary: '', quiz_id: 9 }]
const row = (id: number, title: string, status: string, extra = {}) =>
  ({ id, title, label: title, range: null, status, reason: '', size: 4, last_studied: null, cards: 0, questions: 0, ...extra })
const coverage: Coverage = {
  subject: { id: 3, name: 'Database Systems' }, state: 'ready', percent: 40, sentence: 'Hash indexes hasn’t come up yet.',
  counts: { not_studied: 1, shaky: 1, solid: 1, fading: 1 },
  files: [
    { id: 10, name: 'indexes.pdf', state: 'ready', error: '', percent: 75, studied: 3, sections: [
      row(41, 'B-trees', 'solid') as never, row(42, 'Range queries', 'shaky', { range: 'Pages 3–4' }) as never,
      row(43, 'Clustered indexes', 'fading') as never, row(44, 'Hash indexes', 'not_studied') as never,
    ] },
    { id: 11, name: 'lecture5.mp4', state: 'processing', error: '', percent: null, studied: 0, sections: [] },
    { id: 12, name: 'scan.pdf', state: 'failed', error: 'No text found in this file.', percent: null, studied: 0, sections: [] },
  ],
}
const section: SectionDetail = {
  id: 42, title: 'Range queries', label: 'Range queries', range: 'Pages 3–4', status: 'shaky', last_studied: now,
  reason: 'You missed 2 of 3 quiz questions on this and you rated one card Hard.', subject_id: 3, file: { id: 10, name: 'indexes.pdf' }, cards: 2,
  text: 'Leaf nodes are linked in key order, so range queries walk the leaves.',
  passages: [{ chunk_id: 5, chunk_index: 2, material_name: 'indexes.pdf', content: 'Leaf nodes are linked in key order, so range queries walk the leaves.' }],
}
const base = { 'GET /api/me/': me, 'GET /api/subjects/summary/': summary, 'GET /api/subjects/3/materials/': materials, 'GET /api/subjects/3/coverage/': coverage }

afterEach(() => vi.unstubAllGlobals())

describe('Coverage map', () => {
  it('shows the number, the sentence, every status with a label, and file states', async () => {
    mockApi(base)
    renderApp('/subjects/3?tab=coverage')
    expect(await screen.findByRole('heading', { name: 'You’ve studied 40% of Database Systems.' })).toBeInTheDocument()
    expect(screen.getByText('Hash indexes hasn’t come up yet.')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'studied 40%' })).toBeInTheDocument()
    const legend = screen.getByRole('list', { name: 'Sections by status' })
    expect(within(legend).getAllByRole('listitem').map(li => li.textContent)).toEqual(['Solid 1', 'Fading 1', 'Shaky 1', 'Not studied 1'])
    const file = screen.getByRole('button', { name: /indexes\.pdf\s*3 of 4 sections studied/ })
    expect(file).toHaveAttribute('aria-expanded', 'true') // a small subject opens every file
    for (const [name, label] of [['B-trees', 'Solid'], ['Range queries', 'Shaky'], ['Clustered indexes', 'Fading'], ['Hash indexes', 'Not studied']]) {
      expect(within(screen.getByRole('button', { name: new RegExp(name) })).getByText(label)).toBeInTheDocument() // never colour alone
    }
    expect(screen.getByText(/Reading this file/)).toBeInTheDocument()
    expect(screen.getByText(/Couldn’t read this file. No text found/)).toBeInTheDocument()
    await userEvent.click(file)
    expect(screen.queryByRole('button', { name: /B-trees/ })).not.toBeInTheDocument()
  })

  it('opens a section with why it is shaky, its text, and three ways to study it', async () => {
    const user = userEvent.setup()
    const api = mockApi({
      ...base,
      'GET /api/sections/42/': section,
      'POST /api/sections/42/quiz/': () => ({ status: 201, body: { id: 77 } }),
      'GET /api/quiz/attempts/77/': { id: 77, status: 'generating', fresh: true, started_at: now, questions: [],
        quiz: { id: 9, title: 'Quiz', section: 'Range queries', material_name: 'indexes.pdf', subject_id: 3, subject_name: 'Database Systems', time_limit: null, pass_score: 60 } },
    })
    renderApp('/subjects/3?tab=coverage')
    await user.click(await screen.findByRole('button', { name: /Range queries/ }))
    const sheet = await screen.findByRole('dialog')
    expect(within(sheet).getByRole('heading', { name: 'Range queries' })).toBeInTheDocument()
    expect(within(sheet).getByText('Pages 3–4 · indexes.pdf')).toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Why is this shaky?' }))
    expect(within(sheet).getByText(section.reason)).toBeInTheDocument()
    expect(within(sheet).getByText(/Leaf nodes are linked/)).toBeInTheDocument()
    expect(within(sheet).getByRole('link', { name: 'Study 2 flashcards' })).toHaveAttribute('href', '/review?section=42')
    expect(within(sheet).getByRole('button', { name: 'Explain it to XP' })).toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Quiz this section' }))
    expect(await screen.findByText(/Reading indexes.pdf/)).toBeInTheDocument() // the quiz page, writing 5 fresh questions
    expect(api.mock.calls.some(c => String(c[0]) === '/api/sections/42/quiz/')).toBe(true)
  })

  it('starts Explain it back on a section, even one without flashcards', async () => {
    const user = userEvent.setup()
    const api = mockApi({
      ...base,
      'GET /api/sections/44/': { ...section, id: 44, title: 'Hash indexes', status: 'not_studied', cards: 0 },
      'POST /api/subjects/3/explain/': () => ({ status: 201, body: { id: 8 } }),
      'GET /api/explain/8/': { id: 8, topic: 'Hash indexes', subject_id: 3, subject_name: 'Database Systems', material_id: 10, material_name: 'indexes.pdf',
        finished: false, coverage: null, accuracy: null, created_at: now, key_points: [], turns: [], voice: 'browser', max_rounds: 4, summary: null,
        limit: { used: 0, limit: 30, resets_at: null } },
    })
    renderApp('/subjects/3?tab=coverage&section=44') // deep link, as Today's suggestions use
    const sheet = await screen.findByRole('dialog')
    expect(await within(sheet).findByRole('heading', { name: 'Hash indexes' })).toBeInTheDocument()
    expect(within(sheet).queryByRole('link', { name: /flashcard/ })).not.toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Explain it to XP' }))
    expect(await screen.findByRole('heading', { name: 'Hash indexes', level: 1 })).toBeInTheDocument()
    expect(JSON.parse(String(api.mock.calls.find(c => String(c[0]) === '/api/subjects/3/explain/')?.[1]?.body))).toEqual({ section_id: 44 })
  })

  it('asks for notes first in a subject with no files', async () => {
    mockApi({ ...base, 'GET /api/subjects/3/coverage/': { ...coverage, state: 'empty', percent: 0, sentence: '', files: [] } })
    renderApp('/subjects/3?tab=coverage')
    expect(await screen.findByRole('heading', { name: 'Upload notes first' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload file' })).toBeInTheDocument()
  })

  it('shows the headline above the Files tab with a way into the map', async () => {
    const user = userEvent.setup()
    mockApi(base)
    renderApp('/subjects/3')
    expect(await screen.findByText('You’ve studied 40% of Database Systems.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /See the map/ }))
    expect(await screen.findByRole('list', { name: 'Sections by status' })).toBeInTheDocument()
  })

  it('shows how much of each subject is studied on the subjects page', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/summary/': [...summary, { ...summary[0], id: 4, name: 'Maths', studied_percent: null }] })
    renderApp('/subjects')
    const db = (await screen.findByRole('heading', { name: 'Database Systems' })).closest('article')!
    expect(within(db).getByText('40%').nextElementSibling).toHaveTextContent('studied')
    const maths = screen.getByRole('heading', { name: 'Maths' }).closest('article')!
    expect(within(maths).getAllByText('—')).toHaveLength(2) // no quiz yet, no map yet
  })
})
