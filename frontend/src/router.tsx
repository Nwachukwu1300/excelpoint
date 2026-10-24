import { createBrowserRouter } from 'react-router'
import { Today } from './features/home/Today'
import { SubjectWorkspace } from './features/subjects/SubjectWorkspace'
import { SubjectsList } from './features/subjects/SubjectsList'
import { ErrorPage } from './features/system/ErrorPage'
import { Shell } from './layout/Shell'
import type { RouteHandle } from './layout/Topbar'

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
        handle: { title: ({ subjectId }, me) => me?.subjects.find(s => s.id === Number(subjectId))?.name ?? 'Subject' } satisfies RouteHandle,
      },
    ],
  },
  { path: '*', element: <ErrorPage code="404" /> },
]

export const router = createBrowserRouter(routes, { basename: '/app' })
