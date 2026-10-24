import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useRef, useState, type ReactNode } from 'react'
import { popover } from '../lib/motion'
import { useDismiss } from '../lib/useDismiss'
import { IconButton } from './primitives'

/** A "…" button that opens a small list of actions. */
export function MoreMenu({ label, items }: { label: string; items: { label: string; danger?: boolean; onSelect: () => void; icon?: ReactNode }[] }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(ref, close, open)
  return (
    <div className="menu-wrap" ref={ref}>
      <IconButton icon="more" label={label} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(o => !o)} />
      <AnimatePresence>
        {open && (
          <motion.div className="dropdown row-menu" role="menu" {...popover}>
            <div className="dropdown-links">
              {items.map(item => (
                <button type="button" role="menuitem" key={item.label} className={item.danger ? 'danger' : ''} onClick={() => { close(); item.onSelect() }}>
                  {item.icon}{item.label}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
