import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { me, mockApi, renderApp, reply } from '../../test/render'
import { followNotification, type Notification } from './notifications'

afterEach(() => vi.unstubAllGlobals())

const note = (over: Partial<Notification> = {}): Notification => ({
  id: 7, kind: 'material_ready', title: 'notes.pdf is ready to study', body: '5 flashcards', url: '/subjects/3/', read: false, created_at: new Date().toISOString(), ...over,
})

describe('Settings', () => {
  it('saves profile changes and shows server-side errors on the field', async () => {
    let calls = 0
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'PATCH /api/me/': () => (++calls === 1 ? { status: 400, body: { email: ['Enter a valid email address.'] } } : { body: { ...me, first_name: 'Alexa' } }),
    })
    renderApp('/settings')
    const first = await screen.findByLabelText('First name')
    expect(first).toHaveValue('Alex')
    expect(screen.getByLabelText('Level of education')).toHaveValue('undergraduate')

    await userEvent.clear(first)
    await userEvent.type(first, 'Alexa')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true')

    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByText('Changes saved')).toBeInTheDocument()
    const [, init] = fetchMock.mock.calls.filter(([u, i]) => u === '/api/me/' && i?.method === 'PATCH').at(-1)!
    expect(JSON.parse(init!.body as string)).toMatchObject({ first_name: 'Alexa', education_level: 'undergraduate' })
  })

  it('deletes the account only with the right password', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { ...location, assign })
    let calls = 0
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'POST /api/me/delete/': () => (++calls === 1 ? { status: 400, body: { confirm: ['That password isn’t right.'] } } : { status: 204, body: null }),
    })
    renderApp('/settings')
    expect(await screen.findByRole('link', { name: 'Download my data' })).toHaveAttribute('href', '/api/me/export/')
    await userEvent.click(await screen.findByRole('button', { name: 'Delete my account' }))
    const dialog = screen.getByRole('dialog', { name: 'Delete your account?' })
    await userEvent.type(within(dialog).getByLabelText('Enter your password to confirm'), 'wrong')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete account' }))
    expect(await within(dialog).findByText('That password isn’t right.')).toBeInTheDocument()
    expect(assign).not.toHaveBeenCalled()

    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete account' }))
    await waitFor(() => expect(assign).toHaveBeenCalledWith('/app/welcome?deleted=1'))
    const [, init] = fetchMock.mock.calls.filter(([u]) => u === '/api/me/delete/').at(-1)!
    expect(JSON.parse(init!.body as string)).toEqual({ confirm: 'wrong' })
  })

  it('switches theme straight away', async () => {
    mockApi({ 'GET /api/me/': me })
    renderApp('/settings')
    await userEvent.click(await screen.findByRole('radio', { name: /Dark/ }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(screen.getByRole('radio', { name: /Dark/ })).toHaveAttribute('aria-checked', 'true')
    await userEvent.click(screen.getByRole('radio', { name: /Light/ }))
  })
})

describe('Change password', () => {
  it('shows each field’s errors, then saves and returns to Settings', async () => {
    let calls = 0
    mockApi({
      'GET /api/me/': me,
      'POST /api/me/password/': () => (++calls === 1
        ? { status: 400, body: { old_password: ['Your old password was entered incorrectly.'], new_password2: ['This password is too short.', 'This password is too common.'] } }
        : { body: { ok: true } }),
    })
    renderApp('/settings/password')
    await userEvent.type(await screen.findByLabelText('Current password'), 'wrong')
    await userEvent.type(screen.getByLabelText('New password'), 'abc')
    await userEvent.type(screen.getByLabelText('Confirm new password'), 'abc')
    await userEvent.click(screen.getByRole('button', { name: 'Update password' }))
    expect(await screen.findByText('Your old password was entered incorrectly.')).toBeInTheDocument()
    expect(screen.getByText('This password is too common.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Update password' }))
    expect(await screen.findByText('Password updated')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
  })

  it('lets Google-only accounts set a password without the old one', async () => {
    const fetchMock = mockApi({ 'GET /api/me/': { ...me, has_password: false }, 'POST /api/me/password/': { ok: true } })
    renderApp('/settings/password')
    expect(await screen.findByRole('heading', { name: 'Set a password' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Current password')).not.toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('New password'), 'Brand-new-456!')
    await userEvent.type(screen.getByLabelText('Confirm new password'), 'Brand-new-456!')
    await userEvent.click(screen.getByRole('button', { name: 'Set password' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/me/password/', expect.anything()))
    const [, init] = fetchMock.mock.calls.find(([u]) => u === '/api/me/password/')!
    expect(JSON.parse(init!.body as string)).toEqual({ new_password1: 'Brand-new-456!', new_password2: 'Brand-new-456!' })
  })
})

describe('Notifications', () => {
  it('lists notifications and marks them all read', async () => {
    const fetchMock = mockApi({
      'GET /api/me/': me,
      'GET /api/notifications/?limit=50': { unread: 1, results: [note(), note({ id: 6, kind: 'review_due', title: '12 flashcards due', read: true })] },
      'POST /api/notifications/read/': reply(200, { marked: 1, unread: 0 }),
    })
    renderApp('/notifications')
    expect(await screen.findByText('notes.pdf is ready to study')).toBeInTheDocument()
    expect(screen.getByText('notes.pdf is ready to study').closest('button')).toHaveClass('is-unread')
    await userEvent.click(screen.getByRole('button', { name: 'Mark all as read' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/notifications/read/', expect.objectContaining({ method: 'POST' })))
  })

  it('never follows a link off the site', () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { ...location, assign })
    const navigate = vi.fn()
    followNotification(note({ url: 'https://evil.example' }), navigate)
    followNotification(note({ url: '//evil.example' }), navigate)
    expect(assign).not.toHaveBeenCalled()
    followNotification(note({ url: '/app/review' }), navigate)
    expect(navigate).toHaveBeenCalledWith('/review')
    followNotification(note({ url: '/subjects/3/' }), navigate)
    expect(assign).toHaveBeenCalledWith('/subjects/3/')
  })
})
