import type { Me } from '../lib/api'

// Screens not rebuilt yet still live on the old Django pages. Each step swaps its entry for an in-app route.
export const oldPages = {
  subjects: '/subjects/',
  subject: (id: number) => `/subjects/${id}/`,
  review: (id: number) => `/subjects/${id}/review/`,
  insights: '/insights/',
  notifications: '/users/notifications/',
  settings: '/users/settings/',
  password: '/users/change-password/',
  logout: '/users/logout/',
}

/** The old review page is per subject: send people to the first subject with cards due. */
export function reviewHref(me: Me | undefined) {
  const due = me?.subjects.find(s => s.due_count > 0)
  return due ? oldPages.review(due.id) : oldPages.subjects
}
