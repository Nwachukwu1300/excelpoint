import { AnimatePresence, motion } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { plural } from '../../lib/format'
import { spring } from '../../lib/motion'
import { fileName } from '../chat/Thread'
import { ConfidencePill, VerificationBadge } from '../../ui/AnswerBadges'
import { Icon } from '../../ui/Icon'
import { Markdown } from '../../ui/Markdown'
import { Badge, Button, ProgressBar, Skeleton } from '../../ui/primitives'
import { ms, num, pct, useTrace, type Trace } from './api'
import '../../styles/insights.css'

function Section({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="trace-section">
      <div className="trace-section-title"><span>{n}</span><h2>{title}</h2></div>
      <div className="trace-section-body">{children}</div>
    </section>
  )
}

function Chunks({ chunks }: { chunks: Trace['chunks'] }) {
  if (!chunks.length) return <p className="list-empty">Nothing in your materials matched this question.</p>
  return (
    <>
      {chunks.map((c, i) => (
        <article className="trace-chunk" key={`${c.material_name}-${c.chunk_index}-${i}`}>
          <span className="chunk-number">{i + 1}</span>
          <div className="chunk-main">
            <div><strong>{fileName(c.material_name)}</strong><span>Part {c.chunk_index + 1}</span></div>
            <p>“{c.text.length > 320 ? `${c.text.slice(0, 317)}…` : c.text}”</p>
          </div>
          <dl>
            <div><dt>Similarity</dt><dd>{num(c.similarity)}</dd></div>
            <div><dt>Rerank</dt><dd>{num(c.rerank)}</dd></div>
          </dl>
        </article>
      ))}
    </>
  )
}

const STAGE_LABEL: Record<string, string> = { generation: 'Answer generation', rewrite: 'Follow-up rewrite', verification: 'Verification' }
const humanize = (key: string) => key.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())

