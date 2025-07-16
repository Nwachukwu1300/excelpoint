import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { chatApi } from '../../services/chatApi'
import type { ChatSession } from '../../types/chat'

interface ChatHistoryPanelProps {
  subjectId: number
  currentSessionId?: number
  selectedSessionId?: number
  onSessionSelect: (session: ChatSession | null) => void
  onNewChat?: () => void
  isVisible?: boolean
  onClose?: () => void
}

interface SessionItemProps {
  session: ChatSession
  isSelected: boolean
  onClick: () => void
}

const SessionItem: React.FC<SessionItemProps> = ({ session, isSelected, onClick }) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInMinutes = (now.getTime() - date.getTime()) / (1000 * 60)
    
    if (diffInMinutes < 1) {
      return 'Just now'
    } else if (diffInMinutes < 60) {
      return `${Math.floor(diffInMinutes)}m ago`
    } else if (diffInMinutes < 1440) { // 24 hours
      return `${Math.floor(diffInMinutes / 60)}h ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  // Generate a ChatGPT-style title based on the session
  const getSessionTitle = (session: ChatSession) => {
    if (session.title && session.title !== 'New conversation') {
      return session.title
    }
    
    // Generate a title based on message count and date
    const messageCount = session.message_count || 0
    if (messageCount === 0) {
      return 'New conversation'
    } else if (messageCount < 5) {
      return `Chat ${session.id}`
    } else {
      return `Conversation ${session.id}`
    }
  }

  const title = getSessionTitle(session)

  return (
    <div
      className={`mx-2 my-1 p-3 rounded-lg cursor-pointer transition-colors ${
        isSelected 
          ? 'bg-gray-800 text-white' 
          : 'text-gray-300 hover:bg-gray-800'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-3">
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <div className="flex-1 min-w-0">
          <p className="text-sm truncate">
            {title}
          </p>
        </div>
      </div>
    </div>
  )
}

export const ChatHistoryPanel: React.FC<ChatHistoryPanelProps> = ({
  subjectId,
  currentSessionId,
  selectedSessionId,
  onSessionSelect,
  onNewChat,
  isVisible = true,
  onClose
}) => {
  // Query for session history
  const {
    data: historyData,
    isLoading,
    isError,
    refetch
  } = useQuery({
    queryKey: ['chat', 'history', subjectId],
    queryFn: async () => {
      console.log('🔍 Fetching chat history for subject:', subjectId)
      try {
        const result = await chatApi.getSessionHistory(subjectId, {
          limit: 30,
          includeInactive: true
        })
        console.log('✅ Chat history loaded:', result)
        return result
      } catch (error) {
        console.error('❌ Failed to load chat history:', error)
        throw error
      }
    },
    enabled: isVisible,
    staleTime: 1000 * 60 * 2, // 2 minutes
    refetchOnWindowFocus: false
  })

  const sessions = historyData?.sessions || []
  const metadata = historyData?.metadata

  const handleSessionClick = (session: ChatSession) => {
    onSessionSelect(session)
  }

  if (!isVisible) {
    return null
  }

  console.log('📱 ChatHistoryPanel is visible, rendering with', sessions.length, 'sessions')

  return (
    <div className="fixed inset-y-0 left-0 w-64 bg-gray-900 text-white flex flex-col shadow-2xl"
         style={{ zIndex: 99999 }} // Ensure it's above everything else
    >
      {/* Header */}
      <div className="p-3">
        <button
          onClick={() => {
            // Start new chat by clearing session and reloading
            window.location.reload()
          }}
          className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-600 hover:border-gray-500 transition-colors group"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          <span className="text-sm">New chat</span>
        </button>
        
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-3 right-3 p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-800"
            aria-label="Close sidebar"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>



      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto py-2">
        {isLoading ? (
          <div className="p-4 text-center">
            <div className="inline-block w-6 h-6 border-2 border-gray-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-2 text-sm text-gray-400">Loading history...</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-sm text-gray-400">No previous conversations</p>
          </div>
        ) : (
          <div>
            {sessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isSelected={session.id === (selectedSessionId || currentSessionId)}
                onClick={() => handleSessionClick(session)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatHistoryPanel 