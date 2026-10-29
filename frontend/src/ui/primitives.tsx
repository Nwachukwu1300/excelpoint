import excelpointIcon from '../assets/excelpoint-icon.webp'
import xpIcon from '../assets/xp-icon.webp'
import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react'
import { CountUp } from './CountUp'
import { Icon, type IconName } from './Icon'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'ai'

/** Class string for a <Link> or <a> styled as a button. */
export const buttonClass = (variant: ButtonVariant = 'primary', extra = '') => `button button--${variant} ${extra}`.trim()

export function Button({
  children, variant = 'primary', icon, className = '', type = 'button', ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; icon?: IconName }) {
  return (
    <button type={type} className={buttonClass(variant, className)} {...props}>
      {icon && <Icon name={icon} />}
      {children}
    </button>
  )
}

export function IconButton({
  icon, label, className = '', ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: IconName; label: string }) {
  return (
    <button type="button" aria-label={label} title={label} className={`icon-button ${className}`.trim()} {...props}>
      <Icon name={icon} />
    </button>
  )
}

export type Tone = 'neutral' | 'primary' | 'ai' | 'success' | 'warning' | 'danger'

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

export function Avatar({ initials, small = false }: { initials: string; small?: boolean }) {
  return <span className={`avatar ${small ? 'avatar--small' : ''}`} aria-hidden="true">{initials}</span>
}

/** XP, the AI study assistant: its 3D icon wherever XP speaks or works. */
export function XpAvatar({ small = false }: { small?: boolean }) {
  return <span className={`xp-avatar ${small ? 'xp-avatar--small' : ''}`.trim()}><img src={xpIcon} alt="" /></span>
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo">
      <img className="logo-mark" src={excelpointIcon} alt="" width={32} height={32} />
      {!compact && <span className="logo-word">Excel<b>P</b>oint</span>}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <span className={`skeleton ${className}`.trim()} aria-hidden="true" />
}

export type MaterialStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
const STATUS: Record<MaterialStatus, { label: string; tone: Tone }> = {
  PENDING: { label: 'Pending', tone: 'warning' },
  PROCESSING: { label: 'Processing', tone: 'primary' },
  COMPLETED: { label: 'Ready', tone: 'success' },
  FAILED: { label: 'Failed', tone: 'danger' },
}

export function StatusChip({ status }: { status: MaterialStatus }) {
  const { label, tone } = STATUS[status]
  return <Badge tone={tone}><span className="status-dot" />{label}</Badge>
}

/** Determinate when `value` is given; otherwise an indeterminate sweep (processing has no real %). */
export function ProgressBar({ value, label }: { value?: number; label: string }) {
  return (
    <div className={`progress-track ${value === undefined ? 'is-indeterminate' : ''}`} role="progressbar" aria-label={label}
      aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <span style={value === undefined ? undefined : { width: `${value}%` }} />
    </div>
  )
}

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
