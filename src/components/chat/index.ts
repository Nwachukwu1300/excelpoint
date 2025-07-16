// Main chat widget component
export { ChatWidget } from './ChatWidget'

// Individual chat components
export { ChatBubble } from './ChatBubble'
export { ChatPanel } from './ChatPanel'
export { ChatPage } from './ChatPage'
export { ChatHistoryPanel } from './ChatHistoryPanel'
export { MessageList } from './MessageList'
export { MessageInput } from './MessageInput'
export { TypingIndicator } from './TypingIndicator'

// Re-export types for convenience
export type {
  ChatWidgetProps,
  ChatPanelProps,
  MessageListProps,
  MessageInputProps,
  ChatBubbleProps,
  ChatMessage,
  ChatSession,
  ChatStats,
  ChatWidgetState,
} from '@/types/chat' 