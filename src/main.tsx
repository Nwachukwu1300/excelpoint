import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatWidget } from '@/components/chat/ChatWidget'

console.log('Chat widget: Script loaded!')

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 2,
    },
  },
})

// Initialize chat widget with retry logic
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

// Try to initialize immediately
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