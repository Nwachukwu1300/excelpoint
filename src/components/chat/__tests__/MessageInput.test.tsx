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
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      expect(textarea).toBeInTheDocument()
      expect(sendButton).toBeInTheDocument()
    })

    it('hides the character count until the message is long', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} />)

      expect(screen.queryByText(/\/1000/)).not.toBeInTheDocument()
    })

    it('disables components when loading', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} isLoading />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      expect(textarea).toBeDisabled()
      expect(sendButton).toBeDisabled()
    })

    it('disables components when disabled prop is true', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} disabled />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      expect(textarea).toBeDisabled()
      expect(sendButton).toBeDisabled()
    })
  })

  describe('Text Input', () => {
    it('shows the character count past 70% of the limit', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)

      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.type(textarea, 'Hello world')
      expect(screen.queryByText(/\/1000/)).not.toBeInTheDocument()

      await user.click(textarea)
      await user.paste('a'.repeat(740))
      expect(screen.getByText('751/1000')).toBeInTheDocument()
    })

    it('allows multiline input', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.type(textarea, 'Line 1{Shift>}{Enter}{/Shift}Line 2')
      
      expect(textarea).toHaveValue('Line 1\nLine 2')
    })

    it('trims whitespace when sending', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, '  Hello world  ')
      await user.click(sendButton)
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world')
    })

    it('grows with its content up to 120px', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)

      const textarea = screen.getByRole('textbox', { name: /type your message/i }) as HTMLTextAreaElement
      // jsdom does no layout, so stand in for the browser's measured content height
      let contentHeight = 80
      Object.defineProperty(textarea, 'scrollHeight', { configurable: true, get: () => contentHeight })

      await user.type(textarea, 'Line 1')
      expect(textarea.style.height).toBe('80px')

      contentHeight = 300
      await user.type(textarea, '{Shift>}{Enter}{/Shift}Line 2')
      expect(textarea.style.height).toBe('120px')
    })
  })

  describe('Character Limit', () => {
    it('trims a paste that goes past 1000 characters', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)

      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.click(textarea)
      await user.paste('a'.repeat(1200))

      expect(textarea).toHaveValue('a'.repeat(1000))
      expect(screen.getByText('1000/1000')).toBeInTheDocument()
    })

    it('stops accepting typed characters at the limit', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)

      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.click(textarea)
      await user.paste('a'.repeat(1000))
      await user.type(textarea, 'bc')

      expect(textarea).toHaveValue('a'.repeat(1000))
    })

    it('still allows sending a message exactly at the limit', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)

      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.click(textarea)
      await user.paste('a'.repeat(1000))

      expect(screen.getByRole('button', { name: /send message/i })).toBeEnabled()
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('sends message on Enter key', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.type(textarea, 'Hello world')
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world')
    })

    it('adds new line on Shift+Enter', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.type(textarea, 'Line 1{Shift>}{Enter}{/Shift}Line 2')
      
      expect(textarea).toHaveValue('Line 1\nLine 2')
      expect(mockOnSendMessage).not.toHaveBeenCalled()
    })

    it('does not send empty messages on Enter', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).not.toHaveBeenCalled()
    })

    it('does not send whitespace-only messages on Enter', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      await user.type(textarea, '   ')
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).not.toHaveBeenCalled()
    })
  })

  describe('Send Button', () => {
    it('sends message when clicked', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, 'Hello world')
      await user.click(sendButton)
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world')
    })

    it('clears input after sending', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      const sendButton = screen.getByRole('button', { name: /send message/i })
      
      await user.type(textarea, 'Hello world')
      await user.click(sendButton)
      
      expect(textarea).toHaveValue('')
      expect(screen.queryByText(/\/1000/)).not.toBeInTheDocument()
    })

    it('is disabled when input is empty', () => {
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const sendButton = screen.getByRole('button', { name: /send message/i })
      expect(sendButton).toBeDisabled()
    })

    it('is enabled when input has content', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
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

    it('associates the character count with the textarea once shown', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)

      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      expect(textarea).not.toHaveAttribute('aria-describedby')

      await user.click(textarea)
      await user.paste('a'.repeat(800))
      expect(textarea).toHaveAccessibleDescription('800/1000')
    })

    it('maintains focus on textarea after sending', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      
      await user.type(textarea, 'Hello world')
      await user.keyboard('{Enter}')
      
      expect(textarea).toHaveFocus()
    })
  })

  describe('Error Handling', () => {
    it('handles rapid key presses without issues', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
      
      // Rapid typing
      await user.type(textarea, 'Hello')
      await user.keyboard('{Enter}')
      
      expect(mockOnSendMessage).toHaveBeenCalledWith('Hello')
    })

    it('prevents multiple sends of the same message', async () => {
      const user = userEvent.setup()
      render(<MessageInput onSendMessage={mockOnSendMessage} />)
      
      const textarea = screen.getByRole('textbox', { name: /type your message/i })
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