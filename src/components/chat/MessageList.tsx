import React, { useEffect, useRef } from 'react'
import styled from 'styled-components'
import { format } from 'date-fns'
import { User, Brain } from 'lucide-react'
import type { MessageListProps, ChatMessage } from '@/types/chat'
import { TypingIndicator } from './TypingIndicator'

// Styled components
const MessagesContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-behavior: smooth;
  
  /* Custom scrollbar */
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f5f9;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 3px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
`

const MessageGroup = styled.div<{ isUser: boolean }>`
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 0 16px;
  flex-direction: ${props => props.isUser ? 'row-reverse' : 'row'};
`

const AvatarContainer = styled.div<{ isUser: boolean }>`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: ${props => props.isUser 
    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
    : 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'
  };
  color: white;
  margin-top: 4px;
`

const MessageBubble = styled.div<{ isUser: boolean }>`
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 18px;
  background: ${props => props.isUser 
    ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'
    : '#f1f5f9'
  };
  color: ${props => props.isUser ? 'white' : '#1e293b'};
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
  position: relative;
  
  /* Message tail */
  &::before {
    content: '';
    position: absolute;
    top: 6px;
    ${props => props.isUser ? 'right: -6px' : 'left: -6px'};
    width: 0;
    height: 0;
    border: 6px solid transparent;
    border-top-color: ${props => props.isUser 
      ? '#3b82f6'
      : '#f1f5f9'
    };
    ${props => props.isUser 
      ? 'border-right: none; border-top-right-radius: 4px;'
      : 'border-left: none; border-top-left-radius: 4px;'
    }
  }
`

const MessageContent = styled.div`
  white-space: pre-wrap;
  word-break: break-word;
  
  /* Style code blocks */
  code {
    background: rgba(0, 0, 0, 0.1);
    padding: 2px 4px;
    border-radius: 4px;
    font-family: 'Monaco', 'Consolas', monospace;
    font-size: 13px;
  }
  
  /* Style links */
  a {
    color: inherit;
    text-decoration: underline;
    opacity: 0.9;
    
    &:hover {
      opacity: 1;
    }
  }
`

const MessageMeta = styled.div<{ isUser: boolean }>`
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 11px;
  color: #64748b;
  ${props => props.isUser ? 'justify-content: flex-end;' : ''}
`

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 32px 16px;
  text-align: center;
  color: #64748b;
`

const EmptyStateIcon = styled.div`
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  color: white;
`

const EmptyStateTitle = styled.h3`
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
`

const EmptyStateText = styled.p`
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  max-width: 280px;
`

const LoadingState = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: #64748b;
  font-size: 14px;
`

interface MessageListComponent extends React.FC<MessageListProps> {}

export const MessageList: MessageListComponent = ({ 
  messages, 
  isLoading = false 
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isLoading])

  const formatMessageTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return format(date, 'HH:mm')
    } catch {
      return ''
    }
  }

  if (isLoading && messages.length === 0) {
    return (
      <MessagesContainer ref={containerRef}>
        <LoadingState>Loading conversation...</LoadingState>
      </MessagesContainer>
    )
  }

  if (messages.length === 0) {
    return (
      <MessagesContainer ref={containerRef}>
        <EmptyState>
          <EmptyStateIcon>
            <Brain size={28} />
          </EmptyStateIcon>
          <EmptyStateTitle>Welcome to XP!</EmptyStateTitle>
          <EmptyStateText>
            I'm your AI assistant for this subject. Ask me anything about the materials you've uploaded, and I'll help you learn and understand the content better.
          </EmptyStateText>
        </EmptyState>
      </MessagesContainer>
    )
  }

  return (
    <MessagesContainer ref={containerRef}>
      {messages.map((message: ChatMessage) => {
        const isUser = message.role === 'user'
        return (
          <MessageGroup key={message.id} isUser={isUser}>
            <AvatarContainer isUser={isUser}>
              {isUser ? (
                <User size={18} />
              ) : (
                <Brain size={18} />
              )}
            </AvatarContainer>
            
            <div>
              <MessageBubble isUser={isUser}>
                <MessageContent>{message.content}</MessageContent>
              </MessageBubble>
              <MessageMeta isUser={isUser}>
                <span>{formatMessageTime(message.timestamp)}</span>
              </MessageMeta>
            </div>
          </MessageGroup>
        )
      })}
      
      {isLoading && (
        <TypingIndicator variant="typing" />
      )}
      
      <div ref={messagesEndRef} />
    </MessagesContainer>
  )
}

export default MessageList 