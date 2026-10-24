import type { Me } from '../lib/api'

// Screens not rebuilt yet still live on the old Django pages. Each step swaps its entry for an in-app route.
export const oldPages = {
  chat: (subjectId: number) => `/subjects/${subjectId}/`, // the old subject page hosts the XP chat widget (until step 4)
  review: (subjectId: number) => `/subjects/${subjectId}/review/`,
  takeQuiz: (quizId: number, fresh = false) => `/api/quiz/${quizId}/take/${fresh ? '?dynamic=true' : ''}`,
  quizHistory: '/api/quiz/history/',
  insights: '/insights/',
  notifications: '/users/notifications/',
  settings: '/users/settings/',
  password: '/users/change-password/',
  logout: '/users/logout/',
}

/** The old review page is per subject: send people to the first subject with cards due. */
export function reviewHref(me: Me | undefined) {
  const due = me?.subjects.find(s => s.due_count > 0)
  return due ? oldPages.review(due.id) : '/subjects'
}
