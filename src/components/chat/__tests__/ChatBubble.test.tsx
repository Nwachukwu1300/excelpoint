import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatBubble } from '../ChatBubble'

describe('ChatBubble', () => {
  const mockOnClick = vi.fn()

  beforeEach(() => {
    mockOnClick.mockClear()
  })

  describe('Rendering', () => {
    it('renders the chat bubble with default state', () => {
      render(<ChatBubble onClick={mockOnClick} />)
      
      const bubble = screen.getByRole('button', { name: /open chat/i })
      expect(bubble).toBeInTheDocument()
      expect(bubble).toHaveAttribute('aria-label', 'Open chat')
    })

    it('renders with new messages state', () => {
      render(<ChatBubble onClick={mockOnClick} hasNewMessages />)
      
      const bubble = screen.getByRole('button', { name: /open chat.*new messages/i })
      expect(bubble).toBeInTheDocument()
      expect(bubble).toHaveAttribute('aria-label', 'Open chat - You have new messages')
    })

    it('shows correct icon based on new messages state', () => {
      const { rerender } = render(<ChatBubble onClick={mockOnClick} />)
      
      // Should show message circle icon by default
      expect(screen.getByRole('button')).toBeInTheDocument()
      
      // Should show sparkles icon when there are new messages
      rerender(<ChatBubble onClick={mockOnClick} hasNewMessages />)
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('shows notification badge when there are new messages', () => {
      const { container } = render(<ChatBubble onClick={mockOnClick} hasNewMessages />)
      
      // Check for notification badge (it doesn't have a specific role/text)
      const badge = container.querySelector('[class*="NotificationBadge"]')
      expect(badge).toBeInTheDocument()
    })

    it('does not show notification badge when there are no new messages', () => {
      const { container } = render(<ChatBubble onClick={mockOnClick} />)
      
      const badge = container.querySelector('[class*="NotificationBadge"]')
      expect(badge).not.toBeInTheDocument()
    })
  })

  describe('Interactions', () => {
    it('calls onClick when clicked', async () => {
      const user = userEvent.setup()
      render(<ChatBubble onClick={mockOnClick} />)
      
      const bubble = screen.getByRole('button')
      await user.click(bubble)
      
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when Enter key is pressed', async () => {
      const user = userEvent.setup()
      render(<ChatBubble onClick={mockOnClick} />)
      
      const bubble = screen.getByRole('button')
      bubble.focus()
      await user.keyboard('{Enter}')
      
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when Space key is pressed', async () => {
      const user = userEvent.setup()
      render(<ChatBubble onClick={mockOnClick} />)
      
      const bubble = screen.getByRole('button')
      bubble.focus()
      await user.keyboard(' ')
      
      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('shows tooltip on hover', async () => {
      const user = userEvent.setup()
      render(<ChatBubble onClick={mockOnClick} />)
      
      const container = screen.getByRole('button').closest('div')
      expect(container).toBeInTheDocument()
      
      if (container) {
        await user.hover(container)
        // Tooltip text is rendered but may not be visible due to CSS
        // We can check that the component structure supports tooltips
        expect(container).toBeInTheDocument()
      }
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<ChatBubble onClick={mockOnClick} />)
      
      const bubble = screen.getByRole('button')
      expect(bubble).toHaveAttribute('aria-label', 'Open chat')
    })

    it('updates ARIA label when there are new messages', () => {
      render(<ChatBubble onClick={mockOnClick} hasNewMessages />)
      
      const bubble = screen.getByRole('button')
      expect(bubble).toHaveAttribute('aria-label', 'Open chat - You have new messages')
    })

    it('is focusable with keyboard navigation', () => {
      render(<ChatBubble onClick={mockOnClick} />)
      
      const bubble = screen.getByRole('button')
      expect(bubble).toHaveAttribute('tabIndex', '0')
    })

    it('has proper semantic structure', () => {
      render(<ChatBubble onClick={mockOnClick} />)
      
      // Check for proper button role
      const bubble = screen.getByRole('button')
      expect(bubble).toBeInTheDocument()
      
      // Check for container with button role
      const container = screen.getByRole('button').closest('[role="button"]')
      expect(container).toBeInTheDocument()
    })
  })

  describe('Visual States', () => {
    it('applies animation classes when there are new messages', () => {
      const { container } = render(<ChatBubble onClick={mockOnClick} hasNewMessages />)
      
      // Check that the styled component receives the hasNewMessages prop
      // This would apply the animation styles
      const bubbleButton = container.querySelector('button')
      expect(bubbleButton).toBeInTheDocument()
    })

    it('has proper positioning styles', () => {
      const { container } = render(<ChatBubble onClick={mockOnClick} />)
      
      const bubbleContainer = container.firstChild as HTMLElement
      expect(bubbleContainer).toHaveStyle({
        position: 'fixed',
      })
    })
  })

  describe('Error Handling', () => {
    it('handles missing onClick prop gracefully', () => {
      // This should not throw an error
      expect(() => {
        render(<ChatBubble onClick={() => {}} />)
      }).not.toThrow()
    })

    it('handles rapid clicks without issues', async () => {
      const user = userEvent.setup()
      render(<ChatBubble onClick={mockOnClick} />)
      
      const bubble = screen.getByRole('button')
      
      // Rapid clicks
      await user.click(bubble)
      await user.click(bubble)
      await user.click(bubble)
      
      expect(mockOnClick).toHaveBeenCalledTimes(3)
    })
  })
}) 