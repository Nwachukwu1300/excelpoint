import React from 'react'
import styled, { keyframes } from 'styled-components'
import { Brain } from 'lucide-react'

// Animations
const bounce = keyframes`
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
`

const pulse = keyframes`
  0%, 100% {
    opacity: 0.4;
  }
  50% {
    opacity: 1;
  }
`

const shimmer = keyframes`
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
`

// Styled components
const IndicatorContainer = styled.div`
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 18px;
  margin: 8px 16px;
  max-width: 200px;
  gap: 8px;
  animation: ${pulse} 2s ease-in-out infinite;
`

const IconContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  flex-shrink: 0;
`

const DotsContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
`

const Dot = styled.div<{ delay: number }>`
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6b7280;
  animation: ${bounce} 1.4s ease-in-out infinite;
  animation-delay: ${props => props.delay}s;
`

const TypingText = styled.div`
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
  letter-spacing: 0.025em;
`

const ThinkingContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(
    90deg,
    #f3f4f6 0%,
    #e5e7eb 50%,
    #f3f4f6 100%
  );
  background-size: 200px 100%;
  animation: ${shimmer} 1.5s ease-in-out infinite;
  border-radius: 12px;
  padding: 8px 12px;
  margin: 8px 16px;
  max-width: 160px;
`

const ThinkingText = styled.div`
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
`

interface TypingIndicatorProps {
  variant?: 'typing' | 'thinking'
  text?: string
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ 
  variant = 'typing',
  text
}) => {
  if (variant === 'thinking') {
    return (
      <ThinkingContainer role="status" aria-label="AI is thinking">
        <IconContainer>
          <Brain size={14} />
        </IconContainer>
        <ThinkingText>
          {text || 'Thinking...'}
        </ThinkingText>
      </ThinkingContainer>
    )
  }

  return (
    <IndicatorContainer role="status" aria-label="AI is typing">
      <IconContainer>
        <Brain size={14} />
      </IconContainer>
      <TypingText>
        {text || 'XP is typing'}
      </TypingText>
      <DotsContainer>
        <Dot delay={0} />
        <Dot delay={0.2} />
        <Dot delay={0.4} />
      </DotsContainer>
    </IndicatorContainer>
  )
}

export default TypingIndicator 