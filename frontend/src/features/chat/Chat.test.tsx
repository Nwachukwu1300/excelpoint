import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp, reply } from '../../test/render'
import { inline, parseBlocks } from '../../ui/Markdown'
import { describeAnswer, parseSseBlock, RateLimitError, type ChatMessage } from './api'

const at = '2026-10-24T10:42:00Z'
const answer = (over: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 2, role: 'assistant', timestamp: at, trace_url: '/insights/abc/',
  content: 'A **B-tree** keeps keys sorted.\n- Nodes narrow the search\n- Leaves are linked',
  metadata: {
    context_used: true,
    retrieved_chunks: [{ content: 'A B-tree is a self-balancing search tree…', chunk_index: 17, material_name: 'lecture4.pdf', similarity_score: 0.94 }],
    model_info: { pipeline: 'reasoning', verified: true, confidence: 0.91 },
  },
  ...over,
})
const sessions = { sessions: [{ id: 5, title: 'B-tree indexes explained', last_activity: at, message_count: 2, is_active: true }] }
const history = { messages: [{ id: 1, role: 'user', content: 'How does a B-tree work?', timestamp: at }, answer()] }

/** An SSE response whose blocks the test releases one at a time. */
function controlledStream() {
  let push!: (block: string) => void
  let end!: () => void
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      push = block => c.enqueue(new TextEncoder().encode(block))
      end = () => c.close()
    },
  })
  return { response: new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }), push: (b: string) => push(b), end: () => end() }
}
const sse = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`

afterEach(() => vi.unstubAllGlobals())

describe('XP chat', () => {
  it('shows a past conversation with citations, verification and its sources', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/3/chat/sessions/?limit=30': sessions, 'GET /api/subjects/3/chat/messages/?session_id=5': history })
    renderApp('/subjects/3/chat/5')
    expect(await screen.findByText('How does a B-tree work?')).toBeInTheDocument()
    expect(screen.getByText('B-tree', { selector: 'strong' })).toBeInTheDocument()
    expect(screen.getByText('Leaves are linked')).toBeInTheDocument()
    expect(screen.getByText('Verified')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'How was this answered?' })).toHaveAttribute('href', '/insights/abc')
    expect(screen.getByRole('link', { name: /B-tree indexes explained/ })).toHaveAttribute('aria-current', 'page')

    await userEvent.click(screen.getByRole('button', { name: /Show sources/ }))
    await userEvent.click(screen.getByRole('button', { name: /lecture4.pdf · part 18/ }))
    const panel = screen.getByRole('complementary', { name: 'Sources' })
    expect(within(panel).getByText('1 excerpt used')).toBeInTheDocument()
    expect(within(panel).getByText('94%')).toBeInTheDocument()
    expect(within(panel).getByText('High · 0.91')).toBeInTheDocument()
    expect(panel.querySelector('.source-excerpt')).toHaveClass('is-focused')
  })

  it('starts a new chat, streams the answer token by token, then shows the saved answer', async () => {
    document.cookie = 'csrftoken=tok'
    const stream = controlledStream()
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/3/chat/sessions/?limit=30': { sessions: [] },
      'POST /api/subjects/3/chat/session/': reply(201, { id: 9, title: null, last_activity: at, message_count: 0, is_active: true }),
    })
    const base = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (input, init) => (String(input) === '/api/subjects/3/chat/stream/' ? stream.response : base(input, init)))
    renderApp('/subjects/3/chat')

    expect(await screen.findByRole('heading', { name: /Ask anything about your Database Systems materials/ })).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Ask XP'), 'How does a B-tree work?{Enter}')
    expect(await screen.findByText('XP is thinking…')).toBeInTheDocument()

    await act(async () => stream.push(sse('token', { text: 'A B-tree ' })))
    expect(await screen.findByText(/^A B-tree/)).toBeInTheDocument()
    expect(screen.queryByText('XP is thinking…')).not.toBeInTheDocument()
    await act(async () => stream.push(sse('token', { text: 'keeps keys sorted' })))
    expect(await screen.findByText(/A B-tree keeps keys sorted/)).toBeInTheDocument()
    expect(document.querySelector('.caret')).toBeInTheDocument()

    await act(async () => {
      stream.push(sse('done', {
        user_message: { id: 11, role: 'user', content: 'How does a B-tree work?', timestamp: at },
        assistant_message: answer({ id: 12, content: 'A verified final answer.' }),
        session: { id: 9, title: 'B-trees', last_activity: at, message_count: 2, is_active: true },
      }))
      stream.end()
    })
    expect(await screen.findByText('A verified final answer.')).toBeInTheDocument()
    expect(document.querySelector('.caret')).not.toBeInTheDocument()
    expect(screen.getAllByText('How does a B-tree work?')).toHaveLength(1)

    const [, init] = fetchMock.mock.calls.find(([url]) => url === '/api/subjects/3/chat/stream/')!
    expect(JSON.parse(init!.body as string)).toEqual({ message: 'How does a B-tree work?', session_id: 9 })
    expect((init!.headers as Record<string, string>)['X-CSRFToken']).toBe('tok')
  })

  it('falls back to a normal request when the stream cannot start', async () => {
    mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/3/chat/sessions/?limit=30': sessions,
      'GET /api/subjects/3/chat/messages/?session_id=5': { messages: [] },
      'POST /api/subjects/3/chat/stream/': reply(502, { detail: 'Bad gateway' }),
      'POST /api/subjects/3/chat/messages/': reply(201, {
        user_message: { id: 21, role: 'user', content: 'Explain ACID', timestamp: at },
        assistant_message: answer({ id: 22, content: 'ACID means atomicity…' }),
        session: sessions.sessions[0],
      }),
    })
    renderApp('/subjects/3/chat/5')
    await userEvent.type(await screen.findByLabelText('Ask XP'), 'Explain ACID{Enter}')
    expect(await screen.findByText('ACID means atomicity…')).toBeInTheDocument()
  })

  it('shows the hourly limit and keeps the question', async () => {
    mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/3/chat/sessions/?limit=30': sessions,
      'GET /api/subjects/3/chat/messages/?session_id=5': { messages: [] },
      'POST /api/subjects/3/chat/stream/': reply(429, { detail: 'Request was throttled. Expected available in 600 seconds.' }),
    })
    renderApp('/subjects/3/chat/5')
    await userEvent.type(await screen.findByLabelText('Ask XP'), 'One more question{Enter}')
    expect(await screen.findByText(/reached your limit/)).toBeInTheDocument()
    expect(screen.getByText(/Try again in about 10 minutes/)).toBeInTheDocument()
    expect(screen.getByLabelText('Ask XP')).toHaveValue('One more question')
  })

  it('turns a no-match reply into a "Not in your materials" card', async () => {
    const fallback = answer({ id: 3, content: "I couldn't find information about graph databases in your materials.", metadata: { context_used: false, retrieved_chunks: [], model_info: { pipeline: 'fallback' } } })
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/3/chat/sessions/?limit=30': sessions, 'GET /api/subjects/3/chat/messages/?session_id=5': { messages: [fallback] } })
    renderApp('/subjects/3/chat/5')
    expect(await screen.findByText('Not in your materials')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Upload materials/ })).toHaveAttribute('href', '/subjects/3?upload=1')
  })
})

describe('chat helpers', () => {
  it('parses SSE blocks', () => {
    expect(parseSseBlock('event: token\ndata: {"text":"hi"}')).toEqual({ type: 'token', data: { text: 'hi' } })
    expect(parseSseBlock(': keep-alive')).toBeNull()
  })

  it('reads the wait time from a throttle message', () => {
    expect(new RateLimitError('Request was throttled. Expected available in 90 seconds.').retryInSeconds).toBe(90)
    expect(new RateLimitError('Slow down').retryInSeconds).toBeNull()
  })

  it('moves the unverified note out of the answer text', () => {
    const a = describeAnswer(answer({ content: 'Answer.\n\n_Note: parts of this answer could not be fully verified against your materials._', metadata: { model_info: { pipeline: 'reasoning', verified: false } } }))
    expect(a.body).toBe('Answer.')
    expect(a.verified).toBe(false)
    expect(describeAnswer(answer({ metadata: { context_used: false, retrieved_chunks: [], model_info: { pipeline: 'single_call' } } })).notFound).toBe(false)
  })

  it('renders markdown safely, including a half-streamed code block', () => {
    expect(parseBlocks('Intro\n\n- a\n- b\n\n1. one\n\n```\nSELECT 1;')).toEqual([
      { type: 'p', text: 'Intro' }, { type: 'ul', items: ['a', 'b'] }, { type: 'ol', items: ['one'] }, { type: 'code', text: 'SELECT 1;' },
    ])
    const parts = inline('a **b** `c` *d* <img src=x onerror=alert(1)>')
    expect(parts.filter(p => typeof p === 'string').join('')).toContain('<img src=x onerror=alert(1)>') // stays text, never HTML
  })
})

