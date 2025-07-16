import axios, { AxiosResponse } from 'axios'
import type {
  ChatMessage,
  ChatSession,
  SendMessageRequest,
  SendMessageResponse,
  ChatStats,
  ApiError
} from '@/types/chat'

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // Increased to 60 seconds for RAG processing
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add CSRF token to requests (Django requirement)
api.interceptors.request.use((config) => {
  const csrfToken = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      const apiError: ApiError = {
        message: error.response.data?.detail || error.response.data?.message || 'An error occurred',
        status: error.response.status,
        detail: error.response.data?.detail
      }
      throw apiError
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('Network error. Please check your connection.')
    } else {
      // Something else happened
      throw new Error('An unexpected error occurred')
    }
  }
)

// Chat API functions
export const chatApi = {
  // Get or create chat session for a subject
  getOrCreateSession: async (subjectId: number): Promise<ChatSession> => {
    const response: AxiosResponse<ChatSession> = await api.post(
      `/subjects/${subjectId}/chat/session/`
    )
    return response.data
  },

  // Get messages for a session
  getMessages: async (subjectId: number, sessionId?: number): Promise<ChatMessage[]> => {
    const url = sessionId 
      ? `/subjects/${subjectId}/chat/messages/?session_id=${sessionId}`
      : `/subjects/${subjectId}/chat/messages/`
    
    const response: AxiosResponse<{ 
      session: ChatSession | null
      messages: ChatMessage[]
      total_messages: number
      has_more: boolean 
    }> = await api.get(url)
    return response.data.messages || []
  },

  // Send a message
  sendMessage: async (subjectId: number, data: SendMessageRequest): Promise<SendMessageResponse> => {
    const response: AxiosResponse<SendMessageResponse> = await api.post(
      `/subjects/${subjectId}/chat/messages/`,
      { message: data.content }  // Django expects 'message' field, not 'content'
    )
    return response.data
  },

  // Get chat statistics
  getStats: async (subjectId: number): Promise<ChatStats> => {
    const response: AxiosResponse<ChatStats> = await api.get(
      `/subjects/${subjectId}/chat/stats/`
    )
    return response.data
  },

  // Get session details
  getSession: async (sessionId: number): Promise<ChatSession> => {
    const response: AxiosResponse<ChatSession> = await api.get(
      `/chat/sessions/${sessionId}/`
    )
    return response.data
  },

  // Get session history for a subject with filtering options
  getSessionHistory: async (subjectId: number, options?: {
    limit?: number
    status?: 'active' | 'expired' | 'archived'
    includeInactive?: boolean
  }): Promise<{
    sessions: ChatSession[]
    metadata: {
      total_sessions: number
      active_sessions: number
      returned_count: number
      max_limit: number
    }
  }> => {
    const params = new URLSearchParams()
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.status) params.append('status', options.status)
    if (options?.includeInactive !== undefined) {
      params.append('include_inactive', options.includeInactive.toString())
    }
    
    const queryString = params.toString()
    const url = `/subjects/${subjectId}/chat/sessions/${queryString ? '?' + queryString : ''}`
    
    const response = await api.get(url)
    return response.data
  },

  // Validate session
  validateSession: async (subjectId: number, sessionId: number): Promise<{
    valid: boolean
    session: ChatSession | null
    message: string
  }> => {
    const response: AxiosResponse<{
      valid: boolean
      session: ChatSession | null
      message: string
    }> = await api.get(
      `/subjects/${subjectId}/chat/sessions/${sessionId}/validate/`
    )
    return response.data
  },

  // Deactivate session
  deactivateSession: async (sessionId: number): Promise<ChatSession> => {
    const response: AxiosResponse<ChatSession> = await api.patch(
      `/chat/sessions/${sessionId}/`,
      { is_active: false }
    )
    return response.data
  }
}

export default chatApi 