import { motion } from 'motion/react'
import { Link } from 'react-router'
import { useMe } from '../../lib/api'
import { reveal } from '../../lib/motion'
import { CitationChip } from '../../ui/AnswerBadges'
import { Icon, type IconName } from '../../ui/Icon'
import { Badge, Logo, Skeleton, buttonClass } from '../../ui/primitives'
import '../../styles/auth.css'

const STEPS: [IconName, string, string][] = [
  ['upload', 'Upload', 'Add PDFs, Word documents, recordings, and videos.'],
  ['sparkles', 'Ask XP', 'Get focused answers that cite your own notes.'],
  ['repeat', 'Review', 'Practise with quizzes and spaced-repetition flashcards.'],
]
const FEATURES: [IconName, string, string][] = [
  ['sparkles', 'Grounded answers', 'XP answers only from your materials, with citations and confidence on every response.'],
  ['file', 'Quizzes, cards, and summaries', 'Generate useful study aids from every upload without copying and pasting.'],
  ['repeat', 'Spaced repetition', 'Review cards on a schedule that stretches as your memory gets stronger.'],
  ['chart', 'Answer quality insights', 'Track faithfulness, unsupported claims, retrieval quality, and full answer traces.'],
]

export function Landing() {
  const signedIn = !!useMe().data
  return (
    <div className="landing-page">
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
          <motion.div {...reveal(0)}><Badge tone="ai"><Icon name="sparkles" size={12} /> GROUNDED AI STUDY TOOLS</Badge></motion.div>
          <motion.h1 {...reveal(1)}>Learn faster from your own materials</motion.h1>
          <motion.p {...reveal(2)}>Upload your notes and lectures. Ask XP questions with cited answers, then turn every file into summaries, quizzes, and flashcards.</motion.p>
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
                <span className="xp-avatar xp-avatar--small"><Icon name="sparkles" size={14} /></span>
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
          <h2>From upload to understanding</h2>
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
            <h2>Know more. Guess less.</h2>
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
        </section>
      </main>
      <footer className="landing-footer">
        <Logo />
        <span>© {new Date().getFullYear()} ExcelPoint</span>
      </footer>
    </div>
  )
}
