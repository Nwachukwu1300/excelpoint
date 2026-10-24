import { createBrowserRouter } from 'react-router'
import { Today } from './features/home/Today'
import { ErrorPage } from './features/system/ErrorPage'
import { Shell } from './layout/Shell'

export const routes = [
  {
    path: '/',
    element: <Shell />,
    errorElement: <ErrorPage code="500" />,
    children: [
      { index: true, element: <Today />, handle: { title: 'Home' } },
    ],
  },
  { path: '*', element: <ErrorPage code="404" /> },
]

export const router = createBrowserRouter(routes, { basename: '/app' })
