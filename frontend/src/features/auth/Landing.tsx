import { motion } from 'motion/react'
import { Link, useSearchParams } from 'react-router'
import { useMe } from '../../lib/api'
import { reveal } from '../../lib/motion'
import { CitationChip } from '../../ui/AnswerBadges'
import { Icon, type IconName } from '../../ui/Icon'
import { Badge, Logo, Skeleton, buttonClass, XpAvatar } from '../../ui/primitives'
import '../../styles/auth.css'

const STEPS: [IconName, string, string][] = [
  ['upload', 'Upload', 'Add your class notes as PDF or Word (.docx) files.'],
  ['sparkles', 'Ask XP', 'XP is your AI study assistant. It answers from your files and shows where each answer came from.'],
  ['repeat', 'Review', 'Practise with quizzes, and flashcards that come back just before you would forget them.'],
]
const FEATURES: [IconName, string, string][] = [
  ['sparkles', 'Answers only from your files', 'XP uses nothing but the files you upload, and shows the source of every answer and how sure it is.'],
  ['file', 'Quizzes, cards, and summaries', 'Generate useful study aids from every upload without copying and pasting.'],
  ['repeat', 'Flashcards at the right time', 'Each card comes back just before you would forget it, with longer gaps as you learn it.'],
  ['chart', 'Check every answer', 'See how closely each answer matches your files, and which parts of your files XP used.'],
]

export function Landing() {
  const deleted = useSearchParams()[0].has('deleted')
  const signedIn = !!useMe().data
  return (
    <div className="landing-page">
      {deleted && <p className="landing-banner" role="status">Your account and everything in it were deleted.</p>}
      <header className="landing-nav">
        <Logo />
        <nav aria-label="Account">
          {signedIn
            ? <a className={buttonClass()} href="/app/">Open ExcelPoint</a>
            : <><Link className="landing-signin" to="/login">Sign in</Link><Link className={buttonClass()} to="/register">Sign up free</Link></>}
        </nav>
      </header>
      <main>
        <section className="landing-hero">
          <motion.div {...reveal(0)}><Badge tone="ai"><Icon name="sparkles" size={12} /> AI STUDY ASSISTANT</Badge></motion.div>
          <motion.h1 {...reveal(1)}>Learn faster from your own materials</motion.h1>
          <motion.p {...reveal(2)}>Upload your class notes. Ask XP, your AI study assistant, and get answers that show where they came from. Every file also becomes a summary, a quiz and flashcards.</motion.p>
          <motion.div className="landing-actions" {...reveal(3)}>
            <Link className={buttonClass()} to="/register">Start studying free <Icon name="arrow" size={15} /></Link>
            <Link className={buttonClass('secondary')} to="/login">Sign in</Link>
          </motion.div>
          <motion.div className="landing-product" aria-hidden="true" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}>
            <div className="product-sidebar"><Logo compact /><Skeleton /><Skeleton /><Skeleton /></div>
            <div className="product-main">
              <span>Database Systems</span>
              <div className="mock-question">How does a B-tree index improve search performance?</div>
              <div className="mock-answer">
                <XpAvatar small />
                <div>
                  <strong>XP</strong>
                  <p>A B-tree keeps keys sorted in a balanced hierarchy, reducing how many disk pages must be read.</p>
                  <CitationChip label="lecture4.pdf · p. 18" />
                </div>
              </div>
            </div>
          </motion.div>
        </section>
        <section className="how-section">
          <p className="overline">HOW IT WORKS</p>
          <h2>Three simple steps</h2>
          <div>
            {STEPS.map(([icon, title, text], i) => (
              <article key={title}>
                <span className="step-number">0{i + 1}</span>
                <span className="feature-icon"><Icon name={icon} /></span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="features-section">
          <div>
            <p className="overline">BUILT FOR TRUSTED LEARNING</p>
            <h2>Answers you can check</h2>
            <p>ExcelPoint turns the materials you already trust into an active study system, and shows you exactly where every answer came from.</p>
          </div>
          <div className="feature-grid">
            {FEATURES.map(([icon, title, text]) => (
              <article key={title}>
                <span className="feature-icon"><Icon name={icon} /></span>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="landing-cta">
          <h2>Your materials already contain the answers.</h2>
          <p>Let ExcelPoint help you find and remember them.</p>
          <Link className={buttonClass()} to="/register">Create your free account</Link>
          <p className="landing-note">Free while in beta (early testing). No credit card needed. <Link to="/privacy">How we handle your data</Link></p>
        </section>
      </main>
      <footer className="landing-footer">
        <Logo />
        <Link to="/privacy">Privacy</Link>
        <Link to="/terms">Terms</Link>
        <span>Free while in beta · © {new Date().getFullYear()} ExcelPoint</span>
      </footer>
    </div>
  )
}
