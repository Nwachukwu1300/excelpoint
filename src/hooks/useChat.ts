import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatApi } from '@/services/chatApi'
import type { ChatMessage, ChatSession, SendMessageRequest } from '@/types/chat'

// Query keys for React Query caching
export const chatQueryKeys = {
  messages: (subjectId: number, sessionId?: number) => 
    ['chat', 'messages', subjectId, sessionId],
  session: (subjectId: number) => 
    ['chat', 'session', subjectId],
  stats: (subjectId: number) => 
    ['chat', 'stats', subjectId],
}

// Custom hook for managing chat messages and sessions
export const useChatMessages = (subjectId: number) => {
  const queryClient = useQueryClient()
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null)

  // Get or create chat session
  const { 
    data: session, 
    isLoading: isSessionLoading 
  } = useQuery({
    queryKey: chatQueryKeys.session(subjectId),
    queryFn: () => chatApi.getOrCreateSession(subjectId),
    onSuccess: (data) => {
      setCurrentSession(data)
    },
    staleTime: 1000 * 60 * 30, // 30 minutes
    retry: 2,
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

  // Send a message
  const sendMessage = async (content: string) => {
    if (!content.trim()) return

    const messageData: SendMessageRequest = {
      content: content.trim(),
      session_id: currentSession?.id,
    }

    return sendMessageMutation.mutateAsync(messageData)
  }

  return {
    // Data
    messages,
    session: currentSession,
    
    // Loading states
    isLoading: isSessionLoading || isMessagesLoading,
    isSending: sendMessageMutation.isPending,
    
    // Actions
    sendMessage,
    
    // Error states
    error: sendMessageMutation.error,
    isError: sendMessageMutation.isError,
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