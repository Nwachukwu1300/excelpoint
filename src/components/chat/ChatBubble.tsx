import React from 'react'
import type { ChatBubbleProps } from '@/types/chat'

export const ChatBubble: React.FC<ChatBubbleProps> = ({ 
  onClick, 
  hasNewMessages = false 
}) => {
  console.log('ChatBubble: Component rendering')
  const bubbleStyle: React.CSSProperties = {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    zIndex: 1000,
    cursor: 'pointer',
    userSelect: 'none'
  }

  const buttonStyle: React.CSSProperties = {
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    boxShadow: '0 8px 25px rgba(118, 75, 162, 0.4)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    transition: 'all 0.3s ease',
    outline: 'none',
    fontSize: '24px'
  }

  const handleClick = () => {
    console.log('Chat bubble clicked!')
    onClick()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <div style={bubbleStyle} onClick={handleClick} onKeyDown={handleKeyDown} tabIndex={0} role="button" aria-label="Open chat">
      <button style={buttonStyle} aria-label="Chat with XP">
        💬
        {hasNewMessages && (
          <div style={{
            position: 'absolute',
            top: '-6px',
            right: '-6px',
            width: '12px',
            height: '12px',
            background: '#ef4444',
            borderRadius: '50%',
            border: '2px solid white'
          }} />
        )}
      </button>
    </div>
  )
}

export default ChatBubble 