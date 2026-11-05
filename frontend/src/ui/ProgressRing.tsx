import type { CSSProperties } from 'react'
import { CountUp } from './CountUp'

/** Score ring: fills from empty and counts up on first show (both skip with reduced motion). */
export function ProgressRing({ value, label }: { value: number; label: string }) {
  return (
    <div className="progress-ring" style={{ '--progress': `${value * 3.6}deg` } as CSSProperties} role="img" aria-label={`${label} ${value}%`}>
      <div aria-hidden="true">
        <strong><CountUp value={value} />%</strong>
        <span>{label}</span>
      </div>
    </div>
  )
}
