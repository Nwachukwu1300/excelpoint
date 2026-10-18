import { vi } from 'vitest'
import type { ChatMessage, ChatSession, SendMessageResponse, ChatStats } from '@/types/chat'

// Mock data
export const mockChatSession: ChatSession = {
  id: 1,
  user: 1,
  subject: 1,
  status: 'active',
  is_active: true,
  last_activity: '2025-01-08T10:00:00Z',
  created_at: '2025-01-08T10:00:00Z',
  updated_at: '2025-01-08T10:00:00Z',
}

export const mockMessages: ChatMessage[] = [
  {
    id: 1,
    content: 'Hello! How can I help you learn about SQL today?',
    role: 'assistant',
    timestamp: '2025-01-08T10:00:00Z',
    session: 1,
  },
  {
    id: 2,
    content: 'Can you explain JOIN operations?',
    role: 'user',
    timestamp: '2025-01-08T10:01:00Z',
    session: 1,
  },
  {
    id: 3,
    content: 'Certainly! JOIN operations are used to combine rows from two or more tables...',
    role: 'assistant',
    timestamp: '2025-01-08T10:01:30Z',
    session: 1,
  },
]

export const mockStats: ChatStats = {
  total_messages: 50,
  total_sessions: 5,
  average_messages_per_session: 10,
  last_activity: '2025-01-08T10:01:30Z',
}

// Mock API functions
export const mockChatApi = {
  getOrCreateSession: vi.fn().mockResolvedValue(mockChatSession),
  getMessages: vi.fn().mockResolvedValue(mockMessages),
  sendMessage: vi.fn().mockImplementation(async (_subjectId: number, data: { content: string }) => {
    const now = new Date().toISOString()
    const response: SendMessageResponse = {
      user_message: { id: Date.now(), content: data.content, role: 'user', timestamp: now, session: mockChatSession.id },
      assistant_message: {
        id: Date.now() + 1,
        content: `Mock response to: ${data.content}`,
        role: 'assistant',
        timestamp: now,
        session: mockChatSession.id,
      },
      session: mockChatSession,
    }
    return response
  }),
  validateSession: vi.fn().mockResolvedValue({ valid: true, session: mockChatSession, message: 'ok' }),
  getSessionHistory: vi.fn().mockResolvedValue({
    sessions: [mockChatSession],
    metadata: { total_sessions: 1, active_sessions: 1, returned_count: 1, max_limit: 100 },
  }),
  getStats: vi.fn().mockResolvedValue(mockStats),
  getSession: vi.fn().mockResolvedValue(mockChatSession),
  deactivateSession: vi.fn().mockResolvedValue({ ...mockChatSession, is_active: false }),
}

// Mock axios
export const mockAxios = {
  create: vi.fn(() => ({
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
  })),
} 