import React, { useEffect, useState } from 'react'
import { ChatBubble } from './ChatBubble'
import { ChatPanel } from './ChatPanel'

interface ChatWidgetProps {
  subjectId: number;
  initialState?: 'collapsed' | 'expanded';
}

export const ChatWidget: React.FC<ChatWidgetProps> = ({ 
  subjectId, 
  initialState = 'collapsed' 
}) => {
  const [isExpanded, setIsExpanded] = useState(initialState === 'expanded')
  const [hasNewMessages, setHasNewMessages] = useState(false)

  const openChat = () => {
    setIsExpanded(true)
    setHasNewMessages(false)
  }

  const closeChat = () => {
    setIsExpanded(false)
  }

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Escape key closes chat
      if (event.key === 'Escape' && isExpanded) {
        closeChat()
      }
      
      // Ctrl/Cmd + K opens chat
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault()
        if (!isExpanded) {
          openChat()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isExpanded])

  // Handle click outside to close
  useEffect(() => {
    if (!isExpanded) return

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      const chatPanel = document.querySelector('[data-chat-panel]')
      
      if (chatPanel && !chatPanel.contains(target)) {
        closeChat()
      }
    }

    // Small delay to prevent immediate closure after opening
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside)
    }, 100)

    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isExpanded])

  return (
    <>
      {/* Chat Bubble - Only visible when collapsed */}
      {!isExpanded && (
        <ChatBubble
          onClick={openChat}
          hasNewMessages={hasNewMessages}
        />
      )}
      
      {/* Chat Panel - Only rendered when expanded */}
      {isExpanded && (
        <div data-chat-panel>
          <ChatPanel
            subjectId={subjectId}
            onClose={closeChat}
          />
        </div>
      )}
    </>
  )
}

export default ChatWidget 