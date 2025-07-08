import { vi } from 'vitest'
import type { ChatMessage, ChatSession, SendMessageResponse, ChatStats } from '@/types/chat'

// Mock data
export const mockChatSession: ChatSession = {
  id: 1,
  user: 1,
  subject: 1,
  created_at: '2025-01-08T10:00:00Z',
  updated_at: '2025-01-08T10:00:00Z',
  is_active: true,
}

export const mockMessages: ChatMessage[] = [
  {
    id: 1,
    content: 'Hello! How can I help you learn about SQL today?',
    is_user: false,
    timestamp: '2025-01-08T10:00:00Z',
    session: 1,
  },
  {
    id: 2,
    content: 'Can you explain JOIN operations?',
    is_user: true,
    timestamp: '2025-01-08T10:01:00Z',
    session: 1,
  },
  {
    id: 3,
    content: 'Certainly! JOIN operations are used to combine rows from two or more tables...',
    is_user: false,
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
  sendMessage: vi.fn().mockImplementation(async (subjectId: number, data: any) => {
    const response: SendMessageResponse = {
      message: {
        id: Date.now(),
        content: `Mock response to: ${data.content}`,
        is_user: false,
        timestamp: new Date().toISOString(),
        session: mockChatSession.id,
      },
      session: mockChatSession,
    }
    return response
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