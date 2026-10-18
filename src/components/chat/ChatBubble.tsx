import React from 'react'
import type { ChatBubbleProps } from '@/types/chat'

export const ChatBubble: React.FC<ChatBubbleProps> = ({ 
  onClick, 
  hasNewMessages = false 
}) => {
  // One native button: it is focusable and handles Enter/Space itself (no nested interactive elements)
  const buttonStyle: React.CSSProperties = {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    zIndex: 1000,
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
    cursor: 'pointer',
    userSelect: 'none',
    transition: 'all 0.3s ease',
    fontSize: '24px'
  }

  return (
    <button
      type="button"
      style={buttonStyle}
      onClick={onClick}
      title="Chat with XP"
      aria-label={hasNewMessages ? 'Open chat - You have new messages' : 'Open chat'}
    >
      <span aria-hidden="true">💬</span>
      {hasNewMessages && (
        <span
          data-testid="new-messages-badge"
          aria-hidden="true"
          style={{
            position: 'absolute',
            top: '-6px',
            right: '-6px',
            width: '12px',
            height: '12px',
            background: '#ef4444',
            borderRadius: '50%',
            border: '2px solid white'
          }}
        />
      )}
    </button>
  )
}
