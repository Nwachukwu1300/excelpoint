import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useRef, useState } from 'react'
import { Link, useMatches, useNavigate } from 'react-router'
import { api, displayName, initials, type Me } from '../lib/api'
import { timeAgo } from '../lib/format'
import { ease, popover } from '../lib/motion'
import { useTheme } from '../lib/theme'
import { useDismiss } from '../lib/useDismiss'
import { Icon } from '../ui/Icon'
import { Avatar, IconButton, Skeleton } from '../ui/primitives'
import { followNotification, notificationLook, type Notification } from '../features/account/notifications'

export type RouteHandle = { title: string | ((params: Record<string, string | undefined>, me?: Me) => string); fullBleed?: boolean; focus?: boolean }


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
    followNotification(n, navigate)
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
          const look = notificationLook(n)
          return (
            <button type="button" key={n.id} className={`notification ${n.read ? '' : 'is-new'}`} onClick={() => open(n)}>
              <span className={`notification-icon ${look.className}`}>
                <Icon name={look.icon} size={16} />
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
      <Link className="dropdown-footer" to="/notifications" onClick={onClose}>View all notifications</Link>
    </motion.div>
  )
}

function AccountMenu({ me, onClose }: { me?: Me; onClose: () => void }) {
  const name = me ? displayName(me) : ''
  const signOut = async () => {
    await api('/api/auth/logout/', { method: 'POST' }).catch(() => undefined)
    location.assign('/app/welcome') // full load clears everything cached for this user
  }
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
        <Link to="/settings" onClick={onClose}><Icon name="settings" />Settings</Link>
        <Link to="/settings/password" onClick={onClose}><Icon name="lock" />Change password</Link>
        <button type="button" className="logout" onClick={signOut}><Icon name="logout" />Log out</button>
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

  // A route's title is a string, or computed from its URL params and the signed-in user's data.
  const match = useMatches().filter(m => (m.handle as RouteHandle | undefined)?.title).at(-1)
  const handleTitle = (match?.handle as RouteHandle | undefined)?.title
  const title = typeof handleTitle === 'function' ? handleTitle(match!.params, me) : handleTitle
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
          <AnimatePresence>{menu === 'account' && <AccountMenu me={me} onClose={close} />}</AnimatePresence>
        </div>
      </div>
    </header>
  )
}
