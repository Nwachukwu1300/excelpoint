import type { ButtonHTMLAttributes, ReactNode } from 'react'
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

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo">
      <span className="logo-mark"><span>XP</span></span>
      {!compact && <span className="logo-word">ExcelPoint</span>}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <span className={`skeleton ${className}`.trim()} aria-hidden="true" />
}
