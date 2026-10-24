import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { ScrollRestoration, useLocation, useOutlet } from 'react-router'
import { ApiError, loginUrl, useMe } from '../lib/api'
import { Toaster } from '../ui/Toast'
import { MobileNav } from './MobileNav'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

const COLLAPSED_KEY = 'xp-sidebar-collapsed'

function readCollapsed() {
  try { return localStorage.getItem(COLLAPSED_KEY) === '1' } catch { return false }
}

/** Page change: a short fade and 4px rise on the content only; the shell stays still. */
function AnimatedOutlet() {
  const outlet = useOutlet()
  const { pathname } = useLocation()
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, transition: { duration: 0.08 } }}
        transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
      >
        {outlet}
      </motion.div>
    </AnimatePresence>
  )
}

export function Shell() {
  const me = useMe()
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const signedOut = me.error instanceof ApiError && me.error.status === 403

  useEffect(() => { if (signedOut) location.assign(loginUrl()) }, [signedOut])

  const toggle = () => {
    setCollapsed(c => {
      try { localStorage.setItem(COLLAPSED_KEY, c ? '0' : '1') } catch { /* not persisted */ }
      return !c
    })
  }

  if (signedOut) return null
  return (
    <div className="app-shell">
      <Sidebar me={me.data} collapsed={collapsed} onToggle={toggle} />
      <div className={`app-main ${collapsed ? 'sidebar-collapsed' : ''}`}>
        <Topbar me={me.data} />
        <main><AnimatedOutlet /></main>
      </div>
      <MobileNav me={me.data} />
      <Toaster />
      <ScrollRestoration />
    </div>
  )
}
