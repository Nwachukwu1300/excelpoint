import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { emptyHome, me, mockApi, renderApp } from '../test/render'

const notifications = {
  unread: 2,
  results: [
    { id: 7, kind: 'material_ready', title: 'notes.pdf is ready to study', body: '5 flashcards', url: '/subjects/3/', read: false, created_at: new Date().toISOString() },
    { id: 6, kind: 'review_due', title: '12 flashcards due', body: '', url: '', read: true, created_at: new Date().toISOString() },
  ],
}

afterEach(() => vi.unstubAllGlobals())

describe('Shell', () => {
  it('shows the user, subjects with due counts, and badges from /api/me/', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/home/': emptyHome })
    renderApp('/')
    expect(await screen.findByRole('heading', { name: /, Alex$/ })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Primary navigation' })
    expect(within(nav).getByRole('link', { name: /Database Systems\s*12/ })).toHaveAttribute('href', '/subjects/3')
    expect(within(nav).getByRole('link', { name: /Review\s*20/ })).toHaveAttribute('href', '/review')
    expect(within(nav).getByRole('link', { name: /Home/ })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: /Quizzes/ })).toHaveAttribute('href', '/quizzes/history') // same places as the phone tabs
    expect(screen.getByRole('button', { name: 'Notifications, 2 unread' })).toBeInTheDocument()
    expect(screen.getByText('Alex Morgan')).toBeInTheDocument()
    expect(screen.queryByText(/Study tip/)).not.toBeInTheDocument() // the Review badge already shows the count
  })

  it('keeps answer-quality numbers out of the main navigation', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/home/': emptyHome })
    renderApp('/')
    await screen.findByRole('heading', { name: /, Alex$/ })
    expect(within(screen.getByRole('navigation', { name: 'Primary navigation' })).queryByRole('link', { name: /Insights/ })).not.toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: 'Mobile navigation' })).getByRole('link', { name: /Quizzes/ })).toHaveAttribute('href', '/quizzes/history')
  })

  it('lets keyboard users skip straight to the page content', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/home/': emptyHome })
    renderApp('/')
    await screen.findByRole('heading', { name: /, Alex$/ })
    const skip = screen.getByRole('link', { name: 'Skip to content' })
    expect(skip).toHaveAttribute('href', '#main')
    expect(document.getElementById('main')).toHaveAttribute('tabindex', '-1')
  })

  it('sends signed-out users to the Django login with a return path', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { ...location, assign, pathname: '/app/', search: '' })
    mockApi({ 'GET /api/me/': () => ({ status: 403, body: { detail: 'Authentication credentials were not provided.' } }) })
    renderApp('/')
    await waitFor(() => expect(assign).toHaveBeenCalledWith('/app/login?next=%2Fapp%2F'))
  })

  it('lists notifications and marks all read with the CSRF token', async () => {
    document.cookie = 'csrftoken=tok123'
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'GET /api/home/': emptyHome,
      'GET /api/notifications/?limit=5': notifications,
      'POST /api/notifications/read/': { marked: 1, unread: 0 },
    })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: /^Notifications/ }))
    const menu = await screen.findByRole('dialog', { name: 'Notifications' })
    expect(await within(menu).findByText('notes.pdf is ready to study')).toBeInTheDocument()
    expect(within(menu).getByText('12 flashcards due').closest('button')).not.toHaveClass('is-new')

    await userEvent.click(within(menu).getByRole('button', { name: 'Mark all as read' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/notifications/read/', expect.objectContaining({ method: 'POST' })))
    const [, init] = fetchMock.mock.calls.find(([url]) => url === '/api/notifications/read/')!
    expect((init!.headers as Record<string, string>)['X-CSRFToken']).toBe('tok123')
    expect(init!.body).toBe('{}')
  })

  it('closes a menu with Escape', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/home/': emptyHome })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Open account menu' }))
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()
    await userEvent.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument())
  })

  it('collapses the sidebar and remembers it', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/home/': emptyHome })
    renderApp('/')
    await userEvent.click(await screen.findByRole('button', { name: 'Collapse sidebar' }))
    expect(screen.queryByText('Database Systems')).not.toBeInTheDocument()
    expect(localStorage.getItem('xp-sidebar-collapsed')).toBe('1')
    await userEvent.click(screen.getByRole('button', { name: 'Expand sidebar' }))
    expect(screen.getByText('Database Systems')).toBeInTheDocument()
  })

  it('shows the 404 page for unknown routes', async () => {
    mockApi({})
    renderApp('/nope')
    expect(await screen.findByRole('heading', { name: 'This page isn’t here' })).toBeInTheDocument()
  })

  it('asks an unconfirmed student to confirm their email, and can send the link again', async () => {
    sessionStorage.clear()
    const fetchMock = mockApi({ 'GET /api/me/': { ...me, email_verified: false }, 'GET /api/home/': emptyHome,
      'POST /api/me/confirm-email/': { ok: true, email: 'alex@example.com' } })
    renderApp('/')
    const banner = await screen.findByText(/Confirm your email\./)
    expect(banner.closest('[role=status]')).toHaveTextContent('We sent a link to alex@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Send again' }))
    expect(await screen.findByText('Link sent')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([u]) => u === '/api/me/confirm-email/')).toHaveLength(1)
    await userEvent.click(screen.getByRole('button', { name: 'Hide for now' }))
    expect(screen.queryByText(/Confirm your email\./)).not.toBeInTheDocument()
  })

  it('shows no reminder once the email is confirmed', async () => {
    mockApi({ 'GET /api/me/': me, 'GET /api/home/': emptyHome })
    renderApp('/')
    await screen.findByRole('heading', { name: /, Alex$/ })
    expect(screen.queryByText(/Confirm your email/)).not.toBeInTheDocument()
  })
})
