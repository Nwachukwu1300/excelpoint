import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useMe } from '../../lib/api'
import excelpointIcon from '../../assets/excelpoint-icon.webp'
import { ThemeToggle } from '../../ui/ThemeToggle'
import { Icon } from '../../ui/Icon'
import { Logo, XpAvatar, buttonClass } from '../../ui/primitives'
import { CONTACT } from './Privacy'
import '../../styles/landing.css'

// The hero's sample conversation. It mirrors what the app shows: the answer, then the passage it came from.
const QUESTION = 'Where do the light reactions happen, and what do they make?'
const ANSWER = 'The light reactions happen in the thylakoid membranes inside the chloroplast. They use light energy to split water, which releases oxygen, and they make ATP and NADPH for the next stage.'
const WORDS = ANSWER.split(' ')
const PASSAGE = {
  before: 'Stage 1 is the light reactions. ',
  match: 'These take place in the thylakoid membranes inside the chloroplast.',
  after: ' Light energy splits water molecules, and oxygen is released. The energy is stored in ATP and NADPH for stage 2.',
}

const reducedMotion = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** Streams the sample answer word by word once the card is in view, then lights up the passage; whole for reduced motion. */
function useStream(target: React.RefObject<HTMLElement | null>) {
  const [shown, setShown] = useState(() => (reducedMotion() ? WORDS.length : 0))
  const timer = useRef<number>(undefined)
  const play = () => {
    window.clearInterval(timer.current)
    if (reducedMotion()) { setShown(WORDS.length); return }
    setShown(0)
    timer.current = window.setInterval(() => setShown(s => {
      if (s + 1 >= WORDS.length) window.clearInterval(timer.current)
      return Math.min(s + 1, WORDS.length)
    }), 70)
  }
  useEffect(() => {
    let start: number | undefined
    const begin = () => { start = window.setTimeout(play, 600) }
    // On phones the card starts below the fold: play when it is half visible, so the moment is seen, not missed
    const seen = typeof IntersectionObserver === 'function' && target.current
      ? new IntersectionObserver(([e]) => { if (e?.isIntersecting) { seen?.disconnect(); begin() } }, { threshold: 0.5 })
      : null
    if (seen && target.current) seen.observe(target.current)
    else begin()
    return () => { seen?.disconnect(); window.clearTimeout(start); window.clearInterval(timer.current) }
  }, [])
  return { shown, done: shown >= WORDS.length, play }
}

function AnswerDemo() {
  const card = useRef<HTMLElement>(null)
  const { shown, done, play } = useStream(card)
  return (
    <figure className="demo" ref={card}>
      <figcaption className="demo-head">
        <span><i aria-hidden="true" />Biology</span>
        <span>3 files</span>
      </figcaption>
      <div className="demo-chat">
        <p className="demo-question">{QUESTION}</p>
        <div className="demo-answer">
          <XpAvatar small />
          <div>
            <strong>XP</strong>
            <p className="sr-only">{ANSWER}</p>
            <p aria-hidden="true">
              {shown === 0 && <span className="caret" />}
              {WORDS.map((w, i) => <span key={i} className={i < shown ? 'is-on' : ''}>{w}{!done && i === shown - 1 && <span className="caret" />} </span>)}
            </p>
          </div>
        </div>
      </div>
      <div className="demo-evidence">
        <div className="demo-evidence-head">
          <span><Icon name="file" size={15} />From <strong>photosynthesis-notes.docx</strong></span>
          <span className={`demo-verified ${done ? 'is-on' : ''}`}><Icon name="check" size={14} />Verified</span>
        </div>
        <blockquote>
          {PASSAGE.before}<mark className={done ? 'is-on' : ''}>{PASSAGE.match}</mark>{PASSAGE.after}
        </blockquote>
      </div>
      <div className="demo-foot">
        <span>Example with sample notes</span>
        {!reducedMotion() && <button type="button" onClick={play}>Replay answer</button>}
      </div>
    </figure>
  )
}