describe('XP chat before any file is ready', () => {
  const material = (status: string) => ({ id: 1, filename: 'notes.docx', file_type: 'DOCX', status, error: '', created_at: at, summary: '', quiz_id: null })

  it('asks for a file first instead of offering questions', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/3/chat/sessions/?limit=30': { sessions: [] }, 'GET /api/subjects/3/materials/': [material('FAILED')] })
    renderApp('/subjects/3/chat')
    expect(await screen.findByRole('heading', { name: 'Upload a file first' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Upload a file/ })).toHaveAttribute('href', '/subjects/3?upload=1')
    expect(screen.queryByRole('button', { name: 'Summarise the key ideas' })).not.toBeInTheDocument()
  })

  it('says a file is still being read while it processes', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/3/chat/sessions/?limit=30': { sessions: [] }, 'GET /api/subjects/3/materials/': [material('PROCESSING')] })
    renderApp('/subjects/3/chat')
    expect(await screen.findByRole('heading', { name: 'Your file is still being read' })).toBeInTheDocument()
  })

  it('a suggested question is sent straight away', async () => {
    document.cookie = 'csrftoken=tok'
    const fetchMock = mockApi({
      'GET /api/me/': me, 'GET /api/subjects/3/chat/sessions/?limit=30': { sessions: [] }, 'GET /api/subjects/3/materials/': [material('COMPLETED')],
      'POST /api/subjects/3/chat/session/': reply(201, { id: 9, title: null, last_activity: at, message_count: 0, is_active: true }),
    })
    const base = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (input, init) => (String(input) === '/api/subjects/3/chat/stream/' ? new Promise<Response>(() => {}) : base(input, init)))
    renderApp('/subjects/3/chat')
    await userEvent.click(await screen.findByRole('button', { name: 'Summarise the key ideas' }))
    expect(await screen.findByText('XP is thinking…')).toBeInTheDocument()
    const streamCall = fetchMock.mock.calls.find(([url]) => String(url) === '/api/subjects/3/chat/stream/')
    expect(JSON.parse(String(streamCall?.[1]?.body))).toMatchObject({ message: 'Summarise the key ideas', session_id: 9 })
  })

  it('a reply with no ready files points to the files, not to uploading more', () => {
    const a = describeAnswer({ id: 3, role: 'assistant', timestamp: at, content: 'None of your files are ready yet.', metadata: { context_used: false, retrieved_chunks: [], model_info: { pipeline: 'fallback', files_ready: false } } })
    expect(a.notFound && a.noFilesReady).toBe(true)
  })
})

