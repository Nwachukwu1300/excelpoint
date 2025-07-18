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
  console.log('ChatWidget: Component rendering with subjectId:', subjectId)
  console.log('ChatWidget: initialState:', initialState)
  
  const [isExpanded, setIsExpanded] = useState(initialState === 'expanded')
  const [hasNewMessages, setHasNewMessages] = useState(false)

  useEffect(() => {
    console.log('ChatWidget: Component mounted, isExpanded:', isExpanded)
    console.log('ChatWidget: Will render ChatBubble:', !isExpanded)
  }, [isExpanded])

  const openChat = () => {
    console.log('ChatWidget: Opening chat')
    setIsExpanded(true)
    setHasNewMessages(false)
  }

  const closeChat = () => {
    console.log('ChatWidget: Closing chat')
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

  console.log('ChatWidget: Rendering, isExpanded:', isExpanded)

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