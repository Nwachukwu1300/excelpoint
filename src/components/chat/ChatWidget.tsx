import React, { useEffect } from 'react'
import { ChatBubble } from './ChatBubble'
import { ChatPanel } from './ChatPanel'
import { useChatWidget } from '@/hooks/useChat'
import type { ChatWidgetProps, ChatWidgetState } from '@/types/chat'

interface ChatWidgetComponent extends React.FC<ChatWidgetProps> {}

export const ChatWidget: ChatWidgetComponent = ({ 
  subjectId, 
  initialState = 'collapsed' 
}) => {
  const {
    widgetState,
    hasNewMessages,
    isCollapsed,
    isExpanded,
    isFullscreen,
    openChat,
    closeChat,
    toggleFullscreen,
    markAsRead,
  } = useChatWidget(initialState)

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Escape key closes chat or exits fullscreen
      if (event.key === 'Escape') {
        if (isFullscreen) {
          toggleFullscreen()
        } else if (isExpanded) {
          closeChat()
        }
      }
      
      // Ctrl/Cmd + K opens chat
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault()
        if (isCollapsed) {
          openChat()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isCollapsed, isExpanded, isFullscreen, openChat, closeChat, toggleFullscreen])

  // Handle click outside to close (only for expanded state, not fullscreen)
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
  }, [isExpanded, closeChat])

  return (
    <>
      {/* Chat Bubble - Always rendered, only visible when collapsed */}
      {isCollapsed && (
        <ChatBubble
          onClick={openChat}
          hasNewMessages={hasNewMessages}
        />
      )}
      
      {/* Chat Panel - Rendered when expanded or fullscreen */}
      {(isExpanded || isFullscreen) && (
        <div data-chat-panel>
          <ChatPanel
            subjectId={subjectId}
            onClose={closeChat}
            onToggleFullscreen={toggleFullscreen}
            isFullscreen={isFullscreen}
          />
        </div>
      )}
    </>
  )
}

export default ChatWidget 