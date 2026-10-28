import { Link } from 'react-router'
import { Logo } from '../../ui/primitives'
import '../../styles/auth.css'

// Describes what the code does today. Update it whenever data handling changes.
const SECTIONS: [string, string[]][] = [
  ['What we keep', [
    'Your account: username, email, password (stored scrambled, never readable), and the name and level of education you choose to add.',
    'Your files, the text read from them, and the summaries, flashcards and quizzes made from them.',
    'Your questions to XP, its answers, and a record of how each answer was made (which parts of your files it used, and quality scores).',
    'Your quiz answers, flashcard review history and notifications.',
  ]],
  ['Who can see it', [
    'Only you. Other people using ExcelPoint can’t see your files, questions or results.',
    'To write answers, summaries, flashcards and quizzes, the text of your files and your questions is sent to OpenAI, the company that runs the AI model XP uses. OpenAI processes it under its API terms.',
    'The search that finds the right parts of your files runs on our own server.',
    'If you sign in with Google, Google tells us your name, email address and Google account ID.',
  ]],
  ['What we don’t do', [
    'No ads, no selling your data, and no marketing email.',
    'No tracking or analytics tools. The site uses only the cookies it needs to keep you signed in and protect forms, and remembers your light or dark theme in your browser.',
  ]],
  ['Deleting your data', [
    'You can delete any file, subject or XP conversation at any time.',
    'Settings → Delete account removes your account and everything above, including your stored files. This can’t be undone.',
  ]],
  ['Price', [
    'ExcelPoint is free while it is in beta.',
  ]],
]

export function Privacy() {
  return (
    <div className="auth-page privacy-page">
      <Link className="auth-logo" to="/welcome" aria-label="ExcelPoint home"><Logo /></Link>
      <article className="auth-card privacy-card">
        <h1>Privacy</h1>
        <p className="privacy-updated">How ExcelPoint handles your data, in plain words. Last updated 28 October 2026.</p>
        {SECTIONS.map(([title, points]) => (
          <section key={title}>
            <h2>{title}</h2>
            <ul>{points.map(p => <li key={p}>{p}</li>)}</ul>
          </section>
        ))}
        <p className="auth-switch"><Link to="/register">Create an account</Link> · <Link to="/welcome">Back to the home page</Link></p>
      </article>
    </div>
  )
}
