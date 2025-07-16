import React, { useState, useRef, useEffect } from 'react'
import styled from 'styled-components'
import { Send, Loader2 } from 'lucide-react'
import type { MessageInputProps } from '@/types/chat'

// Styled components
const InputContainer = styled.div`
  padding: 16px;
  border-top: 1px solid #e5e7eb;
  background: white;
  display: flex;
  align-items: flex-end;
  gap: 12px;
`

const TextAreaContainer = styled.div`
  flex: 1;
  position: relative;
  min-height: 40px;
  max-height: 120px;
  background: #f9fafb;
  border: 1px solid #d1d5db;
  border-radius: 20px;
  transition: all 0.2s ease;
  
  &:focus-within {
    border-color: #3b82f6;
    background: white;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`

const StyledTextArea = styled.textarea`
  width: 100%;
  min-height: 40px;
  max-height: 120px;
  padding: 10px 16px;
  border: none;
  background: transparent;
  resize: none;
  outline: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.4;
  color: #1f2937;
  border-radius: 20px;
  
  &::placeholder {
    color: #6b7280;
  }
  
  &:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
`

const SendButton = styled.button<{ disabled?: boolean }>`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: ${props => props.disabled ? '#d1d5db' : 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'};
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  transition: all 0.2s ease;
  flex-shrink: 0;
  
  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
  
  &:focus-visible {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
  }
`

const CharacterCount = styled.div<{ isNearLimit?: boolean }>`
  position: absolute;
  bottom: 6px;
  right: 12px;
  font-size: 11px;
  color: ${props => props.isNearLimit ? '#ef4444' : '#9ca3af'};
  pointer-events: none;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 4px;
  border-radius: 4px;
`

interface MessageInputComponent extends React.FC<MessageInputProps> {}

export const MessageInput: MessageInputComponent = ({
  onSendMessage,
  isLoading = false,
  disabled = false
}) => {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const maxLength = 1000

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }, [message])

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    
    const trimmedMessage = message.trim()
    console.log('MessageInput: handleSubmit called with:', trimmedMessage)
    if (trimmedMessage && !isLoading && !disabled) {
      console.log('MessageInput: Calling onSendMessage')
      onSendMessage(trimmedMessage)
      setMessage('')
      
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    } else {
      console.log('MessageInput: Message not sent - conditions not met:', {
        trimmedMessage,
        isLoading,
        disabled
      })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Allow new line with Shift+Enter
        return
      } else {
        // Send message with Enter
        e.preventDefault()
        handleSubmit()
      }
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    if (value.length <= maxLength) {
      setMessage(value)
    }
  }

  const isNearLimit = message.length > maxLength * 0.8
  const canSend = message.trim().length > 0 && !isLoading && !disabled

  return (
    <InputContainer>
      <TextAreaContainer>
        <StyledTextArea
          ref={textareaRef}
          value={message}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask me anything about this subject..."
          disabled={disabled || isLoading}
          rows={1}
          aria-label="Type your message"
        />
        {message.length > maxLength * 0.7 && (
          <CharacterCount isNearLimit={isNearLimit}>
            {message.length}/{maxLength}
          </CharacterCount>
        )}
      </TextAreaContainer>
      
      <SendButton
        type="button"
        onClick={handleSubmit}
        disabled={!canSend}
        aria-label="Send message"
        title={!canSend ? 'Type a message to send' : 'Send message (Enter)'}
      >
        {isLoading ? (
          <Loader2 size={20} className="animate-spin" />
        ) : (
          <Send size={20} />
        )}
      </SendButton>
    </InputContainer>
  )
}

export default MessageInput 