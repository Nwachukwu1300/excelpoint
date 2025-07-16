import React from 'react'
import { ChatPage } from './ChatPage'

export const ChatPageDemo: React.FC = () => {
  return (
    <div style={{ height: '100vh' }}>
      <ChatPage 
        subjectId={1} // Replace with actual subject ID
        subjectName="Demo Subject - XP Assistant"
      />
    </div>
  )
}

export default ChatPageDemo 