import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'
import { Modal } from './Modal'
import { Button } from './primitives'

/** "Delete X?" with what goes with it; Cancel and the danger button lock while it runs. */
export function ConfirmDialog({ open, title, confirmLabel, busy, onCancel, onConfirm, icon = 'close', children }: {
  open: boolean
  title: string
  confirmLabel: string
  busy: boolean
  onCancel: () => void
  onConfirm: () => void
  icon?: IconName
  children: ReactNode
}) {
  return (
    <Modal open={open} onClose={() => !busy && onCancel()} labelledBy="confirm-title" small className="confirm-dialog">
      <span className="danger-icon"><Icon name={icon} /></span>
      <h2 id="confirm-title">{title}</h2>
      {children}
      <div className="modal-actions">
        <Button variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Button>
        <Button variant="danger" onClick={onConfirm} disabled={busy}>{busy ? 'Deleting…' : confirmLabel}</Button>
      </div>
    </Modal>
  )
}
