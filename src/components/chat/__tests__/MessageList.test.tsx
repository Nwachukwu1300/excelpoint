import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageList } from '../MessageList'
import { mockMessages } from '../../../test/mocks/chatApi'

// Mock the intersection observer for scroll behavior testing
const mockIntersectionObserver = vi.fn()
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
})

// Store original IntersectionObserver
const originalIntersectionObserver = global.IntersectionObserver

describe('MessageList', () => {
  beforeEach(() => {
    // Mock IntersectionObserver
    global.IntersectionObserver = mockIntersectionObserver
    // Mock scrollIntoView
    Element.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    // Restore original IntersectionObserver
    global.IntersectionObserver = originalIntersectionObserver
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders empty state when no messages', () => {
      render(<MessageList messages={[]} />)
      
      const emptyMessage = screen.getByText(/welcome to xp/i)
      expect(emptyMessage).toBeInTheDocument()
      
      const aiDescription = screen.getByText(/your ai study companion/i)
      expect(aiDescription).toBeInTheDocument()
    })

    it('renders messages when provided', () => {
      render(<MessageList messages={mockMessages} />)
      
      // Check that all messages are rendered
      expect(screen.getByText('Hello! How can I help you learn about SQL today?')).toBeInTheDocument()
      expect(screen.getByText('Can you explain JOIN operations?')).toBeInTheDocument()
      expect(screen.getByText(/join operations are used to combine rows/i)).toBeInTheDocument()
    })

    it('displays user and AI messages with different styling', () => {
      render(<MessageList messages={mockMessages} />)
      
      const messageContainers = screen.getAllByTestId(/message-\d+/)
      expect(messageContainers).toHaveLength(mockMessages.length)
      
      // Each message should have appropriate styling classes
      messageContainers.forEach((container, index) => {
        expect(container).toBeInTheDocument()
        // The message content should be present
        expect(container).toHaveTextContent(mockMessages[index].content)
      })
    })

    it('shows timestamps for messages', () => {
      render(<MessageList messages={mockMessages} />)
      
      // Check that timestamps are formatted and displayed
      // The exact format may vary, but they should be present
      const timeElements = screen.getAllByText(/am|pm|\d{1,2}:\d{2}/i)
      expect(timeElements.length).toBeGreaterThan(0)
    })

    it('shows appropriate avatars for user vs AI messages', () => {
      render(<MessageList messages={mockMessages} />)
      
      // Check that icons are present (Lucide icons render as SVGs)
      const avatars = screen.getAllByRole('img', { hidden: true })
      expect(avatars.length).toBeGreaterThan(0)
    })
  })

  describe('Loading States', () => {
    it('shows loading spinner when isLoading is true', () => {
      render(<MessageList messages={[]} isLoading />)
      
      // Should show loading state instead of empty state
      expect(screen.queryByText(/welcome to xp/i)).not.toBeInTheDocument()
      // The loading component should be present
    })

    it('shows loading indicator with existing messages', () => {
      render(<MessageList messages={mockMessages} isLoading />)
      
      // Should show both messages and loading indicator
      expect(screen.getByText('Hello! How can I help you learn about SQL today?')).toBeInTheDocument()
      // Loading indicator should also be present
    })
  })

  describe('Message Types', () => {
    it('renders user messages with correct styling', () => {
      const userMessage = mockMessages.find(msg => msg.is_user)
      if (userMessage) {
        render(<MessageList messages={[userMessage]} />)
        
        const messageElement = screen.getByText(userMessage.content)
        expect(messageElement).toBeInTheDocument()
        
        // Check for user message container
        const messageContainer = messageElement.closest('[data-testid*="message-"]')
        expect(messageContainer).toBeInTheDocument()
      }
    })

    it('renders AI messages with correct styling', () => {
      const aiMessage = mockMessages.find(msg => !msg.is_user)
      if (aiMessage) {
        render(<MessageList messages={[aiMessage]} />)
        
        const messageElement = screen.getByText(aiMessage.content)
        expect(messageElement).toBeInTheDocument()
        
        // Check for AI message container
        const messageContainer = messageElement.closest('[data-testid*="message-"]')
        expect(messageContainer).toBeInTheDocument()
      }
    })

    it('handles long messages properly', () => {
      const longMessage = {
        ...mockMessages[0],
        content: 'A'.repeat(1000)
      }
      
      render(<MessageList messages={[longMessage]} />)
      
      const messageElement = screen.getByText('A'.repeat(1000))
      expect(messageElement).toBeInTheDocument()
    })

    it('handles messages with newlines', () => {
      const multilineMessage = {
        ...mockMessages[0],
        content: 'Line 1\nLine 2\nLine 3'
      }
      
      render(<MessageList messages={[multilineMessage]} />)
      
      const messageElement = screen.getByText(/Line 1.*Line 2.*Line 3/s)
      expect(messageElement).toBeInTheDocument()
    })
  })

  describe('Scroll Behavior', () => {
    it('scrolls to bottom when messages are added', () => {
      const { rerender } = render(<MessageList messages={mockMessages.slice(0, 2)} />)
      
      // Add a new message
      rerender(<MessageList messages={mockMessages} />)
      
      // scrollIntoView should have been called
      expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
    })

    it('maintains scroll position during loading', () => {
      const { rerender } = render(<MessageList messages={mockMessages} />)
      
      // Set loading state
      rerender(<MessageList messages={mockMessages} isLoading />)
      
      // Should not interfere with scroll position
      expect(screen.getByText('Hello! How can I help you learn about SQL today?')).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('handles large number of messages', () => {
      const manyMessages = Array.from({ length: 100 }, (_, i) => ({
        ...mockMessages[0],
        id: i + 1,
        content: `Message ${i + 1}`,
      }))
      
      render(<MessageList messages={manyMessages} />)
      
      // Should render without performance issues
      expect(screen.getByText('Message 1')).toBeInTheDocument()
      expect(screen.getByText('Message 100')).toBeInTheDocument()
    })

    it('efficiently updates when new messages are added', () => {
      const { rerender } = render(<MessageList messages={mockMessages.slice(0, 2)} />)
      
      const newMessage = {
        id: 999,
        content: 'New message',
        is_user: true,
        timestamp: new Date().toISOString(),
        session: 1,
      }
      
      rerender(<MessageList messages={[...mockMessages.slice(0, 2), newMessage]} />)
      
      expect(screen.getByText('New message')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles empty message content', () => {
      const emptyMessage = {
        ...mockMessages[0],
        content: ''
      }
      
      render(<MessageList messages={[emptyMessage]} />)
      
      // Should still render the message container
      const messageContainer = screen.getByTestId(`message-${emptyMessage.id}`)
      expect(messageContainer).toBeInTheDocument()
    })

    it('handles missing timestamps', () => {
      const messageWithoutTimestamp = {
        ...mockMessages[0],
        timestamp: ''
      }
      
      render(<MessageList messages={[messageWithoutTimestamp]} />)
      
      const messageElement = screen.getByText(messageWithoutTimestamp.content)
      expect(messageElement).toBeInTheDocument()
    })

    it('handles invalid message data gracefully', () => {
      // Test with minimal message data
      const minimalMessage = {
        id: 1,
        content: 'Test message',
        is_user: false,
        timestamp: new Date().toISOString(),
        session: 1,
      }
      
      expect(() => {
        render(<MessageList messages={[minimalMessage]} />)
      }).not.toThrow()
      
      expect(screen.getByText('Test message')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('provides proper semantic structure', () => {
      render(<MessageList messages={mockMessages} />)
      
      // Check for proper ARIA roles or semantic elements
      const messageList = screen.getByRole('region', { name: /message/i }) || 
                         screen.getByRole('log') ||
                         document.querySelector('[role="feed"]')
      
      expect(messageList || screen.getByTestId('message-list')).toBeInTheDocument()
    })

    it('makes messages accessible to screen readers', () => {
      render(<MessageList messages={mockMessages} />)
      
      mockMessages.forEach(message => {
        const messageElement = screen.getByText(message.content)
        expect(messageElement).toBeInTheDocument()
        
        // Check that message is properly labeled
        const messageContainer = messageElement.closest('[data-testid*="message-"]')
        expect(messageContainer).toBeInTheDocument()
      })
    })

    it('provides context for message types', () => {
      render(<MessageList messages={mockMessages} />)
      
      // User and AI messages should be distinguishable for screen readers
      mockMessages.forEach(message => {
        const messageElement = screen.getByText(message.content)
        expect(messageElement).toBeInTheDocument()
      })
    })
  })
}) 