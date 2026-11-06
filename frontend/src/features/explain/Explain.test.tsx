import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp, reply } from '../../test/render'
import type { Session, Turn } from './api'

const TREE = 'B-trees stay balanced. Every leaf sits at the same depth, so a lookup reads about log n pages.'
const passage = { chunk_id: 1, material_name: 'indexes.pdf', chunk_index: 0, content: TREE }

const overview = {
  files_ready: true,
  files: [{ id: 11, name: 'indexes.pdf' }],
  topics: ['B-tree index', 'Hash index'],
  sessions: [],
  limit: { used: 0, limit: 30, resets_at: null },
}

const session = (changes: Partial<Session> = {}): Session => ({
  id: 7, topic: 'B-tree index', subject_id: 3, subject_name: 'Database Systems', material_id: null, material_name: null,
  finished: false, coverage: null, accuracy: null, created_at: new Date().toISOString(),
  key_points: [], turns: [], voice: 'browser', max_rounds: 4, summary: null, limit: { used: 0, limit: 30, resets_at: null },
  ...changes,
})

const turn: Turn = {
  id: 21, mode: 'text', kind: 'explanation', student_text: 'B-trees stay balanced. Leaves can be at any depth. They date from 1970.',
  reply: 'You got the balance right. Leaves all sit at the same depth, though. How many pages does a lookup read?',
  answer: '', trace_id: null, created_at: new Date().toISOString(),
  marks: [
    { sentence: 'B-trees stay balanced.', verdict: 'correct', note: '', quote: 'B-trees stay balanced', passage },
    { sentence: 'Leaves can be at any depth.', verdict: 'wrong', note: 'Every leaf sits at the same depth.', quote: '', passage },
    { sentence: 'They date from 1970.', verdict: 'not_in_notes', note: '', quote: '', passage: null },
  ],
}
const keyPoints = [
  { id: 'K1', point: 'B-trees stay balanced', covered: true, passage },
  { id: 'K2', point: 'A lookup reads about log n pages', covered: false, passage },
]

afterEach(() => vi.unstubAllGlobals())

