# Chat Session Persistence & History Management Prompt

## Problem Description
The XP chatbot currently starts a new session every time a user leaves and returns to the chat, causing loss of conversation context and poor user experience. We need to implement intelligent session management with persistence and history.

## Current Issues
- Chat creates new session on every page load/return
- No session timeout logic or continuity
- Missing chat history functionality  
- Lost conversation context disrupts user flow
- No visual indication of session status

## Required Solution

### Core Requirements
1. **Session Timeout Logic**: Only create new chat session after 5 minutes of user inactivity
2. **Session Persistence**: Maintain and resume active session when user returns within 5-minute window
3. **Chat History**: Display last 30 previous chat sessions with easy access
4. **Session Management**: Proper cleanup, organization, and database optimization

### Technical Implementation Needed
- Frontend session timeout tracking with localStorage/sessionStorage
- Backend session validation and timeout handling in Django
- Chat history sidebar/dropdown component in React
- Session persistence across page refreshes and navigation
- Database optimization for session storage and retrieval
- Real-time session status indicators in UI

### User Experience Goals
- Seamless conversation continuation within 5-minute window
- Easy access to recent chat history (last 30 sessions)
- Clear visual indication of session status (active/new/resumed)
- Automatic session management without user intervention
- Smooth transitions between sessions

## Instructions for Implementation

### Step 1: Use Taskmaster for Project Management
1. **Initialize/Update Taskmaster**: Use `mcp_task-master-ai_add_task` to create a comprehensive task for "Implement Chat Session Persistence and History Management"
2. **Break Down the Work**: Use `mcp_task-master-ai_expand_task` with research flag to generate detailed subtasks covering:
   - Frontend session timeout implementation
   - Backend session management API updates
   - Chat history UI component development
   - Database schema modifications if needed
   - Session persistence logic
   - Testing and validation

3. **Track Progress**: Use Taskmaster's status management (`mcp_task-master-ai_set_task_status`) to track each subtask as you work through them

4. **Update Tasks**: Use `mcp_task-master-ai_update_subtask` to log progress, findings, and implementation decisions

### Step 2: Research Current Implementation
Before starting, research the current chat system:
- Review `subjects/models.py` for ChatSession and ChatMessage models
- Examine `subjects/views.py` for current session creation logic
- Check `src/services/chatApi.ts` for frontend session handling
- Understand `src/hooks/useChat.ts` current state management

### Step 3: Implementation Areas to Address

#### Frontend Changes (src/)
- Update `useChat.ts` hook with session timeout logic
- Modify `ChatWidget.tsx` to handle session persistence
- Create `ChatHistory.tsx` component for displaying past sessions
- Add session status indicators and transitions
- Implement localStorage for session timeout tracking

#### Backend Changes (subjects/)
- Update ChatSession model with timeout and status fields
- Modify session creation/retrieval logic in views
- Add session cleanup management command
- Implement session validation middleware
- Create chat history API endpoints

#### Database Considerations
- Add session timeout tracking fields
- Implement session cleanup for old data
- Optimize queries for chat history retrieval
- Consider indexing for performance

### Step 4: Validation Requirements
- Test session continuation within 5-minute window
- Verify new session creation after timeout
- Validate chat history display (30 sessions max)
- Test session persistence across page refreshes
- Verify proper cleanup of old sessions

### Step 5: User Experience Testing
- Smooth conversation flow when returning quickly
- Clear session status communication
- Intuitive chat history navigation
- Proper handling of edge cases (network issues, server restarts)

## Success Criteria
- Sessions persist for 5 minutes after last activity
- New sessions only created after timeout or explicit user action
- Chat history shows last 30 sessions with easy access
- No conversation context loss within timeout window
- Clean, intuitive UI for session management

## Notes for Implementation
- Current project uses Django + React with TypeScript
- RAG service has 60-second timeout configuration
- Existing chat system is in subjects/ Django app
- Frontend uses Vite build system
- Consider performance impact of session tracking
- Ensure proper error handling for session edge cases

Use Taskmaster throughout the implementation to maintain organized development workflow and track all progress systematically. 