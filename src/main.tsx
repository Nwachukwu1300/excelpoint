/**
 * Main entry point for the Excelpoint chat widget.
 * 
 * This module initializes and renders a React-based chat widget that integrates
 * with Django templates. The widget provides AI-powered chat functionality
 * for educational content using RAG (Retrieval Augmented Generation).
 * 
 * Key features:
 * - React 18 with React Query for state management
 * - Automatic DOM detection and initialization
 * - Retry logic for container discovery
 * - Subject-specific chat context
 * - Error handling and logging
 * 
 * Usage:
 * Include a div with id="chat-widget-root" and data-subject-id attribute
 * in your Django template to automatically initialize the chat widget.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatWidget } from '@/components/chat/ChatWidget'

console.log('Chat widget: Script loaded!')

// Create a React Query client for data fetching and caching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 2,
    },
  },
})

/**
 * Initialize the chat widget by finding the container and rendering the React component.
 * 
 * This function looks for a DOM element with id="chat-widget-root" and extracts
 * the subject ID from data attributes. It then creates a React root and renders
 * the ChatWidget component with proper context providers.
 * 
 * @returns {boolean} True if initialization was successful, false otherwise
 */
function initializeChatWidget() {
  console.log('Chat widget: Looking for container...')
  
  // Look for chat widget container in the DOM
  const chatContainer = document.getElementById('chat-widget-root')
  console.log('Chat widget: Container element:', chatContainer)
  
  if (chatContainer) {
    console.log('Chat widget: Container found!')
    console.log('Chat widget: Container HTML:', chatContainer.outerHTML)
    
    // Get subject ID from data attribute
    const subjectId = chatContainer.dataset.subjectId
    console.log('Chat widget: Subject ID:', subjectId)
    console.log('Chat widget: All data attributes:', chatContainer.dataset)
    
    if (subjectId) {
      console.log('Chat widget: Initializing React component...')
      try {
        const root = ReactDOM.createRoot(chatContainer)
        root.render(
          <React.StrictMode>
            <QueryClientProvider client={queryClient}>
              <ChatWidget subjectId={parseInt(subjectId, 10)} />
            </QueryClientProvider>
          </React.StrictMode>,
        )
        console.log('Chat widget: React component rendered successfully!')
        return true // Success
      } catch (error) {
        console.error('Chat widget: Error rendering React component:', error)
        return false
      }
    } else {
      console.warn('Chat widget: subjectId not found in data attributes')
      return false
    }
  } else {
    console.warn('Chat widget: Container element #chat-widget-root not found in DOM')
    console.log('Chat widget: All elements with id:', document.querySelectorAll('[id]'))
    return false
  }
}

// Initialize the chat widget based on DOM readiness
if (document.readyState === 'loading') {
  // DOM is still loading, wait for it
  document.addEventListener('DOMContentLoaded', () => {
    console.log('Chat widget: DOM loaded, attempting initialization...')
    if (!initializeChatWidget()) {
      // If still not found, try again after a short delay
      setTimeout(() => {
        console.log('Chat widget: Retrying initialization after delay...')
        initializeChatWidget()
      }, 100)
    }
  })
} else {
  // DOM is already loaded
  console.log('Chat widget: DOM already loaded, attempting initialization...')
  if (!initializeChatWidget()) {
    // If not found, try again after a short delay
    setTimeout(() => {
      console.log('Chat widget: Retrying initialization after delay...')
      initializeChatWidget()
    }, 100)
  }
}

// Export for potential programmatic usage
export { ChatWidget, queryClient } 