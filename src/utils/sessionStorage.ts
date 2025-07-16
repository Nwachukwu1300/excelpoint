import type { ChatSession } from '../types/chat'

const SESSION_STORAGE_KEY = 'xp-chat-sessions'
const ACTIVITY_STORAGE_KEY = 'xp-chat-activity'

export interface StoredSessionData {
  sessionId: number
  subjectId: number
  lastActivity: string
  isValid: boolean
}

export interface ActivityData {
  [subjectId: number]: {
    sessionId: number
    lastActivity: string
    isValid: boolean
  }
}

/**
 * Session Storage Utility for XP Chat
 * Handles localStorage persistence for chat sessions with timeout tracking
 */
export class SessionStorageManager {
  private static readonly TIMEOUT_MINUTES = 5

  /**
   * Store session data for a subject
   */
  static storeSession(subjectId: number, session: ChatSession): void {
    try {
      const activityData = this.getActivityData()
      activityData[subjectId] = {
        sessionId: session.id,
        lastActivity: new Date().toISOString(),
        isValid: session.status === 'active' && session.is_active
      }
      
      localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(activityData))
      
      // Also store individual session data
      const sessionKey = this.getSessionKey(subjectId)
      const sessionData: StoredSessionData = {
        sessionId: session.id,
        subjectId: subjectId,
        lastActivity: new Date().toISOString(),
        isValid: session.status === 'active' && session.is_active
      }
      
      localStorage.setItem(sessionKey, JSON.stringify(sessionData))
    } catch (error) {
      console.warn('Failed to store session data:', error)
    }
  }

  /**
   * Retrieve stored session data for a subject
   */
  static getStoredSession(subjectId: number): StoredSessionData | null {
    try {
      const sessionKey = this.getSessionKey(subjectId)
      const stored = localStorage.getItem(sessionKey)
      
      if (!stored) {
        return null
      }
      
      const sessionData: StoredSessionData = JSON.parse(stored)
      
      // Check if session might be expired based on local activity tracking
      if (this.isLocallyExpired(sessionData.lastActivity)) {
        this.clearSession(subjectId)
        return null
      }
      
      return sessionData
    } catch (error) {
      console.warn('Failed to retrieve session data:', error)
      return null
    }
  }

  /**
   * Update activity timestamp for a session
   */
  static updateActivity(subjectId: number): void {
    try {
      const sessionData = this.getStoredSession(subjectId)
      if (sessionData) {
        sessionData.lastActivity = new Date().toISOString()
        const sessionKey = this.getSessionKey(subjectId)
        localStorage.setItem(sessionKey, JSON.stringify(sessionData))
        
        // Also update in activity data
        const activityData = this.getActivityData()
        if (activityData[subjectId]) {
          activityData[subjectId].lastActivity = new Date().toISOString()
          localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(activityData))
        }
      }
    } catch (error) {
      console.warn('Failed to update activity:', error)
    }
  }

  /**
   * Clear session data for a subject
   */
  static clearSession(subjectId: number): void {
    try {
      const sessionKey = this.getSessionKey(subjectId)
      localStorage.removeItem(sessionKey)
      
      // Also remove from activity data
      const activityData = this.getActivityData()
      delete activityData[subjectId]
      localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(activityData))
    } catch (error) {
      console.warn('Failed to clear session data:', error)
    }
  }

  /**
   * Mark session as invalid but keep the data for potential recovery
   */
  static markSessionInvalid(subjectId: number): void {
    try {
      const sessionData = this.getStoredSession(subjectId)
      if (sessionData) {
        sessionData.isValid = false
        const sessionKey = this.getSessionKey(subjectId)
        localStorage.setItem(sessionKey, JSON.stringify(sessionData))
        
        // Also update in activity data
        const activityData = this.getActivityData()
        if (activityData[subjectId]) {
          activityData[subjectId].isValid = false
          localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(activityData))
        }
      }
    } catch (error) {
      console.warn('Failed to mark session invalid:', error)
    }
  }

  /**
   * Get all active sessions across subjects
   */
  static getAllActiveSessions(): ActivityData {
    return this.getActivityData()
  }

  /**
   * Clean up expired sessions from localStorage
   */
  static cleanupExpiredSessions(): void {
    try {
      const activityData = this.getActivityData()
      const cleanedData: ActivityData = {}
      let hasChanges = false
      
      Object.entries(activityData).forEach(([subjectIdStr, data]) => {
        if (!this.isLocallyExpired(data.lastActivity)) {
          cleanedData[parseInt(subjectIdStr)] = data
        } else {
          hasChanges = true
          // Also clear individual session storage
          this.clearSession(parseInt(subjectIdStr))
        }
      })
      
      if (hasChanges) {
        localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(cleanedData))
      }
    } catch (error) {
      console.warn('Failed to cleanup expired sessions:', error)
    }
  }

  /**
   * Check if a session should be considered expired locally (client-side check)
   */
  static isLocallyExpired(lastActivity: string): boolean {
    try {
      const lastActivityTime = new Date(lastActivity)
      const now = new Date()
      const timeDifferenceMinutes = (now.getTime() - lastActivityTime.getTime()) / (1000 * 60)
      
      return timeDifferenceMinutes > this.TIMEOUT_MINUTES
    } catch (error) {
      console.warn('Failed to check expiration:', error)
      return true // Assume expired if we can't parse the date
    }
  }

  /**
   * Get the localStorage key for a specific subject's session
   */
  private static getSessionKey(subjectId: number): string {
    return `${SESSION_STORAGE_KEY}-${subjectId}`
  }

  /**
   * Get all activity data from localStorage
   */
  private static getActivityData(): ActivityData {
    try {
      const stored = localStorage.getItem(ACTIVITY_STORAGE_KEY)
      return stored ? JSON.parse(stored) : {}
    } catch (error) {
      console.warn('Failed to parse activity data:', error)
      return {}
    }
  }
} 