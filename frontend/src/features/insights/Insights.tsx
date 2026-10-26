import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router'
import { plural } from '../../lib/format'
import { reveal, spring } from '../../lib/motion'
import { ConfidencePill, VerificationBadge, confidenceLevel } from '../../ui/AnswerBadges'
import { CountUp } from '../../ui/CountUp'
import { Icon } from '../../ui/Icon'
import { Badge, Button, Skeleton, buttonClass, type Tone } from '../../ui/primitives'
import { dailySeries, ms, num, pct, useInsights, type InsightsData } from './api'
import '../../styles/insights.css'

const RANGES = [7, 30, 90]

function TrendChart({ summary }: { summary: InsightsData['summary'] }) {
  const series = dailySeries(summary.trends, summary.days)
  const most = Math.max(1, ...series.map(s => s.day?.sessions ?? 0))
  const n = series.length
  const points = series
    .map((s, i) => (s.day?.faithfulness == null ? null : `${((i + 0.5) / n) * 700},${(1 - s.day.faithfulness) * 180}`))
    .filter(Boolean)
    .join(' ')
  const labels = [0, 0.25, 0.5, 0.75, 1].map(f => series[Math.min(n - 1, Math.round(f * (n - 1)))]!.date)
  return (
    <div className="quality-chart">
      <div className="chart-axis" aria-hidden="true"><span>1.0</span><span>0.5</span><span>0</span></div>
      <div className="chart-plot" role="img" aria-label={`Questions and faithfulness per day for the last ${summary.days} days`}>
        {series.map((s, i) => (
          <div className="chart-day" key={i} title={s.day ? `${s.date.toLocaleDateString('en-GB')}: ${plural(s.day.sessions, 'question')}` : undefined}>
            <motion.span initial={{ height: 0 }} animate={{ height: `${((s.day?.sessions ?? 0) / most) * 72}%` }} transition={{ ...spring.gentle, delay: Math.min(i, 30) * 0.01 }} />
            {!!s.day?.no_context && <i />}
            {s.day?.faithfulness != null && <b className="faith-dot" style={{ bottom: `${s.day.faithfulness * 100}%` }} />}
          </div>
        ))}
        {points && (
          <svg viewBox="0 0 700 180" preserveAspectRatio="none" aria-hidden="true">
            <polyline points={points} />
          </svg>
        )}
      </div>
      <div className="chart-labels" aria-hidden="true">
        {labels.map((d, i) => <span key={i}>{d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</span>)}
      </div>
    </div>
  )
}

function Metric({ label, value, note, badge, tone }: { label: string; value: ReactNode; note: string; badge: string; tone: Tone }) {
  return (
    <article className="metric-card">
      <div><span>{label}</span><Badge tone={tone}>{badge}</Badge></div>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  )
}

export function Insights() {
  const [params, setParams] = useSearchParams()
  const days = RANGES.includes(Number(params.get('days'))) ? Number(params.get('days')) : 30
  const insights = useInsights(days)
  const data = insights.data
  const t = data?.summary.totals
  const loading = insights.isPending || (insights.isPlaceholderData && insights.isFetching)

  return (
    <div className="page-content insights-page">
      <div className="page-intro">
        <div>
          <p className="overline">ANSWER QUALITY</p>
          <h1>Insights</h1>
          <p>See how reliably XP answers from your uploaded materials.</p>
        </div>
        <div className="segmented-control" role="group" aria-label="Time range">
          {RANGES.map(r => (
            <button type="button" key={r} aria-pressed={days === r} className={days === r ? 'is-active' : ''} onClick={() => setParams(r === 30 ? {} : { days: String(r) }, { replace: true })}>
              {days === r && <motion.span layoutId="range-pill" className="segment-pill" transition={spring.morph} />}
              <span>{r} days</span>
            </button>
          ))}
        </div>
      </div>

      {insights.isError && (
        <div className="inline-error" role="alert">
          <p>We couldn’t load your insights.</p>
          <Button variant="secondary" onClick={() => insights.refetch()}>Try again</Button>
        </div>
      )}
      {loading && (
        <div aria-busy="true" aria-label="Loading insights">
          <div className="stats-grid">
            {[0, 1, 2, 3].map(i => <div className="metric-card" key={i}><Skeleton className="skeleton-label" /><Skeleton className="skeleton-value" /><Skeleton /></div>)}
          </div>
          <Skeleton className="skeleton-chart" />
        </div>
      )}
      {!loading && data && t && t.sessions === 0 && (
        <div className="empty-state">
          <span className="empty-icon"><Icon name="chart" /></span>
          <h2>No insights yet</h2>
          <p>Ask XP a question about your materials. Every answer is scored here for faithfulness, sources and speed.</p>
          <Link className={buttonClass('secondary')} to="/subjects">Go to subjects</Link>
        </div>
      )}
      {!loading && data && t && t.sessions > 0 && (
        <>
          <div className="stats-grid">
            <Metric label="Questions asked" value={<CountUp value={t.sessions} />} note={`In the last ${days} days`} badge={`${days}d`} tone="primary" />
            <Metric label="Faithfulness" value={num(t.faithfulness)} note="How closely answers stick to your sources"
              badge={t.faithfulness == null ? '—' : confidenceLevel(t.faithfulness)} tone={t.faithfulness == null ? 'neutral' : t.faithfulness >= 0.8 ? 'success' : 'warning'} />
            <Metric label="Unsupported claims" value={pct(t.hallucination_rate)} note={`${plural(t.unverified, 'answer')} not fully verified`} badge={`${days}d`} tone="warning" />
            <Metric label="Not in materials" value={pct(t.sessions ? t.no_context / t.sessions : null)} note={`${plural(t.no_context, 'question')} found nothing in your files`} badge={`${days}d`} tone="neutral" />
          </div>
          <div className="insights-layout">
            <section className="trend-card">
              <div className="card-heading">
                <div>
                  <h2>Daily trend</h2>
                  <p>Faithfulness and questions per day</p>
                </div>
                <div className="chart-legend" aria-hidden="true">
                  <span className="line-key">Faithfulness</span>
                  <span className="bar-key">Questions</span>
                  <span className="dot-key">Nothing found</span>
                </div>
              </div>
              <TrendChart summary={data.summary} />
            </section>
            <section className="retrieval-card">
              <div className="card-heading"><div><h2>Retrieval performance</h2><p>Average across selected period</p></div></div>
              <dl className="retrieval-list">
                {[
                  ['Top similarity', num(data.summary.retrieval.avg_top_similarity)],
                  ['Chunks retrieved', num(data.summary.retrieval.avg_chunks, 1)],
                  ['Search time', ms(data.summary.retrieval.avg_retrieval_ms)],
                  ['Total time', ms(data.summary.retrieval.avg_total_ms)],
                  ['Unverified answers', String(t.unverified)],
                  ['Judge relevance', t.judge_relevance == null ? 'Not enabled' : num(t.judge_relevance)],
                ].map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
              </dl>
            </section>
          </div>
          <section className="attention-card">
            <div className="card-heading">
              <div><h2>Needs attention</h2><p>Answers with weak or incomplete evidence</p></div>
              <Badge tone={data.summary.failures.length ? 'warning' : 'success'}>{plural(data.summary.failures.length, 'answer')}</Badge>
            </div>
            {data.summary.failures.length === 0 && <p className="list-empty">Nothing to look at: every answer in this period was grounded in your materials.</p>}
            {data.summary.failures.map((f, i) => (
              <motion.div key={f.session_id} {...reveal(i)}>
                <Link className="attention-row" to={`/insights/${f.session_id}`}>
                  <span className="warning-marker"><Icon name="clock" size={15} /></span>
                  <strong>{f.query}</strong>
                  <span className="reason-chips">{f.reasons.map(r => <Badge tone="warning" key={r}>{r}</Badge>)}</span>
                  <span className="trace-link">Inspect trace <Icon name="arrow" size={14} /></span>
                </Link>
              </motion.div>
            ))}
          </section>
          <section className="recent-answers">
            <div className="card-heading"><div><h2>Recent answers</h2><p>Most recent XP responses and quality signals</p></div></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Question</th><th>Type</th><th>Chunks</th><th>Confidence</th><th>Status</th><th>Time</th><th /></tr></thead>
                <tbody>
                  {data.recent.map(r => (
                    <tr key={r.session_id}>
                      <td><strong>{r.question}</strong><span className="row-subject">{r.subject_name}</span></td>
                      <td>{r.category}</td>
                      <td>{r.chunks}</td>
                      <td>{r.confidence == null ? '—' : <ConfidencePill value={r.confidence} />}</td>
                      <td>{r.no_context ? <Badge>Nothing found</Badge> : <VerificationBadge verified={!r.unverified} />}</td>
                      <td>{ms(r.latency_ms)}</td>
                      <td><Link className={buttonClass('secondary')} to={`/insights/${r.session_id}`}>Inspect</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