const STEPS = [
  { title: 'Upload', text: 'Add your notes or a lecture recording: PDF, Word, MP3, WAV, M4A, MP4, MOV or AVI, up to 100 MB. Recordings can be up to 3 hours.' },
  { title: 'Ask XP', text: 'Ask anything about your class. XP answers only from your files and shows the passage it used, so you can check it.' },
  { title: 'Review', text: 'Flashcards come back just before you would forget them. Quizzes, and explaining a topic back to XP, show what you know and what to study next.' },
]
const GRADES: [string, string][] = [['Again', 'This session'], ['Hard', '1 day'], ['Good', '3 days'], ['Easy', '7 days']]
const PROMISES: [string, string][] = [
  ['Every answer shows its source', 'The file name and the exact passage, right under the answer.'],
  ['Only you can see your files', 'Your notes stay private to your account.'],
  ['Delete anything, any time', 'One file, one subject or your whole account. Download everything as a zip first.'],
  ['No ads. No selling data.', 'We never sell what you upload.'],
]
// Explain it back, as the app shows it: what the student said, XP's short reply, then each sentence marked
const MARKS: [string, string, string, string?][] = [
  ['is-correct', 'Correct', 'Photosynthesis happens in the chloroplasts.'],
  ['is-wrong', 'Not quite', 'The light reactions take place in the stroma.', 'Your notes say: they take place in the thylakoid membranes.'],
  ['is-unknown', 'Not in your notes', 'It was first described in 1779.'],
]
const FAQ: [string, string][] = [
  ['Is it free?', 'Yes. ExcelPoint is free while it is in beta (early testing). You do not need a credit card.'],
  ['What files work?', 'PDF and Word (.docx) notes, audio (MP3, WAV, M4A) and video (MP4, MOV, AVI). Each file can be up to 100 MB, and recordings up to 3 hours. Scanned PDFs (pictures of text) do not work yet.'],
  ['Where do my files go?', 'We store them privately in your account. To write answers, we send their text and recordings to OpenAI. OpenAI says it does not train its models on this data.'],
  ['Can I practise out loud?', 'Yes. With Explain it back, you explain a topic by speaking or typing, and XP checks each sentence against your notes. Your recording is turned into text and then deleted. Only the text is kept. You can do up to 30 checks a day.'],
  ['Can I delete my data?', 'Yes, any time. Delete one file, a subject, a chat or your whole account. You can also download everything as a zip first.'],
]