function Prompts({ prompts }: { prompts: Trace['prompts'] }) {
  const blocks = Object.entries(prompts).flatMap(([stage, messages]) =>
    messages.map((m, i) => ({ id: `${stage}-${i}`, label: `${STAGE_LABEL[stage] ?? humanize(stage)} · ${m.role === 'system' ? 'system prompt' : 'user prompt with context'}`, text: m.content })))
  const [open, setOpen] = useState<string | null>(blocks[0]?.id ?? null)
  if (!blocks.length) return <p className="list-empty">No prompts were recorded for this answer.</p>
  return (
    <>
      {blocks.map(b => (
        <div className="prompt-block" key={b.id}>
          <button type="button" aria-expanded={open === b.id} onClick={() => setOpen(open === b.id ? null : b.id)}>
            <span>{b.label}</span>
            <Icon name={open === b.id ? 'chevronDown' : 'chevronRight'} size={15} />
          </button>
          <AnimatePresence initial={false}>
            {open === b.id && (
              <motion.div className="prompt-wrap" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={spring.gentle}>
                <pre><code>{b.text}</code></pre>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </>
  )
}

export function AnswerTrace() {
  const sessionId = useParams().sessionId!
  const trace = useTrace(sessionId)
  const t = trace.data

  if (trace.isError) {
    return (
      <div className="page-content trace-page">
        <Link className="back-link" to="/insights"><Icon name="chevronRight" size={14} /> Back to Insights</Link>
        <div className="empty-state">
          <h2>{trace.error.message.includes('404') || trace.error.message === 'Not found.' ? 'This answer isn’t available' : 'We couldn’t load this answer’s details'}</h2>
          <p>It may belong to a subject that was deleted.</p>
          <Button variant="secondary" onClick={() => trace.refetch()}>Try again</Button>
        </div>
      </div>
    )
  }
  if (!t) {
    return (
      <div className="page-content trace-page" aria-busy="true">
        <Skeleton className="skeleton-label" /><Skeleton className="skeleton-value" /><Skeleton className="skeleton-chart" />
      </div>
    )
  }

  const heuristic = t.evaluations.find(e => e.evaluator === 'heuristic')
  const judge = t.evaluations.find(e => e.evaluator === 'llm_judge')
  const claims = t.verification.supported_claims.length + t.verification.unsupported_claims.length
  const breakdown = Object.entries(t.confidence.breakdown)
  const biggest = Math.max(0.001, ...breakdown.map(([, v]) => Math.abs(v)))
  const when = new Date(t.created_at)

  return (
    <div className="page-content trace-page">
      {t.chat
        ? <Link className="back-link" to={`/subjects/${t.chat.subject_id}/chat/${t.chat.session_id}`}><Icon name="chevronRight" size={14} /> Back to the conversation</Link>
        : <Link className="back-link" to="/insights"><Icon name="chevronRight" size={14} /> Back to Insights</Link>}
      <div className="trace-header">
        <div>
          <p className="overline">HOW THIS ANSWER WAS MADE · {when.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }).toUpperCase()}, {when.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</p>
          <h1>{t.question}</h1>
          {t.subject && <p>{t.subject.name}</p>}
        </div>
      </div>
      <PlainSummary t={t} claims={claims} />

      <details className="trace-technical">
      <summary>Technical details: timings, search results, prompts and scores</summary>
      <div className="trace-chips">
        <Badge>{t.follow_up ? 'Follow-up' : 'Standalone'}</Badge>
        {t.confidence.score != null && <ConfidencePill value={t.confidence.score} />}
        {heuristic?.faithfulness != null && <Badge tone={heuristic.faithfulness >= 0.8 ? 'success' : 'warning'}>Match {num(heuristic.faithfulness)}</Badge>}
        {t.chunks.length > 0 && <VerificationBadge verified={!t.unverified} />}
        <Badge>{plural(t.retry_count, 'retry', 'retries')}</Badge>
      </div>

      <section className="latency-card">
        <div className="card-heading">
          <div><h2>Latency by stage</h2><p>Time spent from question to verified answer</p></div>
          <strong>{ms(t.total_ms)} total</strong>
        </div>
        {t.stages.map((s, i) => (
          <div className="latency-row" key={s.name}>
            <span>{humanize(s.name)}</span>
            <div><motion.i initial={{ width: 0 }} animate={{ width: `${Math.max(0.5, s.pct)}%` }} transition={{ ...spring.gentle, delay: i * 0.04 }} /></div>
            <strong>{ms(s.ms)}</strong>
          </div>
        ))}
      </section>

      <div className="trace-stack">
        <Section n={1} title="Query">
          <div className="trace-grid three">
            <div><span>Type</span><strong>{t.follow_up ? 'Follow-up' : 'Standalone'}</strong></div>
            <div><span>Searched for</span><strong>{t.follow_up ? t.rewritten_query : t.question}</strong></div>
            <div><span>Pipeline</span><strong>{t.pipeline}</strong></div>
          </div>
        </Section>
        <Section n={2} title="Retrieved chunks"><Chunks chunks={t.chunks} /></Section>
        <Section n={3} title="Prompts sent to the model"><Prompts prompts={t.prompts} /></Section>
        <Section n={4} title="Answer">
          <div className="trace-answer">
            <Badge tone="success">FINAL ANSWER</Badge>
            <div className="answer-body"><Markdown text={t.final_answer} /></div>
            {t.generated_answer && t.generated_answer !== t.final_answer && (
              <details>
                <summary>View first attempt</summary>
                <div className="answer-body"><Markdown text={t.generated_answer} /></div>
              </details>
            )}
          </div>
        </Section>
        <Section n={5} title="Verification">
          <div className="verification-head">
            {t.chunks.length > 0 && <VerificationBadge verified={!t.unverified} />}
            <span>{claims ? `${t.verification.supported_claims.length} of ${plural(claims, 'statement')} backed by your files` : 'No statements were checked for this answer'}</span>
          </div>
          {t.verification.reasoning && <p className="verification-reason">{t.verification.reasoning}</p>}
          <div className="claims-grid">
            <div>
              <h3>Supported claims</h3>
              {t.verification.supported_claims.length
                ? t.verification.supported_claims.map(c => <p key={c}><Icon name="check" size={14} />{c}</p>)
                : <div className="no-claims">None recorded.</div>}
            </div>
            <div>
              <h3>Statements not backed by your files</h3>
              {t.verification.unsupported_claims.length
                ? t.verification.unsupported_claims.map(c => <p className="is-unsupported" key={c}><Icon name="close" size={14} />{c}</p>)
                : <div className="no-claims">Every statement is backed by your files.</div>}
            </div>
          </div>
        </Section>
        <Section n={6} title="Retries">
          {t.retries.length === 0 ? (
            <div className="empty-inline">
              <Icon name="check" />
              <div><strong>Passed on the first attempt</strong><p>No query rewrite or answer regeneration was needed.</p></div>
            </div>
          ) : (
            <>
              {t.retries.map(r => (
                <div className="retry-row" key={r.attempt_number}>
                  <Badge tone={r.success ? 'success' : 'warning'}>Attempt {r.attempt_number + 1} · {r.success ? 'verified' : 'not verified'}</Badge>
                  <p><span>Searched for</span> {r.rewritten_query}{r.rewrite_strategy ? ` (${r.rewrite_strategy})` : ''}</p>
                </div>
              ))}
              {t.retry_chunks.length > 0 && <><h3 className="retry-chunks-title">Chunks used by retries</h3><Chunks chunks={t.retry_chunks} /></>}
            </>
          )}
        </Section>
      </div>

      <section className="evaluation-card">
        <div className="card-heading"><div><h2>Evaluations</h2><p>Heuristic checks and optional judge output</p></div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Evaluator</th><th>Faithfulness</th><th>Unsupported</th><th>Relevance</th><th>Top similarity</th><th>Notes</th></tr></thead>
            <tbody>
              {[['Heuristic', heuristic], ['LLM judge', judge]].map(([label, e]) => {
                const ev = e as Trace['evaluations'][number] | undefined
                return (
                  <tr key={label as string}>
                    <td><strong>{label as string}</strong></td>
                    <td>{num(ev?.faithfulness)}</td>
                    <td>{pct(ev?.hallucination_rate)}</td>
                    <td>{num(ev?.answer_relevance)}</td>
                    <td>{num(ev?.retrieval_top_similarity)}</td>
                    <td>{ev ? (ev.reasoning || '—') : <Badge>Not enabled</Badge>}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      {t.confidence.score != null && breakdown.length > 0 && (
        <section className="confidence-card">
          <div className="card-heading"><div><h2>Confidence breakdown</h2><p>Signals contributing to the final {num(t.confidence.score)} confidence</p></div></div>
          {breakdown.map(([k, v]) => (
            <div className="confidence-row" key={k}>
              <span>{humanize(k)}</span>
              <ProgressBar value={(Math.abs(v) / biggest) * 100} label={humanize(k)} />
              <strong>{v < 0 ? '−' : ''}{num(Math.abs(v))}</strong>
            </div>
          ))}
        </section>
      )}
      </details>
    </div>
  )
}

/** What happened, in plain words, before any of the technical detail. */
function PlainSummary({ t, claims }: { t: Trace; claims: number }) {
  const files = [...new Set(t.chunks.map(c => fileName(c.material_name)))]
  const backed = t.verification.supported_claims.length
  return (
    <section className="trace-plain" aria-label="In short">
      <h2>In short</h2>
      <ul>
        <li>{files.length
          ? `XP searched your files and used ${plural(t.chunks.length, 'part')} of ${files.join(', ')}.`
          : 'XP found nothing in your files that matched this question, so it did not answer from outside them.'}</li>
        {files.length > 0 && <li>It wrote the answer only from those parts.</li>}
        {claims > 0 && <li>{backed === claims
          ? `It then checked the answer: ${claims === 1 ? 'its statement is' : `all ${claims} statements are`} in your files.`
          : `It then checked the answer: ${backed} of ${plural(claims, 'statement')} are in your files. Treat the rest with care.`}</li>}
        <li>It took {(t.total_ms / 1000).toFixed(1)} seconds.</li>
      </ul>
    </section>
  )
}
