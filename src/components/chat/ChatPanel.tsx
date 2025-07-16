import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { TypingIndicator } from './TypingIndicator';
import { useChatMessages } from '../../hooks/useChat';

interface ChatPanelProps {
  subjectId: number;
  onClose?: () => void;
  className?: string;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  subjectId,
  onClose,
  className
}) => {
  const {
    messages,
    session,
    isLoading,
    isSending,
    sendMessage,
    error
  } = useChatMessages(subjectId);

  const handleSendMessage = async (content: string) => {
    try {
      await sendMessage(content);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  // Styled components
  const Container = className ? 'div' : 'div';
  const Header = 'div';
  const Content = 'div';
  const HeaderControls = 'div';
  const ControlButton = 'button';

  const containerStyles = className ? {} : {
    position: 'fixed' as const,
    bottom: '20px',
    right: '20px',
    width: '400px',
    height: '600px',
    backgroundColor: '#1a1a1a',
    border: '1px solid #333',
    borderRadius: '12px',
    display: 'flex',
    flexDirection: 'column' as const,
    zIndex: 1000,
    boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
    overflow: 'hidden'
  };

  const headerStyles = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid #333',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  };

  const contentStyles = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden'
  };

  const controlsStyles = {
    display: 'flex',
    gap: '8px'
  };

  const buttonStyles = {
    background: 'rgba(255, 255, 255, 0.2)',
    border: 'none',
    borderRadius: '6px',
    padding: '8px',
    cursor: 'pointer',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background-color 0.2s'
  };

  return (
    <Container style={containerStyles} className={className}>
      <Header style={headerStyles}>
        <div style={{ color: 'white', fontWeight: 'bold', fontSize: '16px' }}>
          🤖 XP Assistant
        </div>
        
        <HeaderControls style={controlsStyles}>
          {onClose && (
            <ControlButton
              onClick={onClose}
              aria-label="Close chat"
              title="Close chat"
              style={buttonStyles}
            >
              <X size={16} />
            </ControlButton>
          )}
        </HeaderControls>
      </Header>

      <Content style={contentStyles}>
        <MessageList 
          messages={messages} 
          isLoading={isLoading}
        />
        
        {isSending ? <TypingIndicator /> : null}
        
        <MessageInput 
          onSendMessage={handleSendMessage}
          isLoading={isSending}
          disabled={isLoading}
        />
      </Content>

      {error ? (
        <div style={{
          padding: '12px 20px',
          backgroundColor: '#ff4444',
          color: 'white',
          fontSize: '14px',
          borderTop: '1px solid #333'
        }}>
          Error: {error instanceof Error ? error.message : String(error)}
        </div>
      ) : null}
    </Container>
  );
}; 