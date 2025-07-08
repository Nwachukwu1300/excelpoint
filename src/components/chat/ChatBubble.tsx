import React from 'react'
import styled, { keyframes, css } from 'styled-components'
import { MessageCircle, Sparkles } from 'lucide-react'
import type { ChatBubbleProps } from '@/types/chat'

// Animations
const pulse = keyframes`
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
`

const bounce = keyframes`
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-4px); }
  60% { transform: translateY(-2px); }
`

const ripple = keyframes`
  0% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.5);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
`

// Styled components
const BubbleContainer = styled.div`
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  cursor: pointer;
  user-select: none;
  
  @media (max-width: 768px) {
    bottom: 16px;
    right: 16px;
  }
`

const BubbleButton = styled.button<{ hasNewMessages?: boolean }>`
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border: none;
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
  position: relative;
  overflow: hidden;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 35px rgba(59, 130, 246, 0.5);
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  }
  
  &:active {
    transform: translateY(0);
  }
  
  &:focus-visible {
    ring: 3px solid rgba(59, 130, 246, 0.3);
  }
  
  ${props => props.hasNewMessages && css`
    animation: ${pulse} 2s infinite, ${ripple} 2s infinite;
  `}
  
  @media (max-width: 768px) {
    width: 52px;
    height: 52px;
  }
`

const IconContainer = styled.div<{ hasNewMessages?: boolean }>`
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  
  ${props => props.hasNewMessages && css`
    animation: ${bounce} 1s infinite;
  `}
`

const NotificationBadge = styled.div`
  position: absolute;
  top: -6px;
  right: -6px;
  width: 12px;
  height: 12px;
  background: #ef4444;
  border-radius: 50%;
  border: 2px solid white;
  animation: ${pulse} 1.5s infinite;
`

const Tooltip = styled.div`
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  border-radius: 6px;
  font-size: 14px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transform: translateY(4px);
  transition: all 0.2s ease;
  pointer-events: none;
  z-index: 1001;
  
  &::after {
    content: '';
    position: absolute;
    top: 100%;
    right: 12px;
    border: 4px solid transparent;
    border-top-color: rgba(0, 0, 0, 0.8);
  }
  
  ${BubbleContainer}:hover & {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
  }
`

interface ChatBubbleComponent extends React.FC<ChatBubbleProps> {}

export const ChatBubble: ChatBubbleComponent = ({ 
  onClick, 
  hasNewMessages = false 
}) => {
  return (
    <BubbleContainer onClick={onClick} role="button" tabIndex={0} aria-label="Open chat">
      <BubbleButton 
        hasNewMessages={hasNewMessages}
        aria-label={hasNewMessages ? "Open chat - You have new messages" : "Open chat"}
      >
        <IconContainer hasNewMessages={hasNewMessages}>
          {hasNewMessages ? (
            <Sparkles size={24} />
          ) : (
            <MessageCircle size={24} />
          )}
          {hasNewMessages && <NotificationBadge />}
        </IconContainer>
      </BubbleButton>
      
      <Tooltip>
        {hasNewMessages ? "You have new messages!" : "Chat with XP"}
      </Tooltip>
    </BubbleContainer>
  )
}

export default ChatBubble 