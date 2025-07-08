import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatWidget } from '@/components/chat/ChatWidget'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 2,
    },
  },
})

// Initialize chat widget when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  console.log('Chat widget: DOM loaded, looking for container...')
  
  // Look for chat widget container in the DOM
  const chatContainer = document.getElementById('chat-widget-root')
  
  if (chatContainer) {
    console.log('Chat widget: Container found!')
    
    // Get subject ID from data attribute
    const subjectId = chatContainer.dataset.subjectId
    console.log('Chat widget: Subject ID:', subjectId)
    
    if (subjectId) {
      console.log('Chat widget: Initializing React component...')
      const root = ReactDOM.createRoot(chatContainer)
      root.render(
        <React.StrictMode>
          <QueryClientProvider client={queryClient}>
            <ChatWidget subjectId={parseInt(subjectId, 10)} />
          </QueryClientProvider>
        </React.StrictMode>,
      )
      console.log('Chat widget: React component rendered!')
    } else {
      console.warn('Chat widget: subjectId not found in data attributes')
    }
  } else {
    console.warn('Chat widget: Container element #chat-widget-root not found in DOM')
  }
})

// Export for potential programmatic usage
export { ChatWidget, queryClient } 