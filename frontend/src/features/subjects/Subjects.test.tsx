import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp, reply } from '../../test/render'
import { checkFile, parseSummary } from './api'
import { dueLabel } from './FlashcardsTab'

const now = new Date().toISOString()
const summary = [
  { id: 3, name: 'Database Systems', materials_count: 2, due_count: 12, last_quiz_score: 45, updated_at: now },
  { id: 4, name: 'Maths', materials_count: 0, due_count: 0, last_quiz_score: null, updated_at: now },
]
const materials = [
  { id: 11, filename: 'transactions.mp4', file_type: 'VIDEO', status: 'PROCESSING', created_at: now, summary: '', quiz_id: null },
  { id: 10, filename: 'lecture4.pdf', file_type: 'PDF', status: 'COMPLETED', created_at: now, summary: 'Indexes cut disk reads.\n- B-trees stay balanced\n- Leaves are **linked**', quiz_id: 9 },
]

afterEach(() => vi.unstubAllGlobals())

describe('Subjects list', () => {
  it('shows each subject with its stats and links into the workspace', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/summary/': summary })
    renderApp('/subjects')
    const card = (await screen.findByRole('heading', { name: 'Database Systems' })).closest('article')!
    expect(within(card).getByText('2 materials · Updated just now')).toBeInTheDocument()
    expect(within(card).getByText('45%')).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: /Open subject/ })).toHaveAttribute('href', '/subjects/3')
  })

  it('blocks duplicate names, then creates a subject and opens it', async () => {
    document.cookie = 'csrftoken=tok'
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/summary/': summary,
      'POST /api/subjects/': reply(201, { id: 7, name: 'Anatomy' }),
      'GET /api/subjects/7/materials/': [],
    })
    renderApp('/subjects?new=1')
    const input = await screen.findByLabelText('Subject name')
    await userEvent.type(input, 'database systems')
    expect(screen.getByText('A subject named database systems already exists.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create subject' })).toBeDisabled()

    await userEvent.clear(input)
    await userEvent.type(input, 'Anatomy{Enter}')
    expect(await screen.findByText('Subject created')).toBeInTheDocument()
    expect(screen.getByText('Anatomy is ready for your first upload.')).toBeInTheDocument()
    const [, init] = fetchMock.mock.calls.find(([url, i]) => url === '/api/subjects/' && i?.method === 'POST')!
    expect(init!.body).toBe('{"name":"Anatomy"}')
  })

  it('invites a new user to create their first subject', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/summary/': [] })
    renderApp('/subjects')
    expect(await screen.findByRole('heading', { name: 'Create your first subject' })).toBeInTheDocument()
  })
})

