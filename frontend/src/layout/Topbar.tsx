import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { useMatches, useNavigate } from 'react-router'
import { api, csrfToken, displayName, initials, type Me } from '../lib/api'
import { timeAgo } from '../lib/format'
import { ease, popover } from '../lib/motion'
import { useTheme } from '../lib/theme'
import { Icon } from '../ui/Icon'
import { Avatar, IconButton, Skeleton } from '../ui/primitives'
import { oldPages } from './nav'

type Notification = { id: number; kind: string; title: string; body: string; url: string; read: boolean; created_at: string }

/** Close a menu on outside press or Escape. */
function useDismiss(ref: RefObject<HTMLElement | null>, onClose: () => void, active: boolean) {
  useEffect(() => {
    if (!active) return
    const onDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) onClose() }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [ref, onClose, active])
}

function NotificationsMenu({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const list = useQuery({
    queryKey: ['notifications', 'menu'],
    queryFn: () => api<{ unread: number; results: Notification[] }>('/api/notifications/?limit=5'),
  })
  const markRead = useMutation({
    mutationFn: (ids?: number[]) => api('/api/notifications/read/', { method: 'POST', body: ids ? { ids } : {} }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })

  const open = async (n: Notification) => {
    if (!n.read) await markRead.mutateAsync([n.id]).catch(() => undefined) // still follow the link if this fails
    onClose()
    if (n.url.startsWith('/app/')) navigate(n.url.slice('/app'.length))
    else if (n.url.startsWith('/')) location.assign(n.url)
  }

  const items = list.data?.results ?? []
  return (
    <motion.div className="dropdown dropdown--notifications" {...popover} role="dialog" aria-label="Notifications">
      <div className="dropdown-head">
        <strong>Notifications</strong>
        <button type="button" disabled={!list.data?.unread || markRead.isPending} onClick={() => markRead.mutate(undefined)}>
          Mark all as read
        </button>
      </div>
      <div className="dropdown-list">
        {list.isPending && (
          <div className="dropdown-loading" aria-label="Loading notifications">
            {[0, 1, 2].map(i => (
              <div className="skeleton-list-row" key={i}>
                <Skeleton className="skeleton-avatar" />
                <div><Skeleton /><Skeleton /></div>
              </div>
            ))}
          </div>
        )}
        {list.isError && <p className="dropdown-empty">Couldn’t load notifications. Try again in a moment.</p>}
        {list.isSuccess && items.length === 0 && <p className="dropdown-empty">You’re all caught up.</p>}
        {items.map(n => {
          const failed = /fail|couldn/i.test(n.kind + n.title)
          const review = n.kind.includes('review')
          return (
            <button type="button" key={n.id} className={`notification ${n.read ? '' : 'is-new'}`} onClick={() => open(n)}>
              <span className={`notification-icon ${failed ? 'failed' : n.kind.includes('ready') ? 'ai-bg' : ''}`}>
                <Icon name={failed ? 'close' : review ? 'repeat' : 'sparkles'} size={16} />
              </span>
              <div>
                <strong>{n.title}</strong>
                {n.body && <p>{n.body}</p>}
                <small>{timeAgo(n.created_at)}</small>
              </div>
            </button>
          )
        })}
      </div>
      <a className="dropdown-footer" href={oldPages.notifications}>View all notifications</a>
    </motion.div>
  )
}

function AccountMenu({ me }: { me?: Me }) {
  const name = me ? displayName(me) : ''
  return (
    <motion.div className="dropdown dropdown--account" {...popover}>
      <div className="account-summary">
        <Avatar initials={initials(name)} />
        <div>
          <strong>{name}</strong>
          <span>{me?.email || me?.username}</span>
        </div>
      </div>
      <div className="dropdown-links">
        <a href={oldPages.settings}><Icon name="settings" />Settings</a>
        <a href={oldPages.password}><Icon name="lock" />Change password</a>
        {/* Django's logout only accepts POST with the CSRF token */}
        <form method="post" action={oldPages.logout}>
          <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
          <button type="submit" className="logout"><Icon name="logout" />Log out</button>
        </form>
      </div>
    </motion.div>
  )
}

function ThemeToggle() {
  const { resolved, setTheme } = useTheme()
  const dark = resolved === 'dark'
  return (
    <button
      type="button"
      className="icon-button"
      aria-label={dark ? 'Use light theme' : 'Use dark theme'}
      title={dark ? 'Use light theme' : 'Use dark theme'}
      onClick={() => setTheme(dark ? 'light' : 'dark')}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={resolved}
          className="theme-icon"
          initial={{ opacity: 0, rotate: -60, scale: 0.8 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={{ opacity: 0, rotate: 60, scale: 0.8 }}
          transition={ease.fast}
        >
          <Icon name={dark ? 'sun' : 'moon'} />
        </motion.span>
      </AnimatePresence>
    </button>
  )
}

export function Topbar({ me }: { me?: Me }) {
  const [menu, setMenu] = useState<'notifications' | 'account' | null>(null)
  const notificationsRef = useRef<HTMLDivElement>(null)
  const accountRef = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setMenu(null), [])
  useDismiss(menu === 'notifications' ? notificationsRef : accountRef, close, menu !== null)

  const title = useMatches().map(m => (m.handle as { title?: string } | undefined)?.title).filter(Boolean).at(-1)
  const unread = me?.unread_notifications ?? 0

  return (
    <header className="topbar">
      <div className="breadcrumb">
        <span>Workspace</span>
        <Icon name="chevronRight" size={14} />
        <strong>{title}</strong>
      </div>
      <div className="top-actions">
        <ThemeToggle />
        <div className="menu-wrap" ref={notificationsRef}>
          <IconButton
            icon="bell"
            label={unread ? `Notifications, ${unread} unread` : 'Notifications'}
            aria-expanded={menu === 'notifications'}
            onClick={() => setMenu(menu === 'notifications' ? null : 'notifications')}
          />
          {unread > 0 && <span className="unread">{unread > 9 ? '9+' : unread}</span>}
          <AnimatePresence>{menu === 'notifications' && <NotificationsMenu onClose={close} />}</AnimatePresence>
        </div>
        <div className="menu-wrap" ref={accountRef}>
          <button
            type="button"
            className="avatar-button"
            aria-label="Open account menu"
            aria-expanded={menu === 'account'}
            onClick={() => setMenu(menu === 'account' ? null : 'account')}
          >
            {me ? <Avatar small initials={initials(displayName(me))} /> : <Skeleton className="skeleton-avatar" />}
            <Icon name="chevronDown" size={14} />
          </button>
          <AnimatePresence>{menu === 'account' && <AccountMenu me={me} />}</AnimatePresence>
        </div>
      </div>
    </header>
  )
}
