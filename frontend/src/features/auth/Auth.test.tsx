import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp, reply } from '../../test/render'

const signedOut = { 'GET /api/me/': reply(403, { detail: 'Authentication credentials were not provided.' }) }

afterEach(() => vi.unstubAllGlobals())

describe('Sign in', () => {
  it('shows a wrong-password message, then signs in and goes to the requested page', async () => {
    document.cookie = 'csrftoken=tok'
    const assign = vi.fn()
    vi.stubGlobal('location', { ...location, assign, replace: vi.fn() })
    let calls = 0
    const fetchMock = mockApi({
      ...signedOut,
      'POST /api/auth/login/': () => (++calls === 1 ? { status: 400, body: { detail: 'The username or password is incorrect.' } } : { body: { ok: true, next: '/app/review' } }),
    })
    renderApp('/login?next=/app/review')
    await userEvent.type(await screen.findByLabelText('Username'), 'alex')
    await userEvent.type(screen.getByLabelText('Password'), 'nope')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The username or password is incorrect.')

    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(assign).toHaveBeenCalledWith('/app/review'))
    const [, init] = fetchMock.mock.calls.filter(([u]) => u === '/api/auth/login/').at(-1)!
    expect(JSON.parse(init!.body as string)).toEqual({ username: 'alex', password: 'nope', next: '/app/review' })
    expect((init!.headers as Record<string, string>)['X-CSRFToken']).toBe('tok')
  })

  it('explains a failed Google sign-in', async () => {
    mockApi(signedOut)
    renderApp('/login?error=google')
    expect(await screen.findByRole('alert')).toHaveTextContent('Google sign-in didn’t work')
    expect(screen.getByRole('link', { name: /Continue with Google/ })).toHaveAttribute('href', '/users/google/login/')
  })

  it('sends people who are already signed in straight into the app', async () => {
    const replace = vi.fn()
    vi.stubGlobal('location', { ...location, replace })
    mockApi({ 'GET /api/me/': me })
    renderApp('/login')
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/app/'))
  })
})

describe('Register', () => {
  it('shows each field’s errors from the server', async () => {
    mockApi({ ...signedOut, 'POST /api/auth/register/': reply(400, { username: ['A user with that username already exists.'], password2: ['The two password fields didn’t match.'] }) })
    renderApp('/register')
    await userEvent.type(await screen.findByLabelText('Username'), 'alex')
    await userEvent.type(screen.getByLabelText('Email'), 'alex@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'Brand-new-456!')
    await userEvent.type(screen.getByLabelText('Confirm password'), 'different')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText('A user with that username already exists.')).toBeInTheDocument()
    expect(screen.getByText('The two password fields didn’t match.')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toHaveAttribute('aria-invalid', 'true')
  })
})

describe('Landing', () => {
  it('invites visitors to sign up, and offers the app to signed-in users', async () => {
    mockApi(signedOut)
    const first = renderApp('/welcome')
    expect(await screen.findByRole('heading', { name: 'Learn faster from your own materials' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Sign up free|Start studying free|Create your free account/ })[0]).toHaveAttribute('href', '/register')
    first.unmount()
    vi.unstubAllGlobals()
    mockApi({ 'GET /api/me/': me })
    renderApp('/welcome')
    expect(await screen.findByRole('link', { name: 'Open ExcelPoint' })).toHaveAttribute('href', '/app/')
  })
})
