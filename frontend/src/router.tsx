import { createBrowserRouter } from 'react-router'
import { ChangePassword } from './features/account/ChangePassword'
import { NotificationsPage } from './features/account/NotificationsPage'
import { SettingsPage } from './features/account/SettingsPage'
import { AuthPage } from './features/auth/AuthPage'
import { Landing } from './features/auth/Landing'
import { Privacy } from './features/auth/Privacy'
import { ChatPage } from './features/chat/ChatPage'
import { AnswerTrace } from './features/insights/AnswerTrace'
import { Insights } from './features/insights/Insights'
import { QuizHistory } from './features/quizzes/QuizHistory'
import { QuizResults } from './features/quizzes/QuizResults'
import { StartQuiz } from './features/quizzes/StartQuiz'
import { TakeQuiz } from './features/quizzes/TakeQuiz'
import { ReviewSession } from './features/review/ReviewSession'
import { Today } from './features/home/Today'
import { SubjectWorkspace } from './features/subjects/SubjectWorkspace'
import { SubjectsList } from './features/subjects/SubjectsList'
import { ErrorPage } from './features/system/ErrorPage'
import { Shell } from './layout/Shell'
import type { RouteHandle } from './layout/Topbar'

const subjectTitle: RouteHandle['title'] = ({ subjectId }, me) => me?.subjects.find(s => s.id === Number(subjectId))?.name ?? 'Subject'

export const routes = [
  {
    path: '/',
    element: <Shell />,
    errorElement: <ErrorPage code="500" />,
    children: [
      { index: true, element: <Today />, handle: { title: 'Home' } },
      { path: 'subjects', element: <SubjectsList />, handle: { title: 'Subjects' } },
      {
        path: 'subjects/:subjectId',
        element: <SubjectWorkspace />,
        handle: { title: subjectTitle } satisfies RouteHandle,
      },
      // XP chat fills the window: no top bar or mobile tab bar (the design's full chat page)
      { path: 'review', element: <ReviewSession />, handle: { title: 'Review', focus: true } satisfies RouteHandle },
      { path: 'quizzes/history', element: <QuizHistory />, handle: { title: 'Quiz history' } },
      { path: 'insights', element: <Insights />, handle: { title: 'Insights' } },
      { path: 'notifications', element: <NotificationsPage />, handle: { title: 'Notifications' } },
      { path: 'settings', element: <SettingsPage />, handle: { title: 'Settings' } },
      { path: 'settings/password', element: <ChangePassword />, handle: { title: 'Password' } },
      { path: 'insights/:sessionId', element: <AnswerTrace />, handle: { title: 'Answer trace' } },
      { path: 'quizzes/:quizId/start', element: <StartQuiz />, handle: { title: 'Quiz', focus: true } satisfies RouteHandle },
      { path: 'quiz-attempts/:attemptId', element: <TakeQuiz />, handle: { title: 'Quiz', focus: true } satisfies RouteHandle },
      { path: 'quiz-attempts/:attemptId/results', element: <QuizResults />, handle: { title: 'Quiz results' } },
      { path: 'subjects/:subjectId/chat/:sessionId?', element: <ChatPage />, handle: { title: subjectTitle, fullBleed: true } satisfies RouteHandle },
    ],
  },
  // Public pages, outside the signed-in shell
  { path: 'login', element: <AuthPage mode="signin" /> },
  { path: 'register', element: <AuthPage mode="register" /> },
  { path: 'welcome', element: <Landing /> },
  { path: 'privacy', element: <Privacy /> },
  { path: '*', element: <ErrorPage code="404" /> },
]

export const router = createBrowserRouter(routes, { basename: '/app' })
