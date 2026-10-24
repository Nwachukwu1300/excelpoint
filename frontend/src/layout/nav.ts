// Screens not rebuilt yet still live on the old Django pages. Each step swaps its entry for an in-app route.
export const oldPages = {
  takeQuiz: (quizId: number, fresh = false) => `/api/quiz/${quizId}/take/${fresh ? '?dynamic=true' : ''}`,
  quizHistory: '/api/quiz/history/',
  insights: '/insights/',
  notifications: '/users/notifications/',
  settings: '/users/settings/',
  password: '/users/change-password/',
  logout: '/users/logout/',
}

