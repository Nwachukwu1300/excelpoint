import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageList } from '../MessageList'
import type { ChatMessage } from '@/types/chat'

const base = { timestamp: '2026-10-17T10:00:00Z', session: 1 }

describe('MessageList trace link', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn() // not implemented in jsdom
  })

  it('links assistant answers to their debug trace', () => {
    const messages: ChatMessage[] = [
      { ...base, id: 1, role: 'user', content: 'What is DDL?', trace_url: '/insights/should-not-show/' },
      { ...base, id: 2, role: 'assistant', content: 'Data Definition Language.', trace_url: '/insights/abc/' },
      { ...base, id: 3, role: 'assistant', content: 'Hi there!', trace_url: null },
    ]
    render(<MessageList messages={messages} />)

    const links = screen.getAllByRole('link', { name: /how was this answered/i })
    expect(links).toHaveLength(1)
    expect(links[0]).toHaveAttribute('href', '/insights/abc/')
  })
})
