import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Centered dialog (bottom sheet on phones). Escape or a press on the backdrop closes it,
 * focus stays inside while open and returns to the trigger afterwards.
 */
export function Modal({ open, onClose, labelledBy, small = false, className = '', children }: {
  open: boolean
  onClose: () => void
  labelledBy: string
  small?: boolean
  className?: string
  children: ReactNode
}) {
  const panel = useRef<HTMLElement>(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose // latest handler without re-running the focus effect on every render

  useEffect(() => {
    if (!open) return
    const opener = document.activeElement as HTMLElement | null
    const el = panel.current
    // autoFocus inside the dialog wins; otherwise focus the first control
    if (el && !el.contains(document.activeElement)) el.querySelector<HTMLElement>(FOCUSABLE)?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopPropagation(); closeRef.current(); return }
      if (e.key !== 'Tab' || !el) return
      const items = [...el.querySelectorAll<HTMLElement>(FOCUSABLE)]
      if (!items.length) return
      const first = items[0]!, last = items.at(-1)!
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      opener?.focus?.()
    }
  }, [open])

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="modal-backdrop"
          role="presentation"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          // detail 2: the second click of the double click that opened it, not a request to close
          onMouseDown={e => { if (e.target === e.currentTarget && e.detail <= 1) onClose() }}
        >
          <motion.section
            ref={panel}
            className={`modal ${small ? 'modal--small' : ''} ${className}`.trim()}
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            initial={{ opacity: 0, y: 12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98, transition: { duration: 0.12 } }}
            transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.6 }}
          >
            {children}
          </motion.section>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
