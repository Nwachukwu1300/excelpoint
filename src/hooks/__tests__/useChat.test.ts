import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React, { ReactNode } from 'react'
import { useChatMessages, useChatStats, useChatWidget } from '../useChat'
import { mockChatApi, mockChatSession, mockMessages, mockStats } from '../../test/mocks/chatApi'

// Mock the chatApi module
vi.mock('../../services/chatApi', async () => ({
  chatApi: (await import('../../test/mocks/chatApi')).mockChatApi,
  StreamUnavailableError: (await vi.importActual<typeof import('../../services/chatApi')>('../../services/chatApi')).StreamUnavailableError,
}))

// Create a wrapper for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        cacheTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => {
    return React.createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('useChat hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('useChatMessages', () => {
    const subjectId = 1

    it('loads session and messages on mount', async () => {
      const wrapper = createWrapper()
      
      const { result } = renderHook(() => useChatMessages(subjectId), { wrapper })

      // Initially loading
      expect(result.current.isLoading).toBe(true)
      expect(result.current.messages).toEqual([])
      expect(result.current.session).toBeNull()

      // Wait for session to load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Should have loaded session and messages
      expect(mockChatApi.getOrCreateSession).toHaveBeenCalledWith(subjectId)
      expect(mockChatApi.getMessages).toHaveBeenCalledWith(subjectId, mockChatSession.id)
      expect(result.current.session).toEqual(mockChatSession)
      expect(result.current.messages).toEqual(mockMessages)
    })

    it('handles session creation error', async () => {
      const wrapper = createWrapper()
      const error = new Error('Failed to create session')
      // The hook retries session creation twice (1s apart), so the failure must persist
      mockChatApi.getOrCreateSession.mockRejectedValue(error)
      try {
        const { result } = renderHook(() => useChatMessages(subjectId), { wrapper })

        await waitFor(() => {
          expect(result.current.isLoading).toBe(false)
        }, { timeout: 4000 })

        expect(mockChatApi.getOrCreateSession).toHaveBeenCalledTimes(3)

        expect(result.current.session).toBeNull()
        expect(result.current.messages).toEqual([])
      } finally {
        mockChatApi.getOrCreateSession.mockResolvedValue(mockChatSession)
      }
    }, 8000)

    it('sends message with optimistic update', async () => {
      const wrapper = createWrapper()
      const { result } = renderHook(() => useChatMessages(subjectId), { wrapper })

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const messageContent = 'Test message'

      // Hold the request open so the in-flight state is observable
      let finishSend: (value: unknown) => void = () => {}
      mockChatApi.sendMessage.mockImplementationOnce(() => new Promise(resolve => { finishSend = resolve }))

      act(() => {
        result.current.sendMessage(messageContent)
      })

      await waitFor(() => {
        expect(result.current.isSending).toBe(true)
      })

      await act(async () => {
        finishSend({
          user_message: { ...mockMessages[1], content: messageContent },
          assistant_message: mockMessages[2],
          session: mockChatSession,
        })
      })

      await waitFor(() => {
        expect(result.current.isSending).toBe(false)
      })

      expect(mockChatApi.sendMessage).toHaveBeenCalledWith(subjectId, {
        content: messageContent,
        session_id: mockChatSession.id,
      })
    })

    it('handles send message error with rollback', async () => {
      const wrapper = createWrapper()
      const { result } = renderHook(() => useChatMessages(subjectId), { wrapper })

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      const originalMessagesLength = result.current.messages.length
      const error = new Error('Failed to send message')
      mockChatApi.sendMessage.mockRejectedValueOnce(error)

      // Send message
      act(() => {
        result.current.sendMessage('Test message')
      })

      // Wait for error
      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      // Should rollback to original messages
      expect(result.current.messages).toHaveLength(originalMessagesLength)
      expect(result.current.error).toEqual(error)
    })

    it('prevents sending empty messages', async () => {
      const wrapper = createWrapper()
      const { result } = renderHook(() => useChatMessages(subjectId), { wrapper })

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Try to send empty message
      await act(async () => {
        await result.current.sendMessage('')
      })

      expect(mockChatApi.sendMessage).not.toHaveBeenCalled()
    })

    it('prevents sending whitespace-only messages', async () => {
      const wrapper = createWrapper()
      const { result } = renderHook(() => useChatMessages(subjectId), { wrapper })

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Try to send whitespace message
      await act(async () => {
        await result.current.sendMessage('   \n  \t  ')
      })

      expect(mockChatApi.sendMessage).not.toHaveBeenCalled()
    })

    it('trims message content before sending', async () => {
      const wrapper = createWrapper()
      const { result } = renderHook(() => useChatMessages(subjectId), { wrapper })

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Send message with extra whitespace
      await act(async () => {
        await result.current.sendMessage('  Hello world  ')
      })

      expect(mockChatApi.sendMessage).toHaveBeenCalledWith(subjectId, {
        content: 'Hello world',
        session_id: mockChatSession.id,
      })
    })
  })

  describe('useChatStats', () => {
    const subjectId = 1

    it('loads chat statistics', async () => {
      const wrapper = createWrapper()
      
      const { result } = renderHook(() => useChatStats(subjectId), { wrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockChatApi.getStats).toHaveBeenCalledWith(subjectId)
      expect(result.current.data).toEqual(mockStats)
    })

    it('handles stats loading error', async () => {
      const wrapper = createWrapper()
      const error = new Error('Failed to load stats')
      mockChatApi.getStats.mockRejectedValue(error)  // the hook retries once
      const { result } = renderHook(() => useChatStats(subjectId), { wrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      }, { timeout: 4000 })
      mockChatApi.getStats.mockResolvedValue(mockStats)

      expect(result.current.error).toEqual(error)
    })
  })

  describe('useChatWidget', () => {
    it('initializes with default collapsed state', () => {
      const { result } = renderHook(() => useChatWidget())

      expect(result.current.widgetState).toBe('collapsed')
      expect(result.current.isCollapsed).toBe(true)
      expect(result.current.isExpanded).toBe(false)
      expect(result.current.isFullscreen).toBe(false)
      expect(result.current.hasNewMessages).toBe(false)
    })

    it('initializes with custom initial state', () => {
      const { result } = renderHook(() => useChatWidget('expanded'))

      expect(result.current.widgetState).toBe('expanded')
      expect(result.current.isExpanded).toBe(true)
      expect(result.current.isCollapsed).toBe(false)
      expect(result.current.isFullscreen).toBe(false)
    })

    it('opens chat from collapsed state', () => {
      const { result } = renderHook(() => useChatWidget())

      act(() => {
        result.current.openChat()
      })

      expect(result.current.widgetState).toBe('expanded')
      expect(result.current.isExpanded).toBe(true)
      expect(result.current.hasNewMessages).toBe(false)
    })

    it('closes chat to collapsed state', () => {
      const { result } = renderHook(() => useChatWidget('expanded'))

      act(() => {
        result.current.closeChat()
      })

      expect(result.current.widgetState).toBe('collapsed')
      expect(result.current.isCollapsed).toBe(true)
    })

    it('toggles fullscreen mode', () => {
      const { result } = renderHook(() => useChatWidget('expanded'))

      // Toggle to fullscreen
      act(() => {
        result.current.toggleFullscreen()
      })

      expect(result.current.widgetState).toBe('fullscreen')
      expect(result.current.isFullscreen).toBe(true)

      // Toggle back to expanded
      act(() => {
        result.current.toggleFullscreen()
      })

      expect(result.current.widgetState).toBe('expanded')
      expect(result.current.isExpanded).toBe(true)
    })

    it('manages new message notifications', () => {
      const { result } = renderHook(() => useChatWidget())

      // Mark as unread
      act(() => {
        result.current.markAsUnread()
      })

      expect(result.current.hasNewMessages).toBe(true)

      // Mark as read
      act(() => {
        result.current.markAsRead()
      })

      expect(result.current.hasNewMessages).toBe(false)
    })

    it('clears new messages when opening chat', () => {
      const { result } = renderHook(() => useChatWidget())

      // Mark as unread first
      act(() => {
        result.current.markAsUnread()
      })

      expect(result.current.hasNewMessages).toBe(true)

      // Open chat should clear new messages
      act(() => {
        result.current.openChat()
      })

      expect(result.current.hasNewMessages).toBe(false)
      expect(result.current.isExpanded).toBe(true)
    })

    it('allows direct state setting', () => {
      const { result } = renderHook(() => useChatWidget())

      act(() => {
        result.current.setWidgetState('fullscreen')
      })

      expect(result.current.widgetState).toBe('fullscreen')
      expect(result.current.isFullscreen).toBe(true)
    })
  })

  describe('Integration tests', () => {
    it('combines widget state with message management', async () => {
      const wrapper = createWrapper()
      const subjectId = 1

      const { result: widgetResult } = renderHook(() => useChatWidget())
      const { result: messagesResult } = renderHook(() => useChatMessages(subjectId), { wrapper })

      // Wait for messages to load
      await waitFor(() => {
        expect(messagesResult.current.isLoading).toBe(false)
      })

      // Open widget and send message
      act(() => {
        widgetResult.current.openChat()
      })

      await act(async () => {
        await messagesResult.current.sendMessage('Hello!')
      })

      expect(widgetResult.current.isExpanded).toBe(true)
      expect(mockChatApi.sendMessage).toHaveBeenCalledWith(subjectId, {
        content: 'Hello!',
        session_id: mockChatSession.id,
      })
    })

    it('handles concurrent operations gracefully', async () => {
      const wrapper = createWrapper()
      const { result } = renderHook(() => useChatMessages(1), { wrapper })

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // Send multiple messages concurrently, inside one act() (overlapping act scopes corrupt React's test state)
      await act(async () => {
        await Promise.all([
          result.current.sendMessage('Message 1'),
          result.current.sendMessage('Message 2'),
          result.current.sendMessage('Message 3'),
        ])
      })

      // All messages should have been sent
      expect(mockChatApi.sendMessage).toHaveBeenCalledTimes(3)
    })
  })

  describe('streaming answers', () => {

    it('exposes the answer as it streams, then clears it once the saved reply lands', async () => {
      let emit: (t: string) => void = () => {}
      let finish: (v: any) => void = () => {}
      mockChatApi.streamMessage.mockImplementationOnce((_s: number, _d: unknown, onToken: (t: string) => void) => {
        emit = onToken
        return new Promise((resolve) => { finish = resolve })
      })
      const { result } = renderHook(() => useChatMessages(1), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isLoading).toBe(false))

      act(() => { result.current.sendMessage('Explain DML') })
      await waitFor(() => expect(result.current.streamingText).toBe(''))
      act(() => { emit('DML changes '); emit('rows.') })
      expect(result.current.streamingText).toBe('DML changes rows.')

      await act(async () => {
        finish({
          user_message: { ...mockMessages[1], id: 101, content: 'Explain DML' },
          assistant_message: { ...mockMessages[2], id: 102, content: 'DML changes rows.' },
          session: mockChatSession,
        })
      })
      await waitFor(() => expect(result.current.streamingText).toBeNull())
      expect(result.current.messages.at(-1)?.content).toBe('DML changes rows.')
    })

    it('falls back to a normal request when the stream cannot start', async () => {
      const { StreamUnavailableError } = await vi.importActual<typeof import('../../services/chatApi')>('../../services/chatApi')
      mockChatApi.streamMessage.mockRejectedValueOnce(new StreamUnavailableError('no stream'))
      const { result } = renderHook(() => useChatMessages(1), { wrapper: createWrapper() })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      mockChatApi.sendMessage.mockClear()

      await act(async () => { await result.current.sendMessage('Hello') })

      expect(mockChatApi.sendMessage).toHaveBeenCalledTimes(1)
    })
  })
})