describe('Deleting a conversation', () => {
  it('confirms, deletes and leaves the deleted conversation', async () => {
    let deleted = false
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/3/chat/sessions/?limit=30': () => ({ body: deleted ? { sessions: [] } : sessions }),
      'GET /api/subjects/3/chat/messages/?session_id=5': history,
      'DELETE /api/chat/sessions/5/': () => { deleted = true; return { body: { session_id: 5 } } },
    })
    renderApp('/subjects/3/chat/5')
    await userEvent.click(await screen.findByRole('button', { name: 'Delete conversation: B-tree indexes explained' }))
    const dialog = screen.getByRole('dialog', { name: 'Delete this conversation?' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete conversation' }))
    expect(await screen.findByText('Conversation deleted')).toBeInTheDocument()
    expect(await screen.findByText('Your conversations will be listed here.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/chat/sessions/5/', expect.objectContaining({ method: 'DELETE' }))
  })
})

describe('Chat edge cases', () => {
  it('shows "Subject not found" for a subject that isn’t yours', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/99/chat/sessions/?limit=30': reply(404, { detail: 'Not found.' }), 'GET /api/subjects/99/materials/': reply(404, { detail: 'Not found.' }) })
    renderApp('/subjects/99/chat')
    expect(await screen.findByRole('heading', { name: 'Subject not found' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Ask XP')).not.toBeInTheDocument()
  })

  it('lists a new conversation as soon as its first answer arrives', async () => {
    document.cookie = 'csrftoken=tok'
    const stream = controlledStream()
    const saved = { id: 9, title: 'B-tree basics', last_activity: at, message_count: 2, is_active: true }
    let listed = 0
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/3/chat/sessions/?limit=30': () => ({ body: { sessions: listed++ ? [saved] : [] } }),
      'POST /api/subjects/3/chat/session/': reply(201, { id: 9, title: null, last_activity: at, message_count: 0, is_active: true }),
      'GET /api/subjects/3/chat/messages/?session_id=9': { messages: [] },
    })
    const base = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (input, init) => (String(input) === '/api/subjects/3/chat/stream/' ? stream.response : base(input, init)))
    renderApp('/subjects/3/chat')
    await userEvent.type(await screen.findByLabelText('Ask XP'), 'What is a B-tree?{Enter}')
    await act(async () => {
      stream.push(sse('done', {
        user_message: { id: 11, role: 'user', content: 'What is a B-tree?', timestamp: at },
        assistant_message: answer({ id: 12 }),
        session: saved,
      }))
      stream.end()
    })
    expect(await screen.findByRole('link', { name: /B-tree basics/ })).toHaveAttribute('aria-current', 'page')
  })
})
