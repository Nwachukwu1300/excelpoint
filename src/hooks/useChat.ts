import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatApi } from '@/services/chatApi'
import { SessionStorageManager } from '@/utils/sessionStorage'
import type { ChatMessage, ChatSession, SendMessageRequest } from '@/types/chat'

// Utility function for throttling
const throttle = <T extends (...args: any[]) => any>(
  func: T,
  delay: number
): ((...args: Parameters<T>) => void) => {
  let timeoutId: NodeJS.Timeout | null = null
  let lastExecTime = 0
  
  return (...args: Parameters<T>) => {
    const currentTime = Date.now()
    
    if (currentTime - lastExecTime > delay) {
      func(...args)
      lastExecTime = currentTime
    } else {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      timeoutId = setTimeout(() => {
        func(...args)
        lastExecTime = Date.now()
      }, delay - (currentTime - lastExecTime))
    }
  }
}

// Query keys for React Query caching
export const chatQueryKeys = {
  messages: (subjectId: number, sessionId?: number) => 
    ['chat', 'messages', subjectId, sessionId],
  session: (subjectId: number) => 
    ['chat', 'session', subjectId],
  stats: (subjectId: number) => 
    ['chat', 'stats', subjectId],
}

// Custom hook for managing chat messages and sessions with persistence
export const useChatMessages = (subjectId: number, selectedSessionId?: number) => {
  const queryClient = useQueryClient()
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null)
  const [isValidatingSession, setIsValidatingSession] = useState(false)

  // Session validation and restoration logic
  const validateAndRestoreSession = useCallback(async () => {
    try {
      const storedSession = SessionStorageManager.getStoredSession(subjectId)
      
      if (!storedSession || !storedSession.isValid) {
        // No valid stored session, will create new one
        return null
      }

      setIsValidatingSession(true)
      
      // Add timeout to prevent hanging
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Session validation timeout')), 10000) // 10 second timeout
      })
      
      const validationPromise = chatApi.validateSession(subjectId, storedSession.sessionId)
      
      const validation = await Promise.race([validationPromise, timeoutPromise]) as Awaited<ReturnType<typeof chatApi.validateSession>>
      
      if (validation.valid && validation.session) {
        // Session is still valid, restore it
        SessionStorageManager.storeSession(subjectId, validation.session)
        setCurrentSession(validation.session)
        return validation.session
      } else {
        // Session is invalid, clear storage
        SessionStorageManager.clearSession(subjectId)
        return null
      }
    } catch (error) {
      console.warn('Session validation failed:', error)
      SessionStorageManager.markSessionInvalid(subjectId)
      return null
    } finally {
      setIsValidatingSession(false)
    }
  }, [subjectId])

  // Get or create chat session with persistence
  const { 
    data: session, 
    isLoading: isSessionLoading,
    error: sessionError
  } = useQuery({
    queryKey: selectedSessionId 
      ? ['chat', 'session', subjectId, selectedSessionId] 
      : chatQueryKeys.session(subjectId),
    queryFn: async () => {
      // If a specific session is selected, try to get it
      if (selectedSessionId) {
        try {
          const sessionData = await chatApi.validateSession(subjectId, selectedSessionId)
          if (sessionData.valid && sessionData.session) {
            return sessionData.session
          } else {
            throw new Error('Selected session is no longer valid')
          }
        } catch (error) {
          console.warn('Failed to load selected session:', error)
          throw error
        }
      }

      // Default session logic for new chats
      try {
        // First try to restore an existing session (with timeout)
        const restoredSession = await validateAndRestoreSession()
        if (restoredSession) {
          return restoredSession
        }
      } catch (error) {
        console.warn('Session restoration failed, creating new session:', error)
        // Continue to create new session
      }
      
      // No valid session, create a new one
      const newSession = await chatApi.getOrCreateSession(subjectId)
      SessionStorageManager.storeSession(subjectId, newSession)
      return newSession
    },
    onSuccess: (data) => {
      setCurrentSession(data)
      SessionStorageManager.storeSession(subjectId, data)
    },
    onError: (error) => {
      console.error('Failed to initialize chat session:', error)
      // Clear any stored session on fatal error
      SessionStorageManager.clearSession(subjectId)
    },
    staleTime: 1000 * 60 * 5, // 5 minutes (shorter due to timeout logic)
    retry: (failureCount, error) => {
      // Only retry network errors, not validation timeouts
      const errorMessage = error instanceof Error ? error.message : String(error)
      return failureCount < 2 && !errorMessage.includes('timeout')
    },
    retryDelay: 1000, // 1 second between retries
  })

  // Get messages for the current session
  const { 
    data: messages = [], 
    isLoading: isMessagesLoading 
  } = useQuery({
    queryKey: chatQueryKeys.messages(subjectId, currentSession?.id),
    queryFn: () => currentSession 
      ? chatApi.getMessages(subjectId, currentSession.id)
      : [],
    enabled: !!currentSession,
    staleTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 30000, // Refetch every 30 seconds for real-time updates
  })

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (data: SendMessageRequest) => 
      chatApi.sendMessage(subjectId, data),
    onMutate: async ({ content }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: chatQueryKeys.messages(subjectId, currentSession?.id)
      })

      // Snapshot the previous messages
      const previousMessages = queryClient.getQueryData<ChatMessage[]>(
        chatQueryKeys.messages(subjectId, currentSession?.id)
      ) || []

      // Optimistically update the messages
      const optimisticMessage: ChatMessage = {
        id: Date.now(), // Temporary ID
        content,
        role: 'user',
        timestamp: new Date().toISOString(),
        session: currentSession?.id || 0,
      }

      queryClient.setQueryData(
        chatQueryKeys.messages(subjectId, currentSession?.id),
        [...previousMessages, optimisticMessage]
      )

      return { previousMessages }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousMessages) {
        queryClient.setQueryData(
          chatQueryKeys.messages(subjectId, currentSession?.id),
          context.previousMessages
        )
      }
    },
    onSuccess: (data) => {
      // Update with actual server response
      queryClient.setQueryData(
        chatQueryKeys.messages(subjectId, currentSession?.id),
        (oldMessages: ChatMessage[] = []) => {
          // Remove the optimistic message and add the real ones
          const withoutOptimistic = oldMessages.filter(msg => msg.id < 1000000000000)
          return [...withoutOptimistic, data.user_message, data.assistant_message]
        }
      )

      // Update session if needed
      if (data.session) {
        setCurrentSession(data.session)
        queryClient.setQueryData(
          chatQueryKeys.session(subjectId),
          data.session
        )
      }
    },
  })

  // Send a message with activity tracking
  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    const messageData: SendMessageRequest = {
      content: content.trim(),
      session_id: currentSession?.id,
    }

    try {
      const result = await sendMessageMutation.mutateAsync(messageData)
      
      // Update activity timestamp on successful message send
      SessionStorageManager.updateActivity(subjectId)
      
      return result
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  }

  // Cleanup effect for expired sessions
  useEffect(() => {
    const cleanup = () => {
      SessionStorageManager.cleanupExpiredSessions()
    }
    
    // Run cleanup on mount and when subject changes
    cleanup()
    
    // Set up periodic cleanup (every 5 minutes)
    const cleanupInterval = setInterval(cleanup, 5 * 60 * 1000)
    
    return () => {
      clearInterval(cleanupInterval)
    }
  }, [subjectId])

  // Activity tracking effect
  useEffect(() => {
    if (currentSession) {
      const trackActivity = () => {
        SessionStorageManager.updateActivity(subjectId)
      }
      
      // Track user activity (mouse moves, clicks, keystrokes)
      const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart']
      const throttledTrackActivity = throttle(trackActivity, 30000) // Throttle to once per 30 seconds
      
      events.forEach(event => {
        document.addEventListener(event, throttledTrackActivity, { passive: true })
      })
      
      return () => {
        events.forEach(event => {
          document.removeEventListener(event, throttledTrackActivity)
        })
      }
    }
  }, [currentSession, subjectId])

  return {
    // Data
    messages,
    session: currentSession,
    
    // Loading states
    isLoading: isSessionLoading || isMessagesLoading || isValidatingSession,
    isSending: sendMessageMutation.isPending,
    isValidatingSession,
    
    // Actions
    sendMessage,
    
    // Error states
    error: sessionError || sendMessageMutation.error,
    isError: !!sessionError || sendMessageMutation.isError,
  }
}

