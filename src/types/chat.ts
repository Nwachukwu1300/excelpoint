// Chat message types
export interface ChatMessage {
  id: number
  content: string
  role: 'user' | 'assistant'
  timestamp: string
  session: number
}

// Chat session types
export interface ChatSession {
  id: number
  user: number
  subject: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// Chat API request/response types
export interface SendMessageRequest {
  content: string
  session_id?: number
}

export interface SendMessageResponse {
  user_message: ChatMessage
  assistant_message: ChatMessage
  session: ChatSession
  response_metadata?: {
    chunks_retrieved: number
    response_time_seconds: number
    context_was_used: boolean
  }
}

// Chat stats types
export interface ChatStats {
  total_messages: number
  total_sessions: number
  average_messages_per_session: number
  last_activity: string | null
}

// Widget state types
export type ChatWidgetState = 'collapsed' | 'expanded' | 'fullscreen'

// Chat component props
export interface ChatWidgetProps {
  subjectId: number
  initialState?: ChatWidgetState
}

export interface MessageListProps {
  messages: ChatMessage[]
  isLoading?: boolean
}

export interface MessageInputProps {
  onSendMessage: (content: string) => void
  isLoading?: boolean
  disabled?: boolean
}

export interface ChatBubbleProps {
  onClick: () => void
  hasNewMessages?: boolean
}

export interface ChatPanelProps {
  subjectId: number
  onClose: () => void
  onToggleFullscreen: () => void
  isFullscreen?: boolean
}

// Error types
export interface ApiError {
  message: string
  status?: number
  detail?: string
} 