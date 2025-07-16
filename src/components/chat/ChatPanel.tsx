import React, { useState } from 'react'
import styled from 'styled-components'
import { X, History, Brain, ExternalLink } from 'lucide-react'
import { useChatMessages } from '@/hooks/useChat'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { TypingIndicator } from './TypingIndicator'
import { ChatHistoryPanel } from './ChatHistoryPanel'
import type { ChatSession, ChatPanelProps } from '@/types/chat'

// Styled components
const PanelContainer = styled.div<{ isFullscreen?: boolean }>`
  position: fixed;
  ${props => props.isFullscreen ? `
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;
    height: 100vh;
    z-index: 9999;
  ` : `
    bottom: 24px;
    right: 24px;
    width: 400px;
    height: 600px;
    z-index: 1000;
    border-radius: 16px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  `}
  
  background: white;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  
  @media (max-width: 768px) {
    ${props => !props.isFullscreen && `
      bottom: 0;
      left: 0;
      right: 0;
      width: 100vw;
      height: 80vh;
      border-radius: 16px 16px 0 0;
    `}
  }
`

const PanelHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
`

const HeaderLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`

const HeaderIcon = styled.div`
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
`

const HeaderText = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`

const HeaderTitle = styled.h3`
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.2;
`

const HeaderSubtitle = styled.div`
  font-size: 13px;
  opacity: 0.9;
  line-height: 1.2;
`

const HeaderControls = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`

const ControlButton = styled.button`
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(10px);
  
  &:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
  }
  
  &:active {
    transform: translateY(0);
  }
  
  &:focus-visible {
    outline: 2px solid rgba(255, 255, 255, 0.5);
    outline-offset: 2px;
  }
`

const PanelContent = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fafbfc;
`

const StatusBar = styled.div`
  padding: 8px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: space-between;
`

const OnlineIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  
  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
    animation: pulse 2s ease-in-out infinite;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
`

interface ChatPanelComponent extends React.FC<ChatPanelProps> {}

export const ChatPanel: ChatPanelComponent = ({
  subjectId,
  selectedSessionId,
  onClose,
  isFullscreen = false,
  className
}) => {
  const [isHistoryVisible, setIsHistoryVisible] = useState(false)
  
  const { 
    messages, 
    session,
    isLoading, 
    sendMessage, 
    isSending 
  } = useChatMessages(subjectId, selectedSessionId)

  const handleSendMessage = async (content: string) => {
    try {
      await sendMessage(content)
    } catch (error) {
      console.error('Failed to send message:', error)
      // TODO: Show error toast
    }
  }


  const handleToggleHistory = () => {
    console.log('🔄 Toggling chat history, current state:', isHistoryVisible)
    setIsHistoryVisible(!isHistoryVisible)
    console.log('🔄 New history state will be:', !isHistoryVisible)
  }

  const handleSessionSelect = (selectedSession: ChatSession | null) => {
    console.log('Selected session:', selectedSession)
    setIsHistoryVisible(false)
    
    if (selectedSession) {
      // For now, reload with session parameter - this will trigger the hook to load that session
      const url = new URL(window.location.href)
      url.searchParams.set('session', selectedSession.id.toString())
      window.location.href = url.toString()
    }
  }

  const handleCloseHistory = () => {
    setIsHistoryVisible(false)
  }

  const handleOpenFullscreenPage = () => {
    // Open the dedicated fullscreen chat page
    const fullscreenUrl = `/subjects/${subjectId}/chat/`
    window.open(fullscreenUrl, '_blank')
  }

  // Use className for page mode, styled component for widget mode
  const ContainerComponent = className ? 'div' : PanelContainer
  const containerProps = className ? { className } : { isFullscreen }

  return (
    <>
      {isFullscreen && (
        <ChatHistoryPanel
          subjectId={subjectId}
          currentSessionId={session?.id}
          onSessionSelect={handleSessionSelect}
          isVisible={isHistoryVisible}
          onClose={handleCloseHistory}
        />
      )}
      
      <ContainerComponent {...containerProps}>
        <PanelHeader>
        <HeaderLeft>
          <HeaderIcon>
            <Brain size={20} />
          </HeaderIcon>
          <HeaderText>
            <HeaderTitle>XP Assistant</HeaderTitle>
            <HeaderSubtitle>Subject-specific AI help</HeaderSubtitle>
          </HeaderText>
        </HeaderLeft>
        
        <HeaderControls>
          {!className && (
            <>
              {/* Removed Chat History Button */}
              <ControlButton
                onClick={handleOpenFullscreenPage}
                aria-label="Open fullscreen chat"
                title="Open ChatGPT-style fullscreen interface"
                style={{ background: 'rgba(255, 255, 255, 0.2)' }}
              >
                <ExternalLink size={16} />
              </ControlButton>
            </>
          )}
          
          {onClose && (
            <ControlButton
              onClick={onClose}
              aria-label="Close chat"
              title="Close chat"
            >
              <X size={16} />
            </ControlButton>
          )}
        </HeaderControls>
      </PanelHeader>
      
      <StatusBar>
        <OnlineIndicator>
          Online
        </OnlineIndicator>
        <span>
          {messages.length} message{messages.length !== 1 ? 's' : ''}
        </span>
      </StatusBar>
      
      <PanelContent>
        <MessageList 
          messages={messages} 
          isLoading={isLoading || isSending} 
        />
        
        <MessageInput
          onSendMessage={handleSendMessage}
          isLoading={isSending}
          disabled={isLoading}
        />
      </PanelContent>
    </ContainerComponent>
    </>
  )
}

export default ChatPanel 