describe('Explain it back', () => {
  it('starts from a suggested topic, and offers close topics when one isn’t in the files', async () => {
    const user = userEvent.setup()
    const api = mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/3/explain/': overview,
      'POST /api/subjects/3/explain/': (init: RequestInit | undefined) => {
        const body = JSON.parse(String(init?.body))
        return body.topic === 'Photosynthesis'
          ? { body: { covered: false, topic: 'Photosynthesis', suggestions: ['Hash index'] } }
          : { status: 201, body: session({ topic: body.topic }) }
      },
      'GET /api/explain/7/': session({ topic: 'Hash index' }),
    })
    renderApp('/subjects/3/explain')

    expect(await screen.findByRole('heading', { name: 'Explain it back' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /indexes\.pdf/ })).toBeInTheDocument()
    await user.type(screen.getByLabelText('Type your own topic'), 'Photosynthesis')
    await user.click(screen.getByRole('button', { name: 'Start' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('“Photosynthesis” isn’t in your files')

    await user.click(within(alert).getByRole('button', { name: 'Hash index' }))
    expect(await screen.findByRole('heading', { name: 'Hash index' })).toBeInTheDocument()
    expect(screen.getByText('Round 1 of 4 · Explain it back')).toBeInTheDocument()
    expect(JSON.parse(String(api.mock.calls.at(-2)?.[1]?.body))).toEqual({ topic: 'Hash index' })
  })

  it('asks for notes first when no file is ready', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/subjects/3/explain/': { ...overview, files_ready: false, files: [], topics: [] } })
    renderApp('/subjects/3/explain')
    expect(await screen.findByRole('heading', { name: 'Upload notes first' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Upload a file' })).toHaveAttribute('href', '/subjects/3?upload=1')
  })

  it('checks a typed explanation and marks each statement with its source', async () => {
    const user = userEvent.setup()
    const api = mockApi({
      'GET /api/me/': me,
      'GET /api/explain/7/': session(),
      'POST /api/explain/7/turns/': session({ turns: [turn], key_points: keyPoints, limit: { used: 1, limit: 30, resets_at: null } }),
      'GET /api/subjects/3/explain/': overview,
    })
    renderApp('/subjects/3/explain/7')

    await user.click(await screen.findByRole('button', { name: 'Type instead' }))
    await user.type(screen.getByRole('textbox'), turn.student_text)
    await user.click(screen.getByRole('button', { name: 'Check my explanation' }))

    expect(await screen.findByText(turn.reply)).toBeInTheDocument()
    expect(JSON.parse(String(api.mock.calls.find(c => String(c[0]).endsWith('/turns/'))?.[1]?.body))).toEqual({ text: turn.student_text, mode: 'text' })
    const marks = screen.getByRole('region', { name: 'Checked against your notes' })
    expect(within(marks).getByText('1 correct · 1 not quite · 1 not in your notes')).toBeInTheDocument()
    expect(within(marks).getByText('Your notes say:').parentElement).toHaveTextContent('Every leaf sits at the same depth.')
    expect(within(marks).getAllByText('indexes.pdf')).toHaveLength(2) // evidence for correct and wrong, none for not in notes
    expect(within(marks).getByText(/couldn’t check it/)).toBeInTheDocument()
    expect(screen.getByText('1 key point you haven’t mentioned yet')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Play reply' })).not.toBeInTheDocument() // typed: no audio
    expect(screen.getByText('Round 2 of 4 · Explain it back')).toBeInTheDocument()
  })

  it('says kindly when the daily limit is reached and when they can go again', async () => {
    const user = userEvent.setup()
    const resets = new Date(Date.now() + 60 * 60 * 1000)
    mockApi({
      'GET /api/me/': me,
      'GET /api/explain/7/': session(),
      'POST /api/explain/7/turns/': reply(429, { detail: 'You’ve used today’s 30 checks.', resets_at: resets.toISOString() }),
    })
    renderApp('/subjects/3/explain/7')
    await user.click(await screen.findByRole('button', { name: 'Type instead' }))
    await user.type(screen.getByRole('textbox'), 'B-trees stay balanced.')
    await user.click(screen.getByRole('button', { name: 'Check my explanation' }))
    const banner = await screen.findByText(/You’ve used today’s 30 checks/)
    expect(banner.closest('[role="alert"]')).toHaveTextContent(/You can explain again at \d\d:\d\d/)
    expect(screen.queryByRole('button', { name: 'Check my explanation' })).not.toBeInTheDocument()
  })

  it('ends with a summary of what was nailed, wrong and missed', async () => {
    mockApi({
      'GET /api/me/': me,
      'GET /api/explain/7/': session({
        finished: true, coverage: 0.5, accuracy: 0.5, turns: [turn], key_points: keyPoints,
        summary: { nailed: [turn.marks[0]!], wrong: [turn.marks[1]!], not_in_notes: [turn.marks[2]!], missed: [keyPoints[1]!] },
      }),
    })
    renderApp('/subjects/3/explain/7')
    expect(await screen.findByRole('heading', { name: 'Good progress' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'covered 50%' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'accurate 50%' })).toBeInTheDocument()
    expect(screen.getByText('You covered 1 of 2 key points. 1 of 2 statements XP could check were right.')).toBeInTheDocument()
    for (const name of ['What you nailed', 'What to fix', 'What you missed', 'Not in your notes']) {
      expect(screen.getByRole('heading', { name })).toBeInTheDocument()
    }
    expect(screen.getByText('A lookup reads about log n pages')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start recording' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to subject' })).toHaveAttribute('href', '/subjects/3?tab=explain')
  })

  it('offers typing and explains how to turn the mic on when it is blocked', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('MediaRecorder', class { static isTypeSupported = () => true })
    vi.stubGlobal('navigator', { ...navigator, mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(new DOMException('no', 'NotAllowedError')) } })
    mockApi({ 'GET /api/me/': me, 'GET /api/explain/7/': session() })
    renderApp('/subjects/3/explain/7')
    await user.click(await screen.findByRole('button', { name: 'Start recording' }))
    expect(await screen.findByText('XP can’t use your microphone')).toBeInTheDocument()
    expect(screen.getByText(/set Microphone to Allow/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Type instead' }))
    expect(screen.getByRole('button', { name: 'Check my explanation' })).toBeInTheDocument()
  })

  it('records, shows what XP heard, can redo it, then speaks the reply', async () => {
    const user = userEvent.setup()
    let now = 1_000_000
    vi.spyOn(Date, 'now').mockImplementation(() => now)
    class FakeRecorder {
      static isTypeSupported = () => true
      state = 'inactive'
      mimeType = 'audio/webm'
      ondataavailable: ((e: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      start() { this.state = 'recording' }
      stop() { this.state = 'inactive'; this.ondataavailable?.({ data: new Blob(['sound']) }); this.onstop?.() }
    }
    const stopTrack = vi.fn()
    vi.stubGlobal('MediaRecorder', FakeRecorder)
    vi.stubGlobal('navigator', { ...navigator, mediaDevices: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) } })
    const sent: string[] = []
    vi.stubGlobal('XMLHttpRequest', class {
      upload: { onprogress: ((e: object) => void) | null } = { onprogress: null }
      status = 0
      responseText = ''
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      open(_: string, url: string) { sent.push(url) }
      setRequestHeader() {}
      send() {
        setTimeout(() => {
          this.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 2 })
          this.status = 200
          this.responseText = JSON.stringify({ text: 'B-trees stay balanced.' })
          this.onload?.()
        })
      }
    })
    const speak = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel: vi.fn() })
    vi.stubGlobal('SpeechSynthesisUtterance', class { lang = ''; constructor(public text: string) {} })
    const api = mockApi({
      'GET /api/me/': me,
      'GET /api/explain/7/': session(),
      'POST /api/explain/7/turns/': session({ turns: [{ ...turn, mode: 'voice' }], key_points: keyPoints }),
      'GET /api/subjects/3/explain/': overview,
    })
    renderApp('/subjects/3/explain/7')

    const record = async () => {
      await user.click(await screen.findByRole('button', { name: 'Start recording' }))
      now += 40_000
      await user.click(await screen.findByRole('button', { name: 'Stop recording' }))
    }
    await record()
    const heard = await screen.findByLabelText('What XP heard')
    expect(heard).toHaveValue('B-trees stay balanced.')
    expect(sent).toEqual(['/api/explain/7/transcribe/'])
    expect(stopTrack).toHaveBeenCalled() // the mic is released once they stop

    await user.click(screen.getByRole('button', { name: 'Record again' }))
    await record()
    await user.clear(await screen.findByLabelText('What XP heard'))
    await user.type(screen.getByLabelText('What XP heard'), 'B-trees stay balanced always.')
    await user.click(screen.getByRole('button', { name: 'Check my explanation' }))

    expect(await screen.findByText(turn.reply)).toBeInTheDocument()
    expect(JSON.parse(String(api.mock.calls.find(c => String(c[0]).endsWith('/turns/'))?.[1]?.body)))
      .toEqual({ text: 'B-trees stay balanced always.', mode: 'voice' })
    expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: turn.reply }))
    expect(screen.getByRole('button', { name: 'Play reply' })).toBeInTheDocument()
  })

  it('rejects a take that is too short without sending it', async () => {
    const user = userEvent.setup()
    vi.spyOn(Date, 'now').mockReturnValue(5_000)
    vi.stubGlobal('MediaRecorder', class {
      static isTypeSupported = () => true
      state = 'inactive'
      mimeType = ''
      onstop: (() => void) | null = null
      ondataavailable = null
      start() { this.state = 'recording' }
      stop() { this.state = 'inactive'; this.onstop?.() }
    })
    vi.stubGlobal('navigator', { ...navigator, mediaDevices: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [] }) } })
    mockApi({ 'GET /api/me/': me, 'GET /api/explain/7/': session() })
    renderApp('/subjects/3/explain/7')
    await user.click(await screen.findByRole('button', { name: 'Start recording' }))
    await user.click(await screen.findByRole('button', { name: 'Stop recording' }))
    expect(await screen.findByText('That was too short')).toBeInTheDocument()
  })

  it('lists past sessions in the subject with how coverage changed', async () => {
    const day = (n: number) => new Date(Date.now() - n * 86_400_000).toISOString()
    const row = (id: number, coverage: number | null, created_at: string, finished = true) =>
      ({ id, topic: 'B-tree index', subject_id: 3, finished, coverage, accuracy: 0.8, created_at, rounds: 2 })
    mockApi({
      'GET /api/me/': me,
      'GET /api/subjects/summary/': [{ id: 3, name: 'Database Systems', materials_count: 1, due_count: 0, last_quiz_score: null, updated_at: day(0) }],
      'GET /api/subjects/3/materials/': [{ id: 11, filename: 'indexes.pdf', file_type: 'PDF', status: 'COMPLETED', created_at: day(3), summary: '', quiz_id: null }],
      'GET /api/subjects/3/explain/': { ...overview, sessions: [row(9, null, day(0), false), row(8, 0.75, day(1)), row(5, 0.4, day(2))] },
    })
    renderApp('/subjects/3?tab=explain')
    const latest = await screen.findByRole('link', { name: /B-tree index.*75% covered/ })
    expect(latest).toHaveAttribute('href', '/subjects/3/explain/8')
    expect(within(latest).getByText('Up from 40%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Not finished · 2 rounds/ })).toHaveAttribute('href', '/subjects/3/explain/9')
    expect(screen.getByRole('link', { name: 'Explain it back' })).toHaveAttribute('href', '/subjects/3/explain')
  })
})