// Hook for chat statistics
export const useChatStats = (subjectId: number) => {
  return useQuery({
    queryKey: chatQueryKeys.stats(subjectId),
    queryFn: () => chatApi.getStats(subjectId),
    staleTime: 1000 * 60 * 10, // 10 minutes
    retry: 1,
  })
}

// Hook for managing chat widget state
export const useChatWidget = (initialState: 'collapsed' | 'expanded' | 'fullscreen' = 'collapsed') => {
  const [widgetState, setWidgetState] = useState<'collapsed' | 'expanded' | 'fullscreen'>(initialState)
  const [hasNewMessages, setHasNewMessages] = useState(false)

  const openChat = () => {
    setWidgetState('expanded')
    setHasNewMessages(false)
  }

  const closeChat = () => {
    setWidgetState('collapsed')
  }

  const toggleFullscreen = () => {
    setWidgetState(prev => prev === 'fullscreen' ? 'expanded' : 'fullscreen')
  }

  const markAsRead = () => {
    setHasNewMessages(false)
  }

  const markAsUnread = () => {
    setHasNewMessages(true)
  }

  return {
    // State
    widgetState,
    hasNewMessages,
    isCollapsed: widgetState === 'collapsed',
    isExpanded: widgetState === 'expanded',
    isFullscreen: widgetState === 'fullscreen',
    
    // Actions
    openChat,
    closeChat,
    toggleFullscreen,
    markAsRead,
    markAsUnread,
    setWidgetState,
  }
} 