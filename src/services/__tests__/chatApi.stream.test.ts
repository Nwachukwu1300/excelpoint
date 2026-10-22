import { describe, it, expect, vi, afterEach } from 'vitest'
import { chatApi, parseSseBlock, StreamUnavailableError } from '../chatApi'

const done = {
  user_message: { id: 1, content: 'q', role: 'user', timestamp: 't', session: 1 },
  assistant_message: { id: 2, content: 'INSERT is DML.', role: 'assistant', timestamp: 't', session: 1 },
  session: { id: 1 },
}

// Serve the SSE body in arbitrary network-sized pieces, as a real connection would
const streamOf = (pieces: string[]) =>
  new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder()
      pieces.forEach((p) => controller.enqueue(encoder.encode(p)))
      controller.close()
    },
  })

describe('chat streaming client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('parses an SSE block', () => {
    expect(parseSseBlock('event: token\ndata: {"text": "Hi"}')).toEqual({ type: 'token', data: { text: 'Hi' } })
    expect(parseSseBlock(': comment only')).toBeNull()
  })

  it('emits tokens and resolves with the done payload, even when events split across chunks', async () => {
    const body =
      'event: token\ndata: {"text": "INSERT "}\n\n' +
      'event: token\ndata: {"text": "is DML."}\n\n' +
      `event: done\ndata: ${JSON.stringify(done)}\n\n`
    const fetchMock = vi.fn().mockResolvedValue(new Response(streamOf([body.slice(0, 17), body.slice(17, 60), body.slice(60)])))
    vi.stubGlobal('fetch', fetchMock)

    const tokens: string[] = []
    const result = await chatApi.streamMessage(3, { content: 'q' }, (t) => tokens.push(t))

    expect(tokens).toEqual(['INSERT ', 'is DML.'])
    expect(result.assistant_message.content).toBe('INSERT is DML.')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/subjects/3/chat/stream/')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ message: 'q' })
  })

  it('reports an error event as a failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(streamOf(['event: error\ndata: {"message": "XP is unavailable"}\n\n']))))
    await expect(chatApi.streamMessage(3, { content: 'q' }, () => {})).rejects.toThrow('XP is unavailable')
  })

  it('signals "stream unavailable" when the request itself fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('oops', { status: 500 })))
    await expect(chatApi.streamMessage(3, { content: 'q' }, () => {})).rejects.toBeInstanceOf(StreamUnavailableError)
  })
})