export function Landing() {
  const deleted = useSearchParams()[0].has('deleted')
  const signedIn = !!useMe().data
  const start = signedIn
    ? <a className={buttonClass()} href="/app/">Open ExcelPoint</a>
    : <Link className={buttonClass()} to="/register">Start studying free <Icon name="arrow" size={17} /></Link>

  return (
    <div className="landing">
      {deleted && <p className="landing-banner" role="status">Your account and everything in it were deleted.</p>}
      <header className="landing-bar">
        <Link to="/welcome" aria-label="ExcelPoint home"><Logo /></Link>
        <nav aria-label="Account">
          <ThemeToggle />
          {!signedIn && <Link className="landing-signin" to="/login">Sign in</Link>}
          {signedIn ? <a className={buttonClass()} href="/app/">Open ExcelPoint</a> : <Link className={buttonClass()} to="/register">Start studying free</Link>}
        </nav>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-pitch">
            <h1>Learn faster from your own notes.</h1>
            <p>Upload your class notes or a lecture recording. XP, your AI study assistant, answers only from your files and shows you the exact passage behind every answer.</p>
            <div className="landing-actions">
              {start}
              {!signedIn && <Link className={buttonClass('secondary')} to="/login">Sign in</Link>}
            </div>
            <p className="landing-small">Free while in beta. No credit card. Works with PDF, Word, audio and video.</p>
          </div>
          <AnswerDemo />
        </section>

        <section className="landing-band">
          <div className="landing-wrap">
            <h2>Three steps from your notes to the exam.</h2>
            <ol className="landing-steps">
              {STEPS.map((s, i) => (
                <li key={s.title}>
                  <h3>{i + 1}. {s.title}</h3>
                  <p>{s.text}</p>
                  {i === 0 && <div className="step-files"><span>lecture_04.mp3</span><span>cell_biology.pdf</span></div>}
                  {i === 1 && <div className="step-source"><XpAvatar small /><span>From <strong>cell_biology.pdf</strong></span></div>}
                  {i === 2 && (
                    <div className="step-grades" aria-label="Grades and when each card comes back">
                      {GRADES.map(([g, when]) => <span key={g} className={g === 'Good' ? 'is-picked' : ''}><b>{g}</b>{when}</span>)}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="landing-wrap landing-trust">
          <div>
            <h2>XP does not guess.</h2>
            <p>When your files do not cover a question, XP tells you so. It does not fill the gap with things your teacher never said. XP can still make mistakes, so every answer shows its source for you to check.</p>
          </div>
          <div className="trust-demo">
            <p className="demo-question">When is the final exam?</p>
            <div className="demo-answer">
              <XpAvatar small />
              <div className="not-found">
                <strong><Icon name="search" size={16} />Not in your materials</strong>
                <p>I couldn’t find anything about that in your Biology files. I only answer from the files in this subject. Upload notes that cover it, or ask about something your files include.</p>
              </div>
            </div>
          </div>
          <ul className="trust-promises">
            {PROMISES.map(([t, p]) => <li key={t}><h3>{t}</h3><p>{p}</p></li>)}
          </ul>
        </section>

        <section className="landing-band">
          <div className="landing-wrap">
            <h2>One file. Four ways to study it.</h2>
            <p className="landing-lede">Every upload makes all four in the background. You get a notification when they are ready.</p>
            <div className="landing-outputs">
              <article>
                <div className="output-art art-summary" aria-hidden="true"><i /><i /><i /><i /></div>
                <h3>A summary</h3>
                <p>The key ideas of the file in short, plain paragraphs.</p>
              </article>
              <article>
                <div className="output-art art-card" aria-hidden="true"><span /><span>What does NADPH carry?</span></div>
                <h3>Flashcards</h3>
                <p>They come back on a schedule that fits your memory.</p>
              </article>
              <article>
                <div className="output-art art-quiz" aria-hidden="true"><b>Question 3 of 10</b><span className="is-picked">Thylakoid membrane</span><span>Stroma</span></div>
                <h3>A quiz</h3>
                <p>Save and finish later, or ask for fresh questions.</p>
              </article>
              <article>
                <div className="output-art art-chat" aria-hidden="true"><XpAvatar small /><span><i /><i /><mark /></span></div>
                <h3>Chat with XP</h3>
                <p>Ask follow-up questions and see the source each time.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="landing-wrap landing-trust landing-explain">
          <div>
            <h2>Explain it back. XP checks you.</h2>
            <p>Explain a topic out loud or in writing, as if you were teaching it. XP checks every sentence against your notes, corrects one thing at a time and asks about what you left out.</p>
            <ul className="explain-verdicts">
              <li><b>Correct</b>, with the passage from your notes that backs it up.</li>
              <li><b>Not quite</b>, with the passage that shows the right answer.</li>
              <li><b>Not in your notes</b>, when your files don’t cover it. XP never marks you wrong for that.</li>
            </ul>
            <p>At the end you see what you got right, what to fix and what you missed, so you can explain it again and do better.</p>
          </div>
          <div className="trust-demo explain-demo">
            <p className="demo-question"><span className="demo-said"><Icon name="mic" size={14} />You said</span>Photosynthesis happens in the chloroplasts. The light reactions take place in the stroma. It was first described in 1779.</p>
            <div className="demo-answer">
              <XpAvatar small />
              <div>
                <strong>XP</strong>
                <div className="demo-reply">Right, it happens in the chloroplasts. The light reactions are in the thylakoid membranes, though, not the stroma. What do they make for the next stage?</div>
              </div>
            </div>
            <ul className="demo-marks" aria-label="Each sentence checked against your notes">
              {MARKS.map(([tone, label, sentence, note]) => (
                <li key={label} className={tone}>
                  <b>{label}</b>
                  <span>{sentence}</span>
                  {note && <small>{note}</small>}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="landing-faq">
          <h2>Questions you might have</h2>
          {FAQ.map(([q, a], i) => (
            <details key={q} open={i === 0}>
              <summary>{q}<Icon name="chevronDown" size={18} /></summary>
              <p>{a}</p>
            </details>
          ))}
        </section>

        <section className="landing-close">
          <div>
            <div className="close-copy">
              <img src={excelpointIcon} alt="" aria-hidden="true" width={72} height={72} />
              <div>
                <h2>Your notes already have the answers.</h2>
                <p>Upload one file and see what XP finds.</p>
              </div>
            </div>
            {signedIn ? <a className={buttonClass()} href="/app/">Open ExcelPoint</a> : <Link className={buttonClass()} to="/register">Start studying free</Link>}
          </div>
        </section>
      </main>

      <footer className="landing-foot">
        <Logo />
        <span>Free while in beta (early testing)</span>
        <nav aria-label="Legal">
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms</Link>
          <a href={`mailto:${CONTACT}`}>{CONTACT}</a>
        </nav>
        <span>© {new Date().getFullYear()} ExcelPoint</span>
      </footer>
    </div>
  )
}
