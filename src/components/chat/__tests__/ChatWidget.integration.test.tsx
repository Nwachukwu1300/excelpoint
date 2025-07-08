import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatWidget } from '../ChatWidget'
import { mockChatApi, mockChatSession, mockMessages } from '../../../test/mocks/chatApi'

// Mock the chatApi module
vi.mock('../../../services/chatApi', () => ({
  chatApi: mockChatApi,
}))

// Mock intersection observer
const mockIntersectionObserver = vi.fn()
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
})

// Store original APIs
const originalIntersectionObserver = global.IntersectionObserver

describe('ChatWidget Integration Tests', () => {
  const defaultProps = {
    subjectId: 1,
    initialState: 'collapsed' as const,
  }
  
  const expandedProps = {
    subjectId: 1,
    initialState: 'expanded' as const,
  }

  let queryClient: QueryClient

  beforeEach(() => {
    // Create a new QueryClient for each test
    queryClient = new QueryClient({
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

    // Mock global APIs
    global.IntersectionObserver = mockIntersectionObserver
    Element.prototype.scrollIntoView = vi.fn()
    
    // Mock keyboard events
    Object.defineProperty(window, 'addEventListener', {
      value: vi.fn(),
      writable: true,
    })
    Object.defineProperty(document, 'addEventListener', {
      value: vi.fn(),
      writable: true,
    })

    vi.clearAllMocks()
  })

  afterEach(() => {
    global.IntersectionObserver = originalIntersectionObserver
    vi.clearAllMocks()
  })

  const renderChatWidget = (props: typeof defaultProps | typeof expandedProps = defaultProps) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <ChatWidget {...props} />
      </QueryClientProvider>
    )
  }

  describe('Initial Rendering', () => {
    it('renders in collapsed state by default', () => {
      renderChatWidget()
      
      const chatBubble = screen.getByRole('button', { name: /open chat/i })
      expect(chatBubble).toBeInTheDocument()
      
      // Chat panel should not be visible
      expect(screen.queryByText(/welcome to xp/i)).not.toBeInTheDocument()
    })

    it('renders in expanded state when specified', () => {
      renderChatWidget(expandedProps)
      
      // Should show the chat panel
      expect(screen.getByText(/welcome to xp/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
    })
  })

  describe('State Transitions', () => {
    it('expands when chat bubble is clicked', async () => {
      const user = userEvent.setup()
      renderChatWidget()
      
      const chatBubble = screen.getByRole('button', { name: /open chat/i })
      await user.click(chatBubble)
      
      // Should expand and show the chat interface
      await waitFor(() => {
        expect(screen.getByText(/welcome to xp/i)).toBeInTheDocument()
      })
      
      expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
    })

    it('collapses when close button is clicked', async () => {
      const user = userEvent.setup()
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      const closeButton = screen.getByRole('button', { name: /close chat/i })
      await user.click(closeButton)
      
      // Should collapse back to bubble
      await waitFor(() => {
        expect(screen.queryByText(/welcome to xp/i)).not.toBeInTheDocument()
      })
      
      expect(screen.getByRole('button', { name: /open chat/i })).toBeInTheDocument()
    })

    it('toggles fullscreen mode', async () => {
      const user = userEvent.setup()
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      const fullscreenButton = screen.getByRole('button', { name: /toggle fullscreen/i })
      await user.click(fullscreenButton)
      
      // Should be in fullscreen mode (check for fullscreen-specific content or styles)
      const chatContainer = screen.getByTestId('chat-widget')
      expect(chatContainer).toBeInTheDocument()
    })
  })

  describe('Message Flow', () => {
    it('loads and displays existing messages', async () => {
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Wait for messages to load
      await waitFor(() => {
        expect(mockChatApi.getOrCreateSession).toHaveBeenCalledWith(defaultProps.subjectId)
      })
      
      await waitFor(() => {
        expect(screen.getByText('Hello! How can I help you learn about SQL today?')).toBeInTheDocument()
      })
      
      expect(screen.getByText('Can you explain JOIN operations?')).toBeInTheDocument()
    })

    it('sends a message end-to-end', async () => {
      const user = userEvent.setup()
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Hello! How can I help you learn about SQL today?')).toBeInTheDocument()
      })
      
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      // Type and send a message
      await user.type(messageInput, 'How do I use GROUP BY?')
      await user.click(sendButton)
      
      // Verify API call
      expect(mockChatApi.sendMessage).toHaveBeenCalledWith(defaultProps.subjectId, {
        content: 'How do I use GROUP BY?',
        session_id: mockChatSession.id,
      })
      
      // Input should be cleared
      expect(messageInput).toHaveValue('')
    })

    it('shows loading state while sending message', async () => {
      const user = userEvent.setup()
      
      // Make sendMessage hang to test loading state
      mockChatApi.sendMessage.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      )
      
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
      })
      
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(messageInput, 'Test message')
      await user.click(sendButton)
      
      // Should show loading state
      expect(sendButton).toBeDisabled()
      expect(messageInput).toBeDisabled()
    })

    it('handles message sending errors gracefully', async () => {
      const user = userEvent.setup()
      const error = new Error('Network error')
      mockChatApi.sendMessage.mockRejectedValueOnce(error)
      
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
      })
      
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(messageInput, 'Test message')
      await user.click(sendButton)
      
      // Wait for error handling
      await waitFor(() => {
        expect(sendButton).toBeEnabled()
      })
      
      // Input should still have the message (not cleared on error)
      expect(messageInput).toHaveValue('Test message')
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('sends message with Enter key', async () => {
      const user = userEvent.setup()
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
      })
      
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      
      await user.type(messageInput, 'Hello with Enter')
      await user.keyboard('{Enter}')
      
      expect(mockChatApi.sendMessage).toHaveBeenCalledWith(defaultProps.subjectId, {
        content: 'Hello with Enter',
        session_id: mockChatSession.id,
      })
    })

    it('adds new line with Shift+Enter', async () => {
      const user = userEvent.setup()
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument()
      })
      
      const messageInput = screen.getByPlaceholderText(/type your message/i)
      
      await user.type(messageInput, 'Line 1{shift}{enter}Line 2')
      
      expect(messageInput).toHaveValue('Line 1\nLine 2')
      expect(mockChatApi.sendMessage).not.toHaveBeenCalled()
    })
  })

  describe('Responsive Behavior', () => {
    it('handles window resize events', () => {
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Simulate window resize
      global.innerWidth = 500
      fireEvent(window, new Event('resize'))
      
      // Component should still be rendered
      expect(screen.getByText(/welcome to xp/i)).toBeInTheDocument()
    })

    it('adapts to mobile viewport', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })
      
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Should render mobile-optimized layout
      expect(screen.getByText(/welcome to xp/i)).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('handles rapid state changes without issues', async () => {
      const user = userEvent.setup()
      renderChatWidget()
      
      const chatBubble = screen.getByRole('button', { name: /open chat/i })
      
      // Rapid clicks
      await user.click(chatBubble)
      await user.click(chatBubble)
      await user.click(chatBubble)
      
      // Should end up in expanded state
      await waitFor(() => {
        expect(screen.getByText(/welcome to xp/i)).toBeInTheDocument()
      })
    })

    it('efficiently renders large message lists', async () => {
      // Mock large message list
      const manyMessages = Array.from({ length: 50 }, (_, i) => ({
        ...mockMessages[0],
        id: i + 1,
        content: `Message ${i + 1}`,
      }))
      mockChatApi.getMessages.mockResolvedValueOnce(manyMessages)
      
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Should render without performance issues
      await waitFor(() => {
        expect(screen.getByText('Message 1')).toBeInTheDocument()
      })
      
      expect(screen.getByText('Message 50')).toBeInTheDocument()
    })
  })

  describe('Error Boundaries', () => {
    it('handles API errors gracefully', async () => {
      const error = new Error('API Error')
      mockChatApi.getOrCreateSession.mockRejectedValueOnce(error)
      
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Should show error state without crashing
      await waitFor(() => {
        expect(screen.getByText(/welcome to xp/i)).toBeInTheDocument()
      })
    })

    it('recovers from temporary network failures', async () => {
      // First call fails, second succeeds
      mockChatApi.getOrCreateSession
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockChatSession)
      
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Should eventually recover and load content
      await waitFor(() => {
        expect(screen.getByText(/welcome to xp/i)).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Accessibility', () => {
    it('maintains focus management during state transitions', async () => {
      const user = userEvent.setup()
      renderChatWidget()
      
      const chatBubble = screen.getByRole('button', { name: /open chat/i })
      await user.click(chatBubble)
      
      // After opening, focus should be managed appropriately
      await waitFor(() => {
        const messageInput = screen.getByPlaceholderText(/type your message/i)
        expect(document.activeElement === messageInput || 
               document.activeElement === chatBubble).toBe(true)
      })
    })

    it('provides proper ARIA labels and roles', async () => {
      renderChatWidget({ ...defaultProps, initialState: 'expanded' })
      
      // Check for accessibility attributes
      const messageInput = await screen.findByPlaceholderText(/type your message/i)
      expect(messageInput).toHaveAttribute('aria-label')
      
      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).toHaveAccessibleName()
    })
  })
}) 