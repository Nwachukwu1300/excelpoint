// Main chat widget component
export { ChatWidget } from './ChatWidget'

// Individual chat components
export { ChatBubble } from './ChatBubble'
export { ChatPanel } from './ChatPanel'
export { MessageList } from './MessageList'
export { MessageInput } from './MessageInput'
export { TypingIndicator } from './TypingIndicator'

// Re-export types for convenience
export type {
  MessageListProps,
  MessageInputProps,
  ChatBubbleProps,
  ChatMessage,
  ChatSession,
  ChatStats,
} from '@/types/chat' 