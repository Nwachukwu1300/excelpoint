import { useQueryClient } from '@tanstack/react-query'
import { AnimatePresence } from 'motion/react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError, useMe } from '../../lib/api'
import { shortDate } from '../../lib/format'
import { Icon } from '../../ui/Icon'
import { useOneAtATime } from '../../lib/useOneAtATime'
import { ConfirmDialog } from '../../ui/ConfirmDialog'
import { Button, IconButton, Skeleton, XpAvatar } from '../../ui/primitives'
import { toast } from '../../ui/Toast'
import {
  awaitingAnswer, createSession, messagesKey, RateLimitError, sendMessage, sessionsKey, streamMessage, StreamUnavailableError,
  useDeleteSession, useMessages, useSessions, type ChatMessage, type ChatSession, type Exchange, type SourceChunk,
} from './api'
import { useMaterials } from '../subjects/api'
import { Answer, StreamingAnswer, Thinking, UserBubble } from './Thread'
import { SourcesPanel } from './SourcesPanel'
import '../../styles/chat.css'

const MAX = 1000
const wide = () => typeof matchMedia === 'function' && matchMedia('(min-width: 1101px)').matches

type Pending = { question: string; text: string }

export function ChatPage() {
  const params = useParams()
  const subjectId = Number(params.subjectId)
  const sessionId = params.sessionId ? Number(params.sessionId) : undefined
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const me = useMe()
  const subjectName = me.data?.subjects.find(s => s.id === subjectId)?.name ?? ''
  const sessions = useSessions(subjectId)
  const messages = useMessages(subjectId, sessionId)
  const materials = useMaterials(subjectId)
  const filesReady = !materials.data || materials.data.some(m => m.status === 'COMPLETED')
  const filesBusy = materials.data?.some(m => m.status === 'PENDING' || m.status === 'PROCESSING')

  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState<Pending | null>(null)
  const [justArrived, setJustArrived] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)
  const [rateLimit, setRateLimit] = useState<RateLimitError | null>(null)
  const [sourcesOpen, setSourcesOpen] = useState(wide)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [focus, setFocus] = useState<SourceChunk | null>(null)
  const inflight = useRef<{ sid: number; controller: AbortController } | null>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const composer = useRef<HTMLTextAreaElement>(null)
  const removeChat = useDeleteSession(subjectId)
  const once = useOneAtATime()
  const [deletingChat, setDeletingChat] = useState<ChatSession | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false) // phones: the list opens over the chat
  useEffect(() => setHistoryOpen(false), [sessionId])
  const confirmDeleteChat = () => deletingChat && once(() => removeChat.mutateAsync(deletingChat.id).then(
    () => {
      if (deletingChat.id === sessionId) navigate(`/subjects/${subjectId}/chat`, { replace: true })
      setDeletingChat(null)
      toast('success', 'Conversation deleted')
    },
    () => toast('error', 'Couldn’t delete the conversation', 'Try again in a moment.'),
  ))

  // Opening another conversation drops a half-finished answer from view (the server still saves it).
  // A new chat moving to its own URL is the same conversation, so its stream keeps going.
  useEffect(() => {
    if (inflight.current && inflight.current.sid !== sessionId) {
      inflight.current.controller.abort()
      inflight.current = null
      setPending(null)
    }
  }, [sessionId])
  useEffect(() => () => inflight.current?.controller.abort(), [])
  useEffect(() => { setSelectedId(null); setFocus(null); setError(null) }, [sessionId])

  const thread = messages.data ?? []
  const lastWithSources = [...thread].reverse().find(m => m.role === 'assistant' && m.metadata?.retrieved_chunks?.length)
  const shown = thread.find(m => m.id === selectedId) ?? lastWithSources

  // Keep the newest words in view while the answer streams, unless the reader scrolled up.
  // A conversation opens at its newest message.
  const openedAt = useRef<number | undefined>(undefined)
  useLayoutEffect(() => {
    const el = scroller.current
    if (!el) return
    const firstLoad = thread.length > 0 && openedAt.current !== sessionId
    if (firstLoad) openedAt.current = sessionId
    if (firstLoad || el.scrollHeight - el.scrollTop - el.clientHeight < 160) el.scrollTop = el.scrollHeight
  }, [thread.length, pending?.text, pending?.question, sessionId])

  const finish = (sid: number, exchange: Exchange) => {
    queryClient.setQueryData<{ messages: ChatMessage[] }>(messagesKey(subjectId, sid), old => {
      const fresh = [exchange.user_message, exchange.assistant_message]
      return { messages: [...(old?.messages ?? []).filter(m => !fresh.some(f => f.id === m.id)), ...fresh] }
    })
    setJustArrived(ids => [...ids, exchange.user_message.id, exchange.assistant_message.id])
    setSelectedId(null)
    // Show the conversation in the list now; the refetch below then brings the server's title
    queryClient.setQueryData<{ sessions: ChatSession[] }>(sessionsKey(subjectId), old => old && {
      sessions: [{ ...exchange.session, message_count: Math.max(exchange.session.message_count, 2) }, ...old.sessions.filter(s => s.id !== exchange.session.id)],
    })
    for (const key of [sessionsKey(subjectId), ['home']]) queryClient.invalidateQueries({ queryKey: key })
  }

  const send = async (text = draft) => {
    const question = text.trim()
    if (!question || pending) return
    setDraft('')
    setError(null)
    setRateLimit(null)
    setPending({ question, text: '' })
    try {
      let sid = sessionId
      const controller = new AbortController()
      if (!sid) {
        sid = (await createSession(subjectId)).id
        inflight.current = { sid, controller }
        queryClient.setQueryData(messagesKey(subjectId, sid), { messages: [] }) // nothing to fetch yet
        navigate(`/subjects/${subjectId}/chat/${sid}`, { replace: true })
      }
      inflight.current = { sid, controller }
      const body = { message: question, session_id: sid }
      let exchange: Exchange
      try {
        exchange = await streamMessage(subjectId, body, t => setPending(p => p && { ...p, text: p.text + t }), controller.signal)
      } catch (e) {
        if (!(e instanceof StreamUnavailableError)) throw e
        exchange = await sendMessage(subjectId, body) // the stream couldn't start: ask the normal way
      }
      finish(sid, exchange)
      setPending(null)
      inflight.current = null
    } catch (e) {
      if ((e as Error).name === 'AbortError') return
      inflight.current = null
      setPending(null)
      setDraft(question) // nothing lost: the question goes back in the box
      if (e instanceof RateLimitError) setRateLimit(e)
      else setError((e as Error).message || 'XP is currently unavailable. Please try again later.')
    } finally {
      composer.current?.focus()
    }
  }

  const cite = (message: ChatMessage, chunk: SourceChunk) => {
    setSelectedId(message.id)
    setFocus(chunk)
    setSourcesOpen(true)
  }

  const title = sessions.data?.find(s => s.id === sessionId)?.title || (sessionId ? 'Conversation' : 'New conversation')
  const empty = !sessionId && !pending
  const minutes = rateLimit?.retryInSeconds ? Math.ceil(rateLimit.retryInSeconds / 60) : null

  if (me.data && !me.data.subjects.some(s => s.id === subjectId)) {
    return (
      <div className="page-content">
        <div className="empty-state">
          <span className="empty-icon"><Icon name="book" /></span>
          <h2>Subject not found</h2>
          <p>It may have been deleted, or the link is out of date.</p>
          <Link className="button button--secondary" to="/subjects">Back to subjects</Link>
        </div>
      </div>
    )
  }

  return (
    <div className={`chat-layout ${sourcesOpen ? '' : 'sources-closed'}`}>
      {historyOpen && <div className="history-scrim" onClick={() => setHistoryOpen(false)} aria-hidden="true" />}
      <aside className={`chat-history ${historyOpen ? 'is-open' : ''}`} aria-label="Conversations">
        <Link className="button button--secondary full-width" to={`/subjects/${subjectId}/chat`}><Icon name="plus" />New chat</Link>
        <span className="history-label">RECENT</span>
        {sessions.isPending && <div className="skeleton-stack history-loading"><Skeleton /><Skeleton /><Skeleton /></div>}
        {sessions.data?.length === 0 && <p className="history-empty">Your conversations will be listed here.</p>}
        {sessions.data?.map(s => (
          <div key={s.id} className={`history-row ${s.id === sessionId ? 'is-active' : ''}`}>
            <Link to={`/subjects/${subjectId}/chat/${s.id}`} aria-current={s.id === sessionId ? 'page' : undefined}>
              <strong>{s.title || 'Untitled conversation'}</strong>
              <span>{shortDate(s.last_activity)}</span>
            </Link>
            <IconButton icon="close" label={`Delete conversation: ${s.title || 'Untitled'}`} onClick={() => setDeletingChat(s)} />
          </div>
        ))}
      </aside>

      <section className="chat-thread" aria-label="Conversation with XP">
        <header className="chat-top">
          <div>
            <Link to={`/subjects/${subjectId}`} aria-label={`Back to ${subjectName || 'subject'}`}><Icon name="chevronRight" size={15} /></Link>
            <div>
              <strong>{title}</strong>
              <span>{subjectName}</span>
            </div>
          </div>
          <div className="chat-top-actions">
            <IconButton icon="clock" label="Past conversations" className="history-toggle" aria-expanded={historyOpen} onClick={() => setHistoryOpen(o => !o)} />
            <IconButton icon="panel" label={sourcesOpen ? 'Hide sources' : 'Show sources'} aria-pressed={sourcesOpen} onClick={() => setSourcesOpen(o => !o)} />
          </div>
        </header>

        <div className="messages" ref={scroller}>
          {empty && !filesReady ? (
            <div className="chat-empty">
              <span className="xp-avatar"><Icon name="file" /></span>
              <h1>{filesBusy ? 'Your file is still being read' : 'Upload a file first'}</h1>
              <p>{filesBusy
                ? 'XP can answer as soon as it has finished. This usually takes under a minute.'
                : `XP answers only from the files in ${subjectName || 'this subject'}, and none are ready yet.`}</p>
              <Link className="button" to={`/subjects/${subjectId}${filesBusy ? '' : '?upload=1&then=chat'}`}>
                <Icon name={filesBusy ? 'file' : 'upload'} />{filesBusy ? 'See your files' : 'Upload a file'}
              </Link>
            </div>
          ) : empty ? (
            <div className="chat-empty">
              <XpAvatar />
              <h1>Ask anything about your {subjectName} files</h1>
              <p>XP answers only from your files and shows where each answer came from.</p>
              <div>
                {['Summarise the key ideas', 'Explain the hardest concept simply', 'What are the most important definitions?'].map(q => (
                  <button type="button" key={q} onClick={() => send(q)}>{q}</button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.isPending && sessionId && (
                <div className="skeleton-chat" aria-label="Loading conversation"><Skeleton className="skeleton-avatar" /><div><Skeleton /><Skeleton /><Skeleton /></div></div>
              )}
              {messages.isError && (messages.error instanceof ApiError && messages.error.status === 404 ? (
                <div className="inline-error" role="alert">
                  <p>This conversation was deleted.</p>
                  <Link className="button button--secondary" to={`/subjects/${subjectId}/chat`}>Start a new chat</Link>
                </div>
              ) : (
                <div className="inline-error" role="alert">
                  <p>We couldn’t load this conversation.</p>
                  <Button variant="secondary" onClick={() => messages.refetch()}>Try again</Button>
                </div>
              ))}
              {thread.map(m => m.role === 'user'
                ? <UserBubble key={m.id} text={m.content} animate={justArrived.includes(m.id)} />
                : <Answer key={m.id} message={m} subjectId={subjectId} selected={sourcesOpen && shown?.id === m.id}
                    onCite={c => cite(m, c)} animate={justArrived.includes(m.id)} />)}
              {!pending && awaitingAnswer(thread) && <Thinking />}
              {pending && <UserBubble text={pending.question} animate />}
              {pending && !pending.text && <Thinking />}
              {pending?.text && <StreamingAnswer text={pending.text} />}
              {error && <div className="chat-error" role="alert">{error}</div>}
            </>
          )}
        </div>

        <AnimatePresence>
          {rateLimit && (
            <div className="rate-banner" role="alert">
              <Icon name="clock" size={15} />
              <span>
                <strong>You’ve reached your limit of questions for this hour.</strong>{' '}
                {minutes ? `Try again in about ${minutes} minute${minutes === 1 ? '' : 's'}.` : 'Try again later.'}
              </span>
              <IconButton icon="close" label="Dismiss" onClick={() => setRateLimit(null)} />
            </div>
          )}
        </AnimatePresence>

        <form className="chat-composer" onSubmit={e => { e.preventDefault(); send() }}>
          <textarea
            ref={composer}
            value={draft}
            maxLength={MAX}
            rows={1}
            aria-label="Ask XP"
            placeholder="Ask XP about your files…"
            onChange={e => {
              setDraft(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = `${Math.min(e.target.scrollHeight, 110)}px`
            }}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send() }
            }}
          />
          {draft.length > 850 && <span>{draft.length}/{MAX}</span>}
          <button type="submit" disabled={!draft.trim() || !!pending} aria-label="Send message"><Icon name="arrow" /></button>
          <small>Enter to send · Shift + Enter for a new line</small>
        </form>
      </section>

      <AnimatePresence>
        {sourcesOpen && (
          <>
            <div className="sources-scrim" onClick={() => setSourcesOpen(false)} aria-hidden="true" />
            <SourcesPanel message={shown} focus={focus} onClose={() => setSourcesOpen(false)} />
          </>
        )}
      </AnimatePresence>
      <ConfirmDialog open={!!deletingChat} title="Delete this conversation?" confirmLabel="Delete conversation" icon="sparkles"
        busy={removeChat.isPending} onCancel={() => setDeletingChat(null)} onConfirm={confirmDeleteChat}>
        <p>“{deletingChat?.title || 'Untitled conversation'}” and all its messages will be removed. This can’t be undone.</p>
      </ConfirmDialog>
    </div>
  )
}
