import { describe, it, expect } from 'vitest'
import { SessionStorageManager } from '../sessionStorage'
import type { ChatSession } from '@/types/chat'

const session: ChatSession = {
  id: 7, user: 1, subject: 3, status: 'active', is_active: true,
  last_activity: '2026-10-22T10:00:00Z', created_at: '2026-10-22T10:00:00Z', updated_at: '2026-10-22T10:00:00Z',
}

describe('SessionStorageManager', () => {
  it('persists a chat session per subject and clears it', () => {
    SessionStorageManager.storeSession(3, session)
    expect(SessionStorageManager.getStoredSession(3)?.sessionId).toBe(7)
    expect(SessionStorageManager.getStoredSession(4)).toBeNull()

    SessionStorageManager.clearSession(3)
    expect(SessionStorageManager.getStoredSession(3)).toBeNull()
  })
})