describe('Subject workspace', () => {
  const base = { 'GET /api/me/': me, 'GET /api/subjects/summary/': summary, 'GET /api/subjects/3/materials/': materials }

  it('lists files with status, expands the AI summary and shows processing', async () => {
    mockApi(base)
    renderApp('/subjects/3')
    expect(await screen.findByRole('heading', { name: 'Database Systems', level: 1 })).toBeInTheDocument()
    expect(await screen.findByText('lecture4.pdf')).toBeInTheDocument()
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Processing transactions.mp4' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /AI summary/ }))
    expect(await screen.findByText('B-trees stay balanced')).toBeInTheDocument()
    expect(screen.getByText('Leaves are linked')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Take the quiz for this file/ })).toHaveAttribute('href', '/quizzes/9/start')
  })

  it('deletes a file after confirming', async () => {
    const fetchMock = mockApi({ ...base, 'DELETE /api/materials/10/': reply(204) })
    renderApp('/subjects/3')
    await userEvent.click(await screen.findByRole('button', { name: 'More actions for lecture4.pdf' }))
    await userEvent.click(screen.getByRole('menuitem', { name: 'Delete file' }))
    const dialog = screen.getByRole('dialog', { name: 'Delete lecture4.pdf?' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete file' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/materials/10/', expect.objectContaining({ method: 'DELETE' })))
    expect(await screen.findByText('File deleted')).toBeInTheDocument()
  })

  it('rejects unsupported files and uploads a valid one with the CSRF token', async () => {
    document.cookie = 'csrftoken=tok'
    const fetchMock = mockApi({ ...base, 'POST /api/subjects/3/upload_material/': reply(201, materials[1]) })
    renderApp('/subjects/3?upload=1')
    const dialog = await screen.findByRole('dialog', { name: 'Add study material' })
    const input = dialog.querySelector('input[type=file]') as HTMLInputElement

    await userEvent.upload(input, new File(['x'], 'notes.txt', { type: 'text/plain' }), { applyAccept: false })
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Unsupported file type')

    await userEvent.upload(input, new File(['%PDF'], 'week8.pdf', { type: 'application/pdf' }))
    expect(within(dialog).getByText('week8.pdf')).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Upload material' }))
    expect(await screen.findByText('week8.pdf uploaded')).toBeInTheDocument()
    const [, init] = fetchMock.mock.calls.find(([url]) => url === '/api/subjects/3/upload_material/')!
    expect((init!.headers as Record<string, string>)['X-CSRFToken']).toBe('tok')
    expect((init!.body as FormData).get('file')).toBeInstanceOf(File)
  })

  it('shows quizzes with this user’s scores and flashcards with due dates', async () => {
    mockApi({
      ...base,
      'GET /api/subjects/3/quizzes/': [{ id: 9, title: 'Q', question_count: 10, material_name: 'lecture4.pdf', attempts: 3, last_score: 45, best_score: 72 }],
      'GET /api/subjects/3/flashcards/': [
        { id: 1, question: 'B-tree index', answer: 'A balanced tree', material_name: 'lecture4.pdf', due_at: null },
        { id: 2, question: 'ACID', answer: 'Atomicity…', material_name: 'notes.pdf', due_at: new Date(Date.now() + 3 * 86_400_000).toISOString() },
      ],
    })
    renderApp('/subjects/3?tab=quizzes')
    const row = (await screen.findByRole('heading', { name: 'lecture4.pdf' })).closest('article')!
    expect(within(row).getByText('3 attempts')).toBeInTheDocument()
    expect(within(row).getByRole('link', { name: /New questions/ })).toHaveAttribute('href', '/quizzes/9/start?fresh=1')

    await userEvent.click(screen.getByRole('tab', { name: /Flashcards/ }))
    expect(await screen.findByText('B-tree index')).toBeInTheDocument()
    expect(screen.getByText('Due today')).toBeInTheDocument()
    expect(screen.getByText('In 3 days')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Filter by material'), 'notes.pdf')
    expect(screen.queryByText('B-tree index')).not.toBeInTheDocument()
  })

  it('says so when the subject does not exist', async () => {
    mockApi({ ...base, 'GET /api/subjects/99/materials/': reply(404, { detail: 'Not found.' }) })
    renderApp('/subjects/99')
    expect(await screen.findByRole('heading', { name: 'Subject not found' })).toBeInTheDocument()
  })
})

describe('subject helpers', () => {
  it('splits summaries into an intro and bullet points', () => {
    expect(parseSummary('Intro line\n\n- one\n* two\n1. three\n• **four**')).toEqual({ intro: ['Intro line'], points: ['one', 'two', 'three', 'four'] })
  })

  it('checks type and size before uploading', () => {
    expect(checkFile(new File(['x'], 'a.PDF'))).toBeNull()
    expect(checkFile(new File(['x'], 'a.exe'))).toMatch(/Unsupported/)
    const big = new File(['x'], 'big.mp4')
    Object.defineProperty(big, 'size', { value: 101 * 1024 * 1024 })
    expect(checkFile(big)).toMatch(/over 100 MB/)
  })

  it('labels due dates', () => {
    const at = Date.parse('2026-10-24T12:00:00Z')
    expect(dueLabel({ id: 1, question: '', answer: '', material_name: null, due_at: null }, at).label).toBe('Due today')
    expect(dueLabel({ id: 1, question: '', answer: '', material_name: null, due_at: '2026-10-25T09:00:00Z' }, at).label).toBe('Tomorrow')
    expect(dueLabel({ id: 1, question: '', answer: '', material_name: null, due_at: '2026-10-20T09:00:00Z' }, at).due).toBe(true)
  })
})
