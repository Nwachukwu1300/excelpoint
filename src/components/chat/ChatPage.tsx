import React, { useState } from 'react'
import styled from 'styled-components'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, MessageSquare, X, Search } from 'lucide-react'
import { useChatMessages, chatQueryKeys } from '@/hooks/useChat'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { SessionStorageManager } from '@/utils/sessionStorage'
import { chatApi } from '@/services/chatApi'
import type { ChatSession } from '@/types/chat'

// Styled components
const PageContainer = styled.div`
  display: flex;
  height: 100vh;
  width: 100vw;
  background: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
`

const Sidebar = styled.div`
  width: 280px;
  background: linear-gradient(180deg, #3b82f6 0%, #1e40af 100%);
  color: white;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e2e8f0;
  position: relative;
`

const SidebarHeader = styled.div`
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
`

const NewChatButton = styled.button`
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
  }
  
  &:active {
    transform: translateY(0);
  }
`

const ChatHistory = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 3px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.3);
  }
`

const SessionItem = styled.div<{ $isSelected: boolean }>`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: ${props => props.$isSelected ? 'rgba(255, 255, 255, 0.15)' : 'transparent'};
  
  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
`

const SessionTitle = styled.div`
  flex: 1;
  font-size: 14px;
  line-height: 1.3;
  color: ${props => props.color || 'rgba(255, 255, 255, 0.9)'};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`

const MainArea = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
`

const ChatHeader = styled.div`
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
`

const HeaderTitle = styled.h1`
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
`

const CloseButton = styled.button`
  padding: 8px;
  border: none;
  background: #f1f5f9;
  border-radius: 8px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: #e2e8f0;
    color: #334155;
  }
`

const ChatContent = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`

const LoadingState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
`

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  text-align: center;
`

interface ChatPageProps {
  subjectId: number
  onClose?: () => void
}

export const ChatPage: React.FC<ChatPageProps> = ({ subjectId, onClose }) => {
  const [selectedSessionId, setSelectedSessionId] = useState<number | undefined>()
  const queryClient = useQueryClient()

  // Get chat sessions for sidebar
  const { data: historyData, isLoading: isHistoryLoading } = useQuery({
    queryKey: ['chat', 'history', subjectId],
    queryFn: async () => {
      const result = await chatApi.getSessionHistory(subjectId, {
        limit: 50,
        includeInactive: true
      })
      return result
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
  })

  // Get current chat session and messages
  const { 
    messages, 
    session,
    isLoading: isChatLoading, 
    sendMessage, 
    isSending 
  } = useChatMessages(subjectId, selectedSessionId)

  const sessions = historyData?.sessions || []

  const handleStartNewChat = async () => {
    try {
      // Clear the current session from storage
      SessionStorageManager.clearSession(subjectId)
      
      // Clear selected session
      setSelectedSessionId(undefined)
      
      // Invalidate and refetch session-related queries
      await queryClient.invalidateQueries({
        queryKey: chatQueryKeys.session(subjectId)
      })
      
      // Clear messages cache
      queryClient.removeQueries({
        queryKey: chatQueryKeys.messages(subjectId, session?.id)
      })
      
      // Refresh history
      await queryClient.refetchQueries({
        queryKey: ['chat', 'history', subjectId]
      })
      
      console.log('✅ Started new chat session')
    } catch (error) {
      console.error('Failed to start new chat:', error)
    }
  }

  const handleSessionSelect = (selectedSession: ChatSession) => {
    setSelectedSessionId(selectedSession.id)
  }

  const formatSessionTitle = (session: ChatSession) => {
    if (session.title && session.title !== 'New conversation') {
      return session.title
    }
    
    const messageCount = session.message_count || 0
    const date = new Date(session.created_at)
    const today = new Date()
    const isToday = date.toDateString() === today.toDateString()
    
    if (messageCount === 0) {
      return 'New conversation'
    } else if (isToday) {
      return `Today's conversation`
    } else {
      return `${date.toLocaleDateString()} conversation`
    }
  }

  const handleSendMessage = async (content: string) => {
    console.log('ChatPage: Sending message:', content)
    try {
      await sendMessage(content)
      console.log('ChatPage: Message sent successfully')
      // Removed the unnecessary query refetch that was causing messages to disappear
      // The useChatMessages hook already handles updating the message list
    } catch (error) {
      console.error('ChatPage: Failed to send message:', error)
    }
  }

  return (
    <PageContainer>
      <Sidebar>
        <SidebarHeader>
          <NewChatButton onClick={handleStartNewChat}>
            <Plus size={16} />
            New chat
          </NewChatButton>
        </SidebarHeader>
        
        <ChatHistory>
          {isHistoryLoading ? (
            <LoadingState>
              <div style={{ 
                width: '20px', 
                height: '20px', 
                border: '2px solid rgba(255,255,255,0.3)', 
                borderTop: '2px solid white', 
                borderRadius: '50%', 
                animation: 'spin 1s linear infinite',
                marginBottom: '12px'
              }} />
              Loading conversations...
              <style>{`
                @keyframes spin {
                  0% { transform: rotate(0deg); }
                  100% { transform: rotate(360deg); }
                }
              `}</style>
            </LoadingState>
          ) : sessions.length === 0 ? (
            <EmptyState>
              <MessageSquare size={24} style={{ marginBottom: '12px', opacity: 0.5 }} />
              No conversations yet
              <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.7 }}>
                Start a new chat to begin
              </div>
            </EmptyState>
          ) : (
            sessions.map((sessionItem) => (
              <SessionItem
                key={sessionItem.id}
                $isSelected={sessionItem.id === (selectedSessionId || session?.id)}
                onClick={() => handleSessionSelect(sessionItem)}
              >
                <MessageSquare size={14} style={{ opacity: 0.7, flexShrink: 0 }} />
                <SessionTitle>
                  {formatSessionTitle(sessionItem)}
                </SessionTitle>
              </SessionItem>
            ))
          )}
        </ChatHistory>
      </Sidebar>

      <MainArea>
        <ChatHeader>
          <HeaderTitle>XP Assistant</HeaderTitle>
          {onClose && (
            <CloseButton onClick={onClose}>
              <X size={16} />
            </CloseButton>
          )}
        </ChatHeader>
        
        <ChatContent>
          <MessageList 
            messages={messages} 
            isLoading={isChatLoading}
          />
          <MessageInput 
            onSendMessage={handleSendMessage}
            isLoading={isSending}
            disabled={isChatLoading}
          />
        </ChatContent>
      </MainArea>
    </PageContainer>
  )
} 