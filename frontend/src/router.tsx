import { createBrowserRouter, type RouteObject } from 'react-router'
import { ErrorPage } from './features/system/ErrorPage'
import type { RouteHandle } from './layout/Topbar'

/**
 * Each page is its own download, fetched when first visited, so the public pages (landing, sign in)
 * don't make a phone on slow 3G download and parse chat, quizzes and insights first.
 */
// The "Loading ExcelPoint…" screen from index.html, kept while the first page downloads
const boot = <div className="boot" role="status"><img src={`${import.meta.env.BASE_URL}favicon.png`} alt="" width={44} height={44} />Loading ExcelPoint…</div>

const page = (load: () => Promise<{ default: React.ComponentType }>): Pick<RouteObject, 'lazy' | 'hydrateFallbackElement'> =>
  ({ lazy: () => load().then(m => ({ Component: m.default })), hydrateFallbackElement: boot })

const subjectTitle: RouteHandle['title'] = ({ subjectId }, me) => me?.subjects.find(s => s.id === Number(subjectId))?.name ?? 'Subject'

export const routes: RouteObject[] = [
  {
    path: '/',
    ...page(() => import('./layout/Shell').then(m => ({ default: m.Shell }))),
    errorElement: <ErrorPage code="500" />,
    children: [
      { index: true, ...page(() => import('./features/home/Today').then(m => ({ default: m.Today }))), handle: { title: 'Home' } },
      { path: 'subjects', ...page(() => import('./features/subjects/SubjectsList').then(m => ({ default: m.SubjectsList }))), handle: { title: 'Subjects' } },
      {
        path: 'subjects/:subjectId',
        ...page(() => import('./features/subjects/SubjectWorkspace').then(m => ({ default: m.SubjectWorkspace }))),
        handle: { title: subjectTitle } satisfies RouteHandle,
      },
      // XP chat fills the window: no top bar or mobile tab bar (the design's full chat page)
      { path: 'review', ...page(() => import('./features/review/ReviewSession').then(m => ({ default: m.ReviewSession }))), handle: { title: 'Review', focus: true } satisfies RouteHandle },
      { path: 'quizzes/history', ...page(() => import('./features/quizzes/QuizHistory').then(m => ({ default: m.QuizHistory }))), handle: { title: 'Quiz history' } },
      { path: 'insights', ...page(() => import('./features/insights/Insights').then(m => ({ default: m.Insights }))), handle: { title: 'Answer quality' } },
      { path: 'notifications', ...page(() => import('./features/account/NotificationsPage').then(m => ({ default: m.NotificationsPage }))), handle: { title: 'Notifications' } },
      { path: 'settings', ...page(() => import('./features/account/SettingsPage').then(m => ({ default: m.SettingsPage }))), handle: { title: 'Settings' } },
      { path: 'settings/password', ...page(() => import('./features/account/ChangePassword').then(m => ({ default: m.ChangePassword }))), handle: { title: 'Password' } },
      { path: 'insights/:sessionId', ...page(() => import('./features/insights/AnswerTrace').then(m => ({ default: m.AnswerTrace }))), handle: { title: 'Answer trace' } },
      { path: 'quizzes/:quizId/start', ...page(() => import('./features/quizzes/StartQuiz').then(m => ({ default: m.StartQuiz }))), handle: { title: 'Quiz', focus: true } satisfies RouteHandle },
      { path: 'quiz-attempts/:attemptId', ...page(() => import('./features/quizzes/TakeQuiz').then(m => ({ default: m.TakeQuiz }))), handle: { title: 'Quiz', focus: true } satisfies RouteHandle },
      { path: 'quiz-attempts/:attemptId/results', ...page(() => import('./features/quizzes/QuizResults').then(m => ({ default: m.QuizResults }))), handle: { title: 'Quiz results' } },
      { path: 'subjects/:subjectId/chat/:sessionId?', ...page(() => import('./features/chat/ChatPage').then(m => ({ default: m.ChatPage }))), handle: { title: subjectTitle, fullBleed: true } satisfies RouteHandle },
    ],
  },
  // Public pages, outside the signed-in shell
  { path: 'login', ...page(() => import('./features/auth/AuthPage').then(m => ({ default: () => <m.AuthPage mode="signin" /> }))) },
  { path: 'register', ...page(() => import('./features/auth/AuthPage').then(m => ({ default: () => <m.AuthPage mode="register" /> }))) },
  { path: 'welcome', ...page(() => import('./features/auth/Landing').then(m => ({ default: m.Landing }))) },
  { path: 'privacy', ...page(() => import('./features/auth/Privacy').then(m => ({ default: m.Privacy }))) },
  { path: 'terms', ...page(() => import('./features/auth/Terms').then(m => ({ default: m.Terms }))) },
  { path: 'forgot-password', ...page(() => import('./features/auth/PasswordReset').then(m => ({ default: m.ForgotPassword }))) },
  { path: 'verify-email/:token', ...page(() => import('./features/auth/VerifyEmail').then(m => ({ default: m.VerifyEmail }))) },
  { path: 'reset-password/:uid/:token', ...page(() => import('./features/auth/PasswordReset').then(m => ({ default: m.ResetPassword }))) },
  { path: '*', element: <ErrorPage code="404" /> },
]

export const router = createBrowserRouter(routes, { basename: '/app' })
