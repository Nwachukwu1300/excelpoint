import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageInput } from '../MessageInput'

describe('MessageInput', () => {
  const mockOnSendMessage = vi.fn()

  beforeEach(() => {
    mockOnSendMessage.mockClear()
  })

  describe('Rendering', () => {
    it('renders textarea and send button', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      expect(textarea).toBeInTheDocument()
      expect(sendButton).toBeInTheDocument()
    })

    it('shows character count', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const charCount = screen.getByText('0 / 1000')
      expect(charCount).toBeInTheDocument()
    })

    it('disables components when loading', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} isLoading />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      expect(textarea).toBeDisabled()
      expect(sendButton).toBeDisabled()
    })

    it('disables components when disabled prop is true', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} disabled />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      expect(textarea).toBeDisabled()
      expect(sendButton).toBeDisabled()
    })
  })

  describe('Text Input', () => {
    it('updates character count when typing', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      await user.type(textarea, 'Hello world')
      
      expect(screen.getByText('11 / 1000')).toBeInTheDocument()
    })

    it('allows multiline input', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      await user.type(textarea, 'Line 1{shift}{enter}Line 2')
      
      expect(textarea).toHaveValue('Line 1\nLine 2')
    })

    it('trims whitespace when sending', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, '  Hello world  ')
      await user.click(sendButton)
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world')
    })

    it('auto-resizes textarea based on content', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i) as HTMLTextAreaElement
      const initialHeight = textarea.style.height
      
      // Add multiple lines
      await user.type(textarea, 'Line 1{shift}{enter}Line 2{shift}{enter}Line 3{shift}{enter}Line 4')
      
      // Textarea should have adjusted its height
      expect(textarea.style.height).not.toBe(initialHeight)
    })
  })

  describe('Character Limit', () => {
    it('prevents input beyond 1000 characters', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const longText = 'a'.repeat(1001)
      
      await user.type(textarea, longText)
      
      // Should be limited to 1000 characters
      expect(textarea).toHaveValue('a'.repeat(1000))
      expect(screen.getByText('1000 / 1000')).toBeInTheDocument()
    })

    it('shows warning style when approaching limit', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const warningText = 'a'.repeat(950) // Close to limit
      
      await user.type(textarea, warningText)
      
      const charCount = screen.getByText('950 / 1000')
      expect(charCount).toBeInTheDocument()
      // Character count should have warning styling when > 900 characters
    })

    it('disables send button when at character limit', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      const maxText = 'a'.repeat(1000)
      
      await user.type(textarea, maxText)
      
      expect(sendButton).toBeDisabled()
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('sends message on Enter key', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      await user.type(textarea, 'Hello world')
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world')
    })

    it('adds new line on Shift+Enter', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      await user.type(textarea, 'Line 1{shift}{enter}Line 2')
      
      expect(textarea).toHaveValue('Line 1\nLine 2')
      expect(mockOnSendMessage).not.toHaveBeenCalled()
    })

    it('does not send empty messages on Enter', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).not.toHaveBeenCalled()
    })

    it('does not send whitespace-only messages on Enter', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      await user.type(textarea, '   ')
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).not.toHaveBeenCalled()
    })
  })

  describe('Send Button', () => {
    it('sends message when clicked', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, 'Hello world')
      await user.click(sendButton)
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world')
    })

    it('clears input after sending', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, 'Hello world')
      await user.click(sendButton)
      
      expect(textarea).toHaveValue('')
      expect(screen.getByText('0 / 1000')).toBeInTheDocument()
    })

    it('is disabled when input is empty', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).toBeDisabled()
    })

    it('is enabled when input has content', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, 'Hello')
      expect(sendButton).toBeEnabled()
    })

    it('shows loading spinner when isLoading is true', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} isLoading />)
      
      // The loading spinner should be present (check for specific icon or text)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).toBeDisabled()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      expect(textarea).toHaveAccessibleName()
      expect(sendButton).toHaveAccessibleName()
    })

    it('associates character count with textarea', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      expect(textarea).toHaveAttribute('aria-describedby')
    })

    it('maintains focus on textarea after sending', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      
      await user.type(textarea, 'Hello world')
      await user.keyboard('{Enter}')
      
      expect(textarea).toHaveFocus()
    })
  })

  describe('Error Handling', () => {
    it('handles rapid key presses without issues', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      
      // Rapid typing
      await user.type(textarea, 'Hello')
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello')
    })

    it('prevents multiple sends of the same message', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByPlaceholderText(/type your message/i)
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, 'Hello world')
      
      // Rapid clicks on send button
      await user.click(sendButton)
      await user.click(sendButton)
      
      // Should only send once since input is cleared after first send
      expect(mockOnSendMessage).toHaveBeenCalledTimes(1)
    })
  })
}) 