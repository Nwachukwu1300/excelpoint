import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useRef, useSyncExternalStore } from 'react'
import { spring } from '../lib/motion'
import { Icon } from './Icon'
import { IconButton } from './primitives'

type Toast = { id: number; tone: 'success' | 'error'; title: string; message: string }

let toasts: Toast[] = []
let nextId = 1
const listeners = new Set<() => void>()
const emit = () => listeners.forEach(l => l())

export function toast(tone: Toast['tone'], title: string, message = '') {
  toasts = [...toasts, { id: nextId++, tone, title, message }].slice(-3)
  emit()
}

function dismiss(id: number) {
  toasts = toasts.filter(t => t.id !== id)
  emit()
}

/** Disappears after 4s; hovering pauses the countdown (easyui VelocityToast). */
function ToastItem({ t }: { t: Toast }) {
  const remaining = useRef(4000)
  const started = useRef(0)
  const timer = useRef<number | undefined>(undefined)
  const start = () => { started.current = Date.now(); timer.current = window.setTimeout(() => dismiss(t.id), remaining.current) }
  const pause = () => { window.clearTimeout(timer.current); remaining.current -= Date.now() - started.current }
  useEffect(() => { start(); return () => window.clearTimeout(timer.current) }, [])

  return (
    <motion.div
      layout
      className={`toast toast--${t.tone}`}
      role={t.tone === 'error' ? 'alert' : 'status'}
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.12 } }}
      transition={spring.snappy}
      onMouseEnter={pause}
      onMouseLeave={start}
    >
      <span><Icon name={t.tone === 'success' ? 'check' : 'close'} size={15} /></span>
      <div>
        <strong>{t.title}</strong>
        {t.message && <p>{t.message}</p>}
      </div>
      <IconButton icon="close" label="Dismiss" onClick={() => dismiss(t.id)} />
    </motion.div>
  )
}

export function Toaster() {
  const items = useSyncExternalStore(
    l => { listeners.add(l); return () => listeners.delete(l) },
    () => toasts,
  )
  return (
    <div className="toast-stack">
      <AnimatePresence initial={false}>
        {items.map(t => <ToastItem key={t.id} t={t} />)}
      </AnimatePresence>
    </div>
  )
}
