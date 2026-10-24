import { Icon } from './Icon'

export function CitationChip({ label, onClick, active = false }: { label: string; onClick?: () => void; active?: boolean }) {
  return (
    <button type="button" className={`citation-chip ${active ? 'is-active' : ''}`} onClick={onClick} title={`Show source: ${label}`}>
      <Icon name="file" size={14} />
      <span>{label}</span>
      <Icon name="chevronRight" size={13} />
    </button>
  )
}

export function VerificationBadge({ verified }: { verified: boolean }) {
  return (
    <span className={`verification ${verified ? 'is-verified' : 'is-unverified'}`}>
      {verified ? <Icon name="check" size={13} /> : <span aria-hidden="true">⚠</span>}
      {verified ? 'Verified' : 'Not fully verified'}
    </span>
  )
}

export const confidenceLevel = (value: number) => (value >= 0.8 ? 'High' : value >= 0.55 ? 'Moderate' : 'Low')

export function ConfidencePill({ value }: { value: number }) {
  const level = confidenceLevel(value)
  return <span className={`confidence confidence--${level.toLowerCase()}`}>{level} · {value.toFixed(2)}</span>
}
