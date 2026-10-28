import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router'
import { api } from '../../lib/api'
import { timeAgo } from '../../lib/format'
import { reveal } from '../../lib/motion'
import { Icon } from '../../ui/Icon'
import { Button, Skeleton } from '../../ui/primitives'
import { followNotification, notificationLook, type Notification } from './notifications'
import '../../styles/account.css'

export function NotificationsPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const list = useQuery({ queryKey: ['notifications', 'page'], queryFn: () => api<{ unread: number; results: Notification[] }>('/api/notifications/?limit=50') })
  const markRead = useMutation({
    mutationFn: (ids?: number[]) => api('/api/notifications/read/', { method: 'POST', body: ids ? { ids } : {} }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
  const open = async (n: Notification) => {
    if (!n.read) await markRead.mutateAsync([n.id]).catch(() => undefined) // still follow the link if this fails
    followNotification(n, navigate)
  }
  const items = list.data?.results ?? []

  return (
    <div className="page-content narrow-page">
      <div className="page-intro">
        <div>
          <p className="overline">UPDATES</p>
          <h1>Notifications</h1>
          <p>Study aids, review reminders, and processing updates.</p>
        </div>
        <Button variant="secondary" disabled={!list.data?.unread || markRead.isPending} onClick={() => markRead.mutate(undefined)}>Mark all as read</Button>
      </div>
      {list.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load your notifications.</p>
          <Button variant="secondary" onClick={() => list.refetch()}>Try again</Button>
        </div>
      )}
      {list.isPending && (
        <div className="notifications-list" aria-busy="true" aria-label="Loading notifications">
          {[0, 1, 2].map(i => <div className="notification-page-item" key={i}><Skeleton className="skeleton-avatar" /><div className="skeleton-stack"><Skeleton /><Skeleton className="skeleton-label" /></div></div>)}
        </div>
      )}
      {list.isSuccess && items.length === 0 && (
        <div className="empty-state empty-state--compact">
          <span className="empty-icon"><Icon name="bell" /></span>
          <h2>No notifications yet</h2>
          <p>You’ll hear from XP when a file is ready to study or cards are ready to review.</p>
        </div>
      )}
      {items.length > 0 && (
        <div className="notifications-list">
          {items.map((n, i) => {
            const look = notificationLook(n)
            return (
              <motion.button type="button" key={n.id} className={`notification-page-item ${n.read ? '' : 'is-unread'}`} onClick={() => open(n)} {...reveal(i)}>
                <span className={`notification-icon ${look.className}`}><Icon name={look.icon} /></span>
                <div>
                  <strong>{n.title}</strong>
                  {n.body && <p>{n.body}</p>}
                  <small>{timeAgo(n.created_at)}</small>
                </div>
                {!n.read && <i aria-label="Unread" />}
              </motion.button>
            )
          })}
        </div>
      )}
    </div>
  )
}
