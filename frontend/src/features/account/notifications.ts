import type { IconName } from '../../ui/Icon'

export type Notification = { id: number; kind: string; title: string; body: string; url: string; read: boolean; created_at: string }

/** Icon and colour for a notification, from its kind (material_ready, review_due, …) and wording. */
export function notificationLook(n: Notification): { icon: IconName; className: string } {
  if (/fail|couldn/i.test(n.kind + n.title)) return { icon: 'close', className: 'failed' }
  if (n.kind.includes('review')) return { icon: 'repeat', className: '' }
  return { icon: 'sparkles', className: n.kind.includes('ready') ? 'ai-bg' : '' }
}

/** Follow a notification's link: in-app routes directly, old pages (which mostly redirect into the app) by URL. */
export function followNotification(n: Notification, navigate: (to: string) => void) {
  if (n.url.startsWith('/app/')) navigate(n.url.slice('/app'.length))
  else if (n.url.startsWith('/') && !n.url.startsWith('//')) location.assign(n.url) // site-relative only
}